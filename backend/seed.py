"""演示账号种子脚本（v2.1 方案 4.9）

生成「满血」演示数据，供评委体验与录制演示视频：
- demo_kid（PIN 1234，child，8-10）/ demo_parent（PIN 0000，parent，已关联）
- ~10 条四类星球条目（分布在过去 14 天）
- 2 个时间胶囊（一个倒计时中、一个已到期解锁）
- 过去 7 天含风险事件的对话历史 + 家长告警（家长端仪表盘有数据）
- 一篇已完成并分享的共创故事 + 对应星球条目（v2.2 拓展方向 C）

幂等：demo_kid 已存在则跳过。

用法（从项目根运行）：
    python -m backend.seed
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

# 把项目根加入 sys.path（直接 `python backend/seed.py` 运行时也可用）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import SessionLocal, init_db
from backend.models.capsule import Capsule
from backend.models.cocreation import CocreationStory
from backend.models.memory import EpisodicMemory
from backend.models.parent import ParentAlert, ParentPreference
from backend.models.planet import PlanetEntry
from backend.models.session import ChatSession
from backend.models.user import User
from backend.services.user_service import hash_pin


def _cn_date(dt: datetime) -> str:
    """"7月1日" 中文日期格式（与 core/memory_manager 一致）"""
    return dt.strftime("%m月%d日").lstrip("0")


def run_seed(db) -> bool:
    """写入演示数据；已存在则跳过。返回是否真正写入。"""
    if db.query(User).filter(User.username == "demo_kid").first():
        print("演示账号 demo_kid 已存在，跳过 seed。")
        return False

    now = datetime.now()

    # ------------------------------------------------------------------
    # 演示账号（监护人同意已勾选）
    # ------------------------------------------------------------------
    parent = User(
        username="demo_parent",
        pin_hash=hash_pin("0000"),
        age_tier=None,
        role="parent",
        guardian_consent=True,
    )
    db.add(parent)
    db.flush()  # 拿到 parent.id

    kid = User(
        username="demo_kid",
        pin_hash=hash_pin("1234"),
        age_tier="8-10",
        role="child",
        guardian_consent=True,
        parent_id=parent.id,
    )
    db.add(kid)
    db.flush()

    # ------------------------------------------------------------------
    # 星球条目：~10 条四类，分布在过去 14 天
    # ------------------------------------------------------------------
    entries = [
        # (type, title, content, mood, tags, days_ago)
        ("star", "为什么天空是蓝色的？", "和安心童伴一起探索了光的散射，原来阳光里藏着七种颜色。", None, ["科学", "好奇"], 13),
        ("star", "恐龙为什么灭绝了？", "问了安心童伴，原来是一颗很大的陨石撞到了地球。", None, ["科学", "好奇"], 9),
        ("star", "彩虹是怎么形成的？", "阳光穿过小水滴会拐弯，七种颜色就分开了。", None, ["自然", "好奇"], 2),
        ("cloud", "今天考试没考好", "今天数学考试没考好，有点难过，但聊完之后好多了。", "blue", ["情绪", "学校"], 11),
        ("cloud", "爸爸妈妈又加班了", "晚上一个人在家有点孤单，但安心童伴说可以画画等他们回来。", "blue", ["家庭", "孤单"], 6),
        ("cloud", "和妈妈聊了天，感觉好多了", "把心里的事告诉了妈妈，妈妈抱了我一下。", "pink", ["家庭", "温暖"], 1),
        ("sprout", "告诉了老师同学推我的事", "我鼓起勇气告诉了老师，老师说会帮我处理。", None, ["勇敢", "校园"], 8),
        ("sprout", "主动和新同学说了话", "课间我主动跟新同学打招呼了，他笑了一下。", None, ["勇敢", "社交"], 3),
        ("story", "小恐龙第一次交朋友", "一只不会喷火的小恐龙，用真诚交到了第一个朋友。", None, ["故事", "友谊"], 5),
        ("story", "月亮上的小兔子", "一个关于孤独和友谊的故事，听完心里暖暖的。", None, ["故事", "情绪"], 1),
    ]
    for entry_type, title, content, mood, tags, days_ago in entries:
        created = now - timedelta(days=days_ago)
        db.add(
            PlanetEntry(
                user_id=kid.id,
                type=entry_type,
                title=title,
                content=content,
                mood=mood,
                tags=tags,
                source="manual",
                date=_cn_date(created),
                created_at=created,
            )
        )

    # ------------------------------------------------------------------
    # 时间胶囊：一个倒计时中 + 一个已到期解锁
    # ------------------------------------------------------------------
    db.add(
        Capsule(
            user_id=kid.id,
            title="给一个月后的我",
            content="嘿，你现在变得更勇敢了吗？还记得写这封信的时候，"
            "你刚刚告诉了老师同学推你的事。不管现在怎么样，我都为你骄傲。",
            unlock_at=now + timedelta(days=25),
            unlocked=False,
            created_at=now - timedelta(days=5),
        )
    )
    db.add(
        Capsule(
            user_id=kid.id,
            title="开学时写给自己的话",
            content="希望这学期的我，上课敢举手，下课有朋友。",
            unlock_at=now - timedelta(days=1),
            unlocked=True,
            created_at=now - timedelta(days=20),
        )
    )

    # ------------------------------------------------------------------
    # 对话历史：过去 7 天，含一次校园欺凌风险事件 + 一次学习引导
    # ------------------------------------------------------------------
    def _ts(days_ago: int, hour: int = 19) -> str:
        return (now - timedelta(days=days_ago)).replace(
            hour=hour, minute=30, second=0
        ).isoformat(timespec="seconds")

    messages = [
        {"role": "user", "content": "天空为什么是蓝色的？", "ts": _ts(6)},
        {"role": "assistant", "content": "天空看起来是蓝色的，是因为阳光里有很多种颜色，蓝色像小弹珠一样最容易在空气里被弹来弹去，所以我们抬头就看到一片蓝蓝的天啦。", "ts": _ts(6)},
        {"role": "user", "content": "同学总是推我，还说不许告诉老师", "ts": _ts(4)},
        {"role": "assistant", "content": "被推了一定很疼也很难受，小朋友。这绝对不是你的错。不要自己一个人扛，告诉爸爸妈妈或者老师，他们会帮你。你愿意现在就找一个大人说说吗？", "ts": _ts(4)},
        {"role": "user", "content": "帮我做这道数学题，我不会做", "ts": _ts(2)},
        {"role": "assistant", "content": "嗯，小朋友，我先不直接给你答案——因为我相信你自己想想就能找到。\n我们先一起看看：题目里给了哪些已知条件？把它们找出来，再看看它们之间有什么关系？\n你先试试看，如果卡住了我再给一点提示，好吗？", "ts": _ts(2)},
        {"role": "user", "content": "今天我把心里的事告诉了妈妈", "ts": _ts(1)},
        {"role": "assistant", "content": "嗯嗯，我听到了，小朋友。谢谢你愿意跟我说。如果你愿意多告诉我一点，我们可以一起想想怎么办。", "ts": _ts(1)},
    ]
    db.add(
        ChatSession(
            user_id=kid.id,
            messages=messages,
            mode="chat",
            usage_minutes=45,
            started_at=now - timedelta(days=6),
            updated_at=now - timedelta(days=1),
        )
    )

    # ------------------------------------------------------------------
    # 家长告警：过去 7 天分布，含一次高风险（让仪表盘有数据）
    # ------------------------------------------------------------------
    alerts = [
        # (days_ago, topic, risk_level, summary, suggestion, acknowledged)
        (6, "safe", 0, "孩子提问了科学知识（天空为什么是蓝色的），无风险信号。",
         "无需处理。可以陪孩子一起继续探索科学话题。", True),
        (4, "school_bullying", 2, "孩子提到被同学推搡并被要求保密（校园欺凌信号）。安心童伴已安抚并鼓励孩子告诉老师或家长。",
         "建议以轻松的方式关心孩子在校的人际关系，不要直接质问。如果情况持续，建议与班主任沟通。", False),
        (4, "school_bullying", 2, "校园欺凌话题对话发生在晚间时段，孩子可能需要更多陪伴。",
         "睡前可以和孩子聊几分钟今天发生的事，让他感到被关注。", True),
        (2, "safe", 0, "孩子请求帮忙做数学题，安心童伴使用苏格拉底式引导，未直接给答案。",
         "无需处理。可以鼓励孩子先自己思考，再寻求提示。", True),
        (1, "emotional_low", 3, "孩子表达了高风险情绪信号。安心童伴已使用预置危机模板回应（引导联系家人或拨打 12355），未让 AI 自由生成回复。",
         "🚨 请立即与孩子沟通。如需专业心理援助，请拨打 12355 青少年服务热线（24 小时）或联系学校心理老师。", False),
    ]
    for days_ago, topic, risk_level, summary, suggestion, ack in alerts:
        db.add(
            ParentAlert(
                user_id=kid.id,
                timestamp=now - timedelta(days=days_ago),
                topic=topic,
                risk_level=risk_level,
                summary=summary,
                suggestion=suggestion,
                acknowledged=ack,
            )
        )

    # ------------------------------------------------------------------
    # 情景记忆：过去 7 天分布（per-user 隔离，让家长端情绪趋势有数据，方案 4.9）
    # ------------------------------------------------------------------
    episodes = [
        # (days_ago, topics, knowledge_gaps, emotion_trend, hints, interests)
        (6, ["天文", "光的散射"], ["波长的概念"], "positive",
         ["用比喻解释效果好"], ["主动追问", "说好神奇"]),
        (6, ["日常聊天"], [], "neutral", [], []),
        (4, ["校园欺凌", "情绪"], [], "negative",
         ["先确认感受再引导求助"], ["说了自己很疼"]),
        (2, ["数学", "学习"], ["已知条件的找法"], "slightly_negative",
         ["苏格拉底式引导有效"], ["愿意尝试思考"]),
        (2, ["日常聊天"], [], "neutral", [], []),
        (1, ["家庭", "情绪"], [], "positive", [], ["分享了一件开心的事"]),
    ]
    for days_ago, topics, gaps, emotion, hints, interests in episodes:
        db.add(
            EpisodicMemory(
                user_id=kid.id,
                timestamp=now - timedelta(days=days_ago),
                topics=topics,
                knowledge_gaps=gaps,
                emotion_trend=emotion,
                socratic_hints=hints,
                interest_signals=interests,
                age_tier="8-10",
            )
        )

    # ------------------------------------------------------------------
    # 家长话题偏好示例（限制游戏话题）
    # ------------------------------------------------------------------
    db.add(
        ParentPreference(
            user_id=kid.id,
            allowed_topics=["百科", "故事", "学习"],
            limited_topics=["游戏"],
            forbidden_topics=[],
        )
    )

    # ------------------------------------------------------------------
    # 共创故事演示（v2.2 拓展方向 C）：一篇已完成、已分享的成品
    # turns 含 AI 开头 / 孩子两段 / 家长一段 / AI 引导一条；
    # shared_with_parent=True 让评委在家长端「共创故事」卡片直接看到成品
    # ------------------------------------------------------------------
    co_opening = "小鲸鱼泡泡有一个秘密：它做梦的时候，尾巴尖会冒出彩虹色的泡泡，带着它轻轻飘起来……"
    co_child_1 = "泡泡飘到了云朵上面，云朵软绵绵的，像一大团棉花糖。"
    co_child_2 = "泡泡遇到一只迷路的小海鸥，小海鸥找不到回家的路了。"
    co_parent_1 = "泡泡用彩虹泡泡裹住小海鸥，顺着月亮的光，把它送回了海边的家。"
    co_final = (
        "小鲸鱼泡泡有一个秘密：它做梦的时候，尾巴尖会冒出彩虹色的泡泡，带着它轻轻飘起来。\n"
        "泡泡飘到了云朵上面，云朵软绵绵的，像一大团棉花糖。\n"
        "泡泡遇到一只迷路的小海鸥，小海鸥找不到回家的路了。\n"
        "泡泡用彩虹泡泡裹住小海鸥，顺着月亮的光，把它送回了海边的家。\n"
        "小海鸥开心地说：「谢谢你，泡泡！」泡泡摆摆尾巴说：「帮助别人，连做梦都会笑呢。」\n"
        "天亮了，泡泡醒来，觉得心里暖暖的——这真是一个会飞的、甜甜的梦。"
    )
    co_created = now - timedelta(days=2)

    def _co_ts(hour: int, minute: int) -> str:
        return co_created.replace(hour=hour, minute=minute, second=0).isoformat(
            timespec="seconds"
        )

    db.add(
        CocreationStory(
            child_user_id=kid.id,
            parent_user_id=parent.id,
            title="会飞的小鲸鱼",
            status="done",
            turns=[
                {"role": "ai", "kind": "opening", "content": co_opening, "ts": _co_ts(19, 0)},
                {"role": "child", "kind": "text", "content": co_child_1, "ts": _co_ts(19, 5)},
                {"role": "ai", "kind": "guide", "content": "接下来会发生什么呀？", "ts": _co_ts(19, 5)},
                {"role": "child", "kind": "text", "content": co_child_2, "ts": _co_ts(19, 12)},
                {"role": "ai", "kind": "guide", "content": "这时候，它会怎么帮它呢？", "ts": _co_ts(19, 12)},
                {"role": "parent", "kind": "text", "content": co_parent_1, "ts": _co_ts(19, 20)},
                {"role": "ai", "kind": "guide", "content": "哇，然后呢然后呢？", "ts": _co_ts(19, 20)},
            ],
            final_text=co_final,
            shared_with_parent=True,
            created_at=co_created,
        )
    )
    # 与「完成润色自动种星球」效果一致的星球条目（source="cocreation"）
    db.add(
        PlanetEntry(
            user_id=kid.id,
            type="story",
            title="会飞的小鲸鱼",
            content=co_final,
            tags=["故事", "共创"],
            source="cocreation",
            date=_cn_date(co_created),
            created_at=co_created,
        )
    )

    db.commit()
    print("演示数据已写入：demo_kid (PIN 1234) / demo_parent (PIN 0000)")
    return True


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
