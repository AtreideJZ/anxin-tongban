"""亲子共创服务（v2.2 拓展方向 B + C）

两部分职责：
1. 亲子话题卡（B）：生成温暖的亲子面对面话题，引导孩子拿着话题
   去和爸爸妈妈当面聊——AI 做亲子纽带，而不是替代亲子沟通。
2. 共创故事（C）：start / add_turn / finalize，见对应函数 docstring。

安全不变量：
- 话题卡的 LLM 产出经过 Step 1 关键词检测过滤，命中敏感词即回退预置话题
- 共创故事中孩子的每一段输入仍走完整 Pipeline 审计，不得绕过安全闭环
- 话题卡与共创故事均不计入 2 小时使用计时（亲子活动，不是 AI 使用）
"""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from core import critic_agent
from core import guardrails as gr
from core import llm_client
from core import pipeline
from core.age_tiers import is_younger_tier, normalize_age_tier

from ..database import SessionLocal
from ..models.cocreation import CocreationStory
from ..models.planet import PlanetEntry
from ..models.user import User
from . import episodic_service, planet_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 亲子话题卡（B）
# ---------------------------------------------------------------------------

# 预置话题库（无 LLM 时的兜底，也是 LLM 产出被拦截时的安全回退）
# 分低龄（5-10）/ 高龄（11-14+）两档，均为正向亲子交流话题
_FALLBACK_TOPICS_YOUNGER = [
    "今天学校里最让你笑的一件事是什么？拿去问问爸爸妈妈，也听听他们的答案吧！",
    "如果你可以发明一样东西，它会是什么？和爸爸妈妈一起想想看！",
    "你今天画过什么、搭过什么？讲给爸爸妈妈听听吧！",
    "如果你变成一种小动物一天，你想变成什么？问问爸爸妈妈想变成什么！",
    "这周有没有一件让你觉得「我做到了！」的小事？去告诉爸爸妈妈吧！",
    "如果能和爸爸妈妈一起去一个地方玩，你最想去哪里？",
]

_FALLBACK_TOPICS_OLDER = [
    "最近有没有一个想法，你很想听听爸爸妈妈的观点？找个时间和他们聊聊吧。",
    "如果能和爸爸妈妈交换一天身份，你觉得会发现什么？去问问他们的答案。",
    "最近有没有一件事让你有点小得意？和爸爸妈妈分享一下，也问问他们年轻时的故事。",
    "如果给家里定一条新的「家庭规矩」，你会定什么？和爸爸妈妈讨论一下吧。",
    "你最近在思考的问题里，有没有一个想听听爸妈怎么看的？",
    "和爸爸妈妈聊聊：他们小时候最喜欢的游戏是什么？和你的有什么不一样？",
]

_TOPIC_SYSTEM_PROMPT = """你是一个亲子沟通话题生成器。为孩子生成一个可以拿去和爸爸妈妈面对面聊的话题。

硬性要求：
- 只输出一个话题，一到两句话，以问号或邀请语结尾
- 话题必须正向、温暖、适合亲子交流（如学校趣事、想象力、感恩、家庭回忆）
- 绝不涉及：自伤、暴力、恐怖、成人内容、隐私信息、消极攀比
- 话题要符合孩子的年龄认知水平
- 目的是让孩子放下屏幕去和父母当面交流，话题要能引发双向对话"""


def generate_topic(age_tier: str) -> dict:
    """生成一个亲子话题（年龄适配 + 敏感词过滤）

    LLM 可用时由轻量模型生成，产出经 Step 1 关键词检测过滤；
    不可用或被拦截时回退到分龄预置话题库，保证无 Key 也可运行。

    Returns:
        {"topic": str, "source": "llm" | "fallback", "age_tier": str}
    """
    tier = normalize_age_tier(age_tier)
    fallback_pool = (
        _FALLBACK_TOPICS_YOUNGER if is_younger_tier(tier) else _FALLBACK_TOPICS_OLDER
    )

    if llm_client.is_llm_available():
        try:
            raw = llm_client.chat_complete(
                messages=[
                    {"role": "system", "content": _TOPIC_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"请为一个 {tier} 岁的孩子生成一个亲子话题。",
                    },
                ],
                temperature=0.8,
                max_tokens=120,
            )
            topic = raw.strip().strip('"「」')[:120]
            # 安全过滤：产出过 Step 1 关键词检测，命中即回退预置话题
            if topic and not gr.detect(topic).matched:
                return {"topic": topic, "source": "llm", "age_tier": tier}
        except Exception:
            logger.warning("亲子话题卡 LLM 生成失败，回退预置话题库", exc_info=True)

    return {"topic": random.choice(fallback_pool), "source": "fallback", "age_tier": tier}


# ---------------------------------------------------------------------------
# 共创故事（C，docs/v2.2-拓展方向.md 第五节）
# ---------------------------------------------------------------------------

# 分龄轮次上限（5.4）：孩子 + 家长接的段（kind="text"）合计上限
_MAX_TEXT_TURNS_YOUNGER = 4  # 低龄（5-7 / 8-10）：故事更短
_MAX_TEXT_TURNS_OLDER = 8    # 高龄（11-13 / 14）：孩子主导，故事可更长

# 达到上限时 add_turn 抛出的提示（引导孩子去点「完成润色」）
_STORY_FULL_MESSAGE = "故事已经很长啦，点「完成润色」把它变成成品吧！"

# 预置开头库（无 LLM 时的兜底，也是 LLM 产出被关键词拦截时的安全回退）
# 均为 30-50 字、温和意象、留白结尾（把情节的决定权留给孩子和家长）
_FALLBACK_OPENINGS_YOUNGER = [
    "小鲸鱼泡泡有一个秘密：它做梦的时候，尾巴尖会冒出彩虹色的泡泡，带着它轻轻飘起来……",
    "小恐龙豆豆在森林深处发现了一扇小小的门，门上挂着一盏会眨眼的星星灯……",
    "小兔子团团种下一颗发光的种子，第二天清晨，土里钻出了一片会唱歌的叶子……",
]

_FALLBACK_OPENINGS_OLDER = [
    "林小满在旧书摊淘到一本没有字的书，翻开第一页时，纸面浮起一行淡淡的字：「轮到你了。」",
    "天文社的望远镜在暴雨夜里收到一串有节奏的光点，像是有人从很远的星系敲门……",
    "放学路上，阿澈捡到过一只纸飞机，机翼上写着一行小字：「请在日落前替我完成一件事。」",
]

# 预置引导句库（只提问、不代写——AI 是脚手架，不替孩子写情节）
_FALLBACK_GUIDES_YOUNGER = [
    "接下来会发生什么呀？",
    "这时候，它会遇到谁呢？",
    "你觉得它心里在想什么？",
    "哇，然后呢然后呢？",
]

_FALLBACK_GUIDES_OLDER = [
    "你想怎么推进这个故事？",
    "这个转折之后，主角会怎么选？",
    "这里可以埋一个伏笔——你想留什么线索？",
    "接下来由你掌舵，故事往哪儿走？",
]

_OPENING_SYSTEM_PROMPT = """你是一个亲子共创故事的开头生成器。为孩子和家长一起接龙写的故事写第一段开头。

硬性要求：
- 只输出故事开头这一段，30-50 字，中文
- 结尾必须留白（用省略号或悬念收住），把「接下来发生什么」留给孩子和家长
- 意象温和（小动物、星空、自然、校园），符合孩子的年龄认知水平
- 绝不涉及：自伤、暴力、恐怖、成人内容、隐私信息
- 不要提问、不要解释，只写故事本身"""

_GUIDE_SYSTEM_PROMPT = """你是亲子共创故事的引导者。孩子或家长刚接了一段故事，你要用一句话轻轻引导他们继续。

硬性要求：
- 只输出一句简短的提问或邀请（如"接下来会发生什么呀？"），不超过 30 字
- 只提问、只邀请，绝不替他们写情节、绝不给出具体剧情
- 语气温暖、好奇，符合孩子的年龄"""

_POLISH_SYSTEM_PROMPT = """你是一个谨慎的文字编辑。孩子和家长接龙写了一个故事，你要把它润色成通顺的成品。

硬性要求（必须严格遵守）：
- 只修正语法错误和错别字，适当调整标点与分段
- 绝不改变情节、先后顺序和表达方式，绝不新增情节或角色
- 保留孩子气的语言风格，不要改成大人的腔调
- 直接输出润色后的完整故事，不要解释、不要评论"""

# 家长输入命中关键词时的温和提示（成人输入不走完整 Pipeline，只做 Step 1 关键词检查）
_PARENT_REJECT_MESSAGE = "这一段好像不太适合写进给孩子看的故事里，换一段温和一点的试试？"


def _cn_date(dt: datetime) -> str:
    """"7月1日" 中文日期格式（与 backend/seed.py、planet_service 一致）"""
    return dt.strftime("%m月%d日").lstrip("0")


def _text_turn_limit(age_tier: Optional[str]) -> int:
    """分龄轮次上限：低龄 4 段，高龄 8 段（孩子 + 家长接的段合计）"""
    return _MAX_TEXT_TURNS_YOUNGER if is_younger_tier(age_tier) else _MAX_TEXT_TURNS_OLDER


def _count_text_turns(turns: list) -> int:
    """统计已接的故事段数（只数 child/parent 的 text 段，AI 开头与引导不计）"""
    return sum(1 for t in turns if t.get("kind") == "text")


def _generate_opening(tier: str) -> str:
    """生成故事开头：LLM 可用时生成并过关键词过滤，否则回退分龄预置库"""
    fallback_pool = (
        _FALLBACK_OPENINGS_YOUNGER if is_younger_tier(tier) else _FALLBACK_OPENINGS_OLDER
    )
    if llm_client.is_llm_available():
        try:
            raw = llm_client.chat_complete(
                messages=[
                    {"role": "system", "content": _OPENING_SYSTEM_PROMPT},
                    {"role": "user", "content": f"请为一个 {tier} 岁的孩子写一个共创故事开头。"},
                ],
                temperature=0.9,
                max_tokens=120,
            )
            opening = raw.strip().strip('"「」')
            # 长度校验（30-50 字为目标，留出 LLM 误差带）+ Step 1 关键词过滤
            if 10 <= len(opening) <= 120 and not gr.detect(opening).matched:
                return opening
        except Exception:
            pass  # LLM 失败 → 回退预置开头库
    return random.choice(fallback_pool)


def _generate_guide(tier: str) -> str:
    """生成一句 AI 轻量引导：只提问不代写，产出过关键词过滤，回退预置引导句"""
    fallback_pool = (
        _FALLBACK_GUIDES_YOUNGER if is_younger_tier(tier) else _FALLBACK_GUIDES_OLDER
    )
    if llm_client.is_llm_available():
        try:
            raw = llm_client.chat_complete(
                messages=[
                    {"role": "system", "content": _GUIDE_SYSTEM_PROMPT},
                    {"role": "user", "content": f"请引导一个 {tier} 岁的孩子继续接故事。"},
                ],
                temperature=0.7,
                max_tokens=60,
            )
            guide = raw.strip().strip('"「」')
            if 2 <= len(guide) <= 60 and not gr.detect(guide).matched:
                return guide
        except Exception:
            pass
    return random.choice(fallback_pool)


def _run_child_pipeline(db: Session, child: User, content: str) -> "pipeline.PipelineResult":
    """孩子接的每一段都跑完整 Pipeline 审计（安全硬规则，不得绕过安全闭环）

    episodic 三个回调与 chat_service.process_message 一致：内部新建
    SessionLocal() 会话，保证 per-user 隔离、不写全局 JSON。
    """
    planet = planet_service.build_planet_dict(db, child.id)

    def _episodic_store(summary) -> None:
        with SessionLocal() as s:
            episodic_service.store_episode(s, child.id, summary)

    def _episodic_retriever(user_input: str):
        with SessionLocal() as s:
            return episodic_service.retrieve_by_topic(s, child.id, user_input)

    def _episodic_count() -> int:
        with SessionLocal() as s:
            return episodic_service.count_episodes(s, child.id)

    return pipeline.run(
        content,
        normalize_age_tier(child.age_tier),
        "story",
        planet,
        [],
        None,
        episodic_retriever=_episodic_retriever,
        episodic_store=_episodic_store,
        episodic_count=_episodic_count,
    )


def _get_owned_active_story(db: Session, child: User, story_id: int) -> CocreationStory:
    """取故事并校验归属与状态（只属于该孩子、且仍在进行中）"""
    story = db.get(CocreationStory, story_id)
    if story is None or story.child_user_id != child.id:
        raise ValueError("故事不存在")
    if story.status != "active":
        raise ValueError("这个故事已经完成啦")
    return story


def story_to_dict(story: CocreationStory) -> dict:
    """CocreationStory → API 响应 dict"""
    return {
        "id": story.id,
        "title": story.title,
        "status": story.status,
        "turns": list(story.turns or []),
        "final_text": story.final_text,
        "shared_with_parent": bool(story.shared_with_parent),
        "created_at": story.created_at.isoformat(timespec="seconds"),
    }


def start_story(db: Session, child: User, title: Optional[str]) -> CocreationStory:
    """发起一篇共创故事：AI 生成开头（30-50 字、年龄适配、留白结尾）作为第一条 turn"""
    title = (title or "").strip()
    if not title:
        now = datetime.now()
        title = f"我们的共创故事·{now.month}月{now.day}日"
    tier = normalize_age_tier(child.age_tier)
    opening = _generate_opening(tier)
    story = CocreationStory(
        child_user_id=child.id,
        parent_user_id=child.parent_id,
        title=title[:64],
        turns=[
            {
                "role": "ai",
                "kind": "opening",
                "content": opening,
                "ts": datetime.now().isoformat(timespec="seconds"),
            }
        ],
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def add_turn(db: Session, child: User, story_id: int, role: str, content: str) -> dict:
    """孩子或家长接一段故事（同设备轮流输入，不做实时同步）

    安全硬规则：
    - role="child" 的内容先跑完整 Pipeline 审计；触发危机模板 / 批判拦截 /
      risk_level>=2 时不存储原文，直接把 Pipeline 的安全回复作为回应
      （危机模板路径天然安全）
    - role="parent" 不做完整 Pipeline（成人输入），只做 Step 1 关键词检查，
      命中同样拒绝存储并返回温和提示

    Returns:
        {"accepted": bool, "story": dict, "ai_response": str|None,
         "suggest_finalize": bool}
    """
    if role not in ("child", "parent"):
        raise ValueError("role 只能是 child 或 parent")
    story = _get_owned_active_story(db, child, story_id)

    # 分龄轮次上限（5.4）：达到上限后引导完成润色
    limit = _text_turn_limit(child.age_tier)
    if _count_text_turns(story.turns or []) >= limit:
        raise ValueError(_STORY_FULL_MESSAGE)

    if role == "child":
        result = _run_child_pipeline(db, child, content)
        if result.used_crisis_template or result.critic_intercepted or result.risk_level >= 2:
            # 不存储该段原文；Pipeline 的安全回复直接作为回应
            return {
                "accepted": False,
                "story": story_to_dict(story),
                "ai_response": result.final_reply,
                "suggest_finalize": False,
            }
    else:  # parent：仅关键词检查
        if gr.detect(content).matched:
            return {
                "accepted": False,
                "story": story_to_dict(story),
                "ai_response": _PARENT_REJECT_MESSAGE,
                "suggest_finalize": False,
            }

    # 通过审计：追加本段 + 一条 AI 轻量引导（只提问不代写）
    now_iso = datetime.now().isoformat(timespec="seconds")
    turns = list(story.turns or [])
    turns.append({"role": role, "kind": "text", "content": content, "ts": now_iso})
    turns.append(
        {
            "role": "ai",
            "kind": "guide",
            "content": _generate_guide(normalize_age_tier(child.age_tier)),
            "ts": now_iso,
        }
    )
    story.turns = turns  # JSON 列需整体重赋值才会被 SQLAlchemy 感知
    db.commit()
    db.refresh(story)

    # 达到上限-1 时提示可以收尾了
    suggest_finalize = _count_text_turns(turns) >= limit - 1
    return {
        "accepted": True,
        "story": story_to_dict(story),
        "ai_response": None,
        "suggest_finalize": suggest_finalize,
    }


def finalize_story(db: Session, child: User, story_id: int) -> dict:
    """完成润色：串联原文 → LLM 润色（只改语法/错别字）→ Step 6 审计 → 种小星球

    保底原则：LLM 不可用或批判审计告警时，用未润色的原文拼接——绝不阻塞成品。
    成品自动种一条小星球 story 条目（source="cocreation"）。
    """
    story = _get_owned_active_story(db, child, story_id)

    # 串联：AI 开头 + 所有孩子/家长段的原文（保持接龙顺序）
    turns = list(story.turns or [])
    parts: list[str] = []
    for t in turns:
        if t.get("kind") == "opening" or (
            t.get("kind") == "text" and t.get("role") in ("child", "parent")
        ):
            parts.append(t.get("content", "").strip())
    parts = [p for p in parts if p]
    if _count_text_turns(turns) == 0:
        raise ValueError("还没有人接故事呢，先接一段再润色吧")
    raw_text = "\n".join(parts)

    # LLM 润色（只改语法/错别字，不改情节表达）；产出过 Step 6 批判审计
    final_text = raw_text
    if llm_client.is_llm_available():
        try:
            polished = llm_client.chat_complete(
                messages=[
                    {"role": "system", "content": _POLISH_SYSTEM_PROMPT},
                    {"role": "user", "content": f"请润色这篇共创故事：\n{raw_text}"},
                ],
                temperature=0.2,
                max_tokens=1200,
            ).strip()
            # 批判审计告警或空产出 → 回退未润色原文（保底，绝不阻塞）
            if polished and not critic_agent.audit(polished).alert:
                final_text = polished
        except Exception:
            pass

    story.final_text = final_text
    story.status = "done"
    db.commit()

    # 自动种小星球：故事册 +1（type="story", source="cocreation"）
    now = datetime.now()
    entry = PlanetEntry(
        user_id=child.id,
        type="story",
        title=story.title,
        content=final_text,
        tags=["故事", "共创"],
        source="cocreation",
        date=_cn_date(now),
        created_at=now,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    db.refresh(story)

    return {
        "story": story_to_dict(story),
        "final_text": final_text,
        "authors": f"✍️ {child.username}和家人一起写的故事",
        "planet_entry_id": entry.id,
    }


def list_stories(db: Session, child: User) -> list[CocreationStory]:
    """孩子自己的共创故事列表（时间倒序）"""
    return (
        db.query(CocreationStory)
        .filter(CocreationStory.child_user_id == child.id)
        .order_by(CocreationStory.created_at.desc())
        .all()
    )


def share_story(db: Session, child: User, story_id: int) -> CocreationStory:
    """把已完成的故事分享给家长看（只能分享自己的、已完成的）"""
    story = db.get(CocreationStory, story_id)
    if story is None or story.child_user_id != child.id:
        raise ValueError("故事不存在")
    if story.status != "done":
        raise ValueError("故事还没完成，先点「完成润色」吧")
    story.shared_with_parent = True
    db.commit()
    db.refresh(story)
    return story


def list_shared_stories(db: Session, parent: User) -> list[dict]:
    """家长端：该家长关联孩子的、已分享且已完成的共创故事（含孩子用户名）"""
    rows = (
        db.query(CocreationStory, User.username)
        .join(User, User.id == CocreationStory.child_user_id)
        .filter(
            CocreationStory.parent_user_id == parent.id,
            CocreationStory.shared_with_parent.is_(True),
            CocreationStory.status == "done",
        )
        .order_by(CocreationStory.created_at.desc())
        .all()
    )
    return [
        {**story_to_dict(story), "child_username": username}
        for story, username in rows
    ]
