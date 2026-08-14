"""Step 0: 记忆检索 + 前置过滤（纯 Python，不调 LLM）

依据 docs/安心童伴AI-步骤详解.md 中 Step 0 的逻辑实现。
读 JSON → 标签/内容主题交集判断 → 排序取前 3-5 条 → 生成记忆上下文片段。
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


# 类型到中文名+图标的映射
TYPE_META = {
    "star":    {"label": "好奇星", "icon": "⭐"},
    "cloud":   {"label": "心情云", "icon": "☁️"},
    "sprout":  {"label": "探索芽", "icon": "🌱"},
    "story":   {"label": "故事册", "icon": "📖"},
    "capsule": {"label": "时间胶囊", "icon": "✉️"},
}

# 简单停用词，避免"的/了/是"等无意义词成为关键词
_STOPWORDS = set("的我你他她它们是了在也有就和都还呀啊哦呢吗吧么这不那".split())
_PUNCT = set("，。、！？；：""''\"'（）《》【】 \t\n\r,.;:!?()[]{}<>")


def _extract_keywords(text: str) -> set[str]:
    """简易关键词提取：按标点切分后过滤停用词，保留长度≥2 的片段"""
    if not text:
        return set()
    # 用非汉字/字母数字字符切分
    tokens = re.split(r"[^\u4e00-\u9fa5a-zA-Z0-9]+", text)
    keywords: set[str] = set()
    for tok in tokens:
        tok = tok.strip()
        if not tok or tok in _STOPWORDS:
            continue
        if len(tok) >= 2:
            keywords.add(tok)
    return keywords


def _parse_date(date_str: str) -> Optional[datetime]:
    """尝试解析多种日期格式"""
    if not date_str:
        return None
    # 支持 "7月1日" / "2026-08-15" / "08-15"
    formats = ["%Y-%m-%d", "%m-%d", "%Y/%m/%d", "%m月%d日"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # 缺年份时补当前年
            if "%Y" not in fmt:
                dt = dt.replace(year=datetime.now().year)
            return dt
        except ValueError:
            continue
    return None


def _priority_score(entry: dict, mode: str) -> int:
    """检索优先级评分：最近 7 天 +30 / 30 天 +10 / "重要"标签 +20 / 同类型 +15"""
    base = 0
    dt = _parse_date(entry.get("date", ""))
    if dt:
        days_ago = (datetime.now() - dt).days
        if days_ago < 7:
            base += 30
        elif days_ago < 30:
            base += 10
    tags = entry.get("tags", []) or []
    if "重要" in tags:
        base += 20
    # 同类型：mode 与 entry 类型对应关系
    mode_to_type = {
        "chat": None,
        "story": "story",
        "encyclopedia": "star",
        "emotion": "cloud",
    }
    if mode_to_type.get(mode) == entry.get("type"):
        base += 15
    return base


@dataclass
class MemoryRetrieval:
    retrieved: bool
    entries: list[dict]
    context_text: Optional[str]  # 注入 Prompt 的文本


def _flatten_planet(planet: dict) -> list[dict]:
    """把 planet dict 中各类别的条目拍平成统一列表，附带 type 字段"""
    flat: list[dict] = []
    if not planet:
        return flat
    for entry_type in ["stars", "clouds", "sprouts", "stories", "capsules",
                        "star", "cloud", "sprout", "story", "capsule"]:
        items = planet.get(entry_type, [])
        if not items:
            continue
        # 标准化 key：单数 → 复数
        norm_type = entry_type.rstrip("s") if entry_type.endswith("s") else entry_type
        for item in items:
            if isinstance(item, dict):
                item_copy = dict(item)
                item_copy.setdefault("type", norm_type)
                flat.append(item_copy)
    return flat


def should_retrieve(user_input: str, planet: dict, mode: str = "chat", limit: int = 5) -> MemoryRetrieval:
    """检查用户输入与星球条目的主题交集

    Args:
        user_input: 用户当前输入
        planet: 完整星球数据（含 stars/clouds/sprouts/stories 各列表）
        mode: 当前对话模式
        limit: 最多注入条目数

    Returns:
        MemoryRetrieval
    """
    all_entries = _flatten_planet(planet)
    if not all_entries:
        return MemoryRetrieval(retrieved=False, entries=[], context_text=None)

    input_keywords = _extract_keywords(user_input)
    if not input_keywords:
        return MemoryRetrieval(retrieved=False, entries=[], context_text=None)

    matched: list[dict] = []
    for entry in all_entries[-30:]:  # 只看最近 30 条
        entry_keywords = set(entry.get("tags", []) or [])
        entry_keywords |= _extract_keywords(entry.get("title", ""))
        entry_keywords |= _extract_keywords(entry.get("content", ""))
        entry_keywords |= _extract_keywords(entry.get("preview", ""))

        if input_keywords & entry_keywords:
            matched.append(entry)

    if not matched:
        return MemoryRetrieval(retrieved=False, entries=[], context_text=None)

    # 排序取前 N 条
    matched.sort(key=lambda e: _priority_score(e, mode), reverse=True)
    top = matched[:limit]

    # 生成记忆上下文文本
    lines: list[str] = []
    for e in top:
        meta = TYPE_META.get(e.get("type", ""), {"label": "条目", "icon": "•"})
        date = e.get("date", "")
        title = e.get("title", "（未命名）")
        tags = ", ".join(e.get("tags", []) or [])
        tag_str = f"[标签：{tags}]" if tags else ""
        lines.append(f"{meta['icon']}{meta['label']}({date})：{title} {tag_str}".rstrip())

    context_text = "以下是孩子之前记录的星球记忆，可作为对话背景参考：\n" + "\n".join(lines)
    return MemoryRetrieval(retrieved=True, entries=top, context_text=context_text)


# ---------------------------------------------------------------------------
# 星球 CRUD（纯 Python，操作内存 dict）
# ---------------------------------------------------------------------------
def _next_id(entries: list[dict], prefix: str) -> str:
    existing_nums = []
    for e in entries:
        eid = e.get("id", "")
        if isinstance(eid, str) and eid.startswith(prefix):
            try:
                existing_nums.append(int(eid[len(prefix):]))
            except ValueError:
                continue
    next_num = (max(existing_nums) + 1) if existing_nums else 1
    # max+1 计数在并发下有竞态，附短 UUID 后缀保证唯一（旧格式数字 ID 仍可被本函数解析）
    return f"{prefix}{next_num}_{uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------------------------
# 探索芽验证逻辑
# 探索芽记录真实世界中的事件和经历——勇敢行动、有趣发现、新鲜经历
# 不记录纯 AI 聊天内容（那是和虚拟世界的互动，不是真实世界的事件）
# ---------------------------------------------------------------------------

# 现实行动关键词（探索芽关心的内容）
_REAL_WORLD_ACTION_KEYWORDS = [
    "告诉", "找", "主动", "和妈妈说", "和爸爸说", "跟妈妈说", "跟爸爸说",
    "老师", "同学", "朋友", "求助", "说出来", "面对", "尝试", "第一次",
    "自己做了", "学会了", "做到了", "鼓起勇气", "迈出", "跨出",
    "去问了", "打电话", "写了信", "参加了", "举手", "上台",
    "道歉了", "原谅了", "帮助了", "分享了", "保护了", "站出来",
    # 新增：探索发现类的现实行动
    "发现了", "捡到了", "看到", "遇到了", "去了", "吃了",
    "做了", "画了", "写完了", "完成了", "拿到了", "赢得了",
    "学会了", "记住了", "参观了", "旅行", "去了公园", "去了博物馆",
    "跑步", "跳绳", "游泳", "打球", "骑车", "爬山",
]

# AI 聊天信号（不是现实世界事件，不适合作为探索芽内容）
_AI_ONLY_SIGNALS = [
    "AI", "机器人", "安心童伴", "聊天机器人", "语音助手",
    "和AI聊天", "跟AI说", "问了AI", "和AI说", "AI回答",
    "聊了天", "和AI", "跟机器人", "对AI",
]


def validate_sprout_entry(title: str, content: str = "") -> dict:
    """验证探索芽条目内容是否记录真实世界事件

    设计哲学：
    探索芽记录真实世界中的经历和事件——勇敢的行动、有趣的发现、新鲜的体验。
    值得记住的回忆在真实世界里，不在 AI 里。

    Returns:
        {
            "valid": bool,            # 是否通过验证
            "confidence": str,        # "high" | "low"
            "message": str,           # 提示信息（仅在 valid=False 时有意义）
            "suggested_type": str|None,  # 建议改为的条目类型
        }
    """
    combined = title + content

    # 检测现实行动/事件信号
    has_real_action = any(kw in combined for kw in _REAL_WORLD_ACTION_KEYWORDS)

    # 检测 AI 聊天信号
    has_ai_signal = any(kw in combined for kw in _AI_ONLY_SIGNALS)

    # 明显是 AI 聊天内容 → 建议改为心情云
    if has_ai_signal and not has_real_action:
        return {
            "valid": False,
            "confidence": "high",
            "message": (
                "🌱 探索芽是用来记录**真实世界**里的经历和发现哦——\n\n"
                "比如「我告诉了老师同学推我的事」「在公园发现了一种没见过的虫子」「第一次自己坐地铁」。\n\n"
                "和 AI 聊天是很开心，但值得记住的回忆在真实世界里。\n"
                "要不要试试把这个记录改成**心情云**或**故事册**？"
            ),
            "suggested_type": "cloud",
        }

    # 既无现实信号也无 AI 信号 → 温和提示写得更具体
    if not has_real_action and not has_ai_signal:
        return {
            "valid": False,
            "confidence": "low",
            "message": (
                "🌱 探索芽是记录你在**真实世界**里的经历和发现的地方。\n\n"
                "比如：第一次上台发言、在路边发现了一只特别的虫子、周末跟爸爸去钓鱼、"
                "跳绳破了昨天的记录、告诉了老师一件困扰你的事……\n\n"
                "你写的这个内容，有没有在真实世界里发生呢？\n"
                "如果有，可以写得更具体一点——发生了什么？在哪里？和谁一起？"
            ),
            "suggested_type": None,
        }

    # 包含现实行动信号 → 通过
    return {
        "valid": True,
        "confidence": "high",
        "message": "",
        "suggested_type": None,
    }


def create_entry(planet: dict, entry: dict) -> dict:
    """向 planet 中新增一条条目，返回更新后的 entry（含 id）

    对于探索芽 (sprout) 类型，会进行内容验证：
    - 通过验证 → _validation.valid = True，正常保存
    - 未通过 → _validation.valid = False，条目仍保存，
      但 _validation.message 包含提示信息，由调用方决定如何展示
    """
    if not planet:
        planet = {}
    entry_type = entry.get("type", "star")

    # 探索芽验证
    if entry_type == "sprout":
        validation = validate_sprout_entry(
            entry.get("title", ""),
            entry.get("content", ""),
        )
        if not validation["valid"]:
            # 验证失败：条目仍保存（不丢失孩子写的内容），但附带验证信息
            # 调用方（页面）应展示 _validation.message 并给出类型修改建议
            entry["_validation"] = validation

    plural_key = entry_type + "s" if not entry_type.endswith("s") else entry_type
    items = planet.setdefault(plural_key, [])

    prefix = entry_type[:2] if entry_type else "en"
    if "id" not in entry or not entry["id"]:
        entry["id"] = _next_id(items, prefix)
    if "date" not in entry or not entry["date"]:
        entry["date"] = datetime.now().strftime("%m月%d日").lstrip("0")

    items.append(entry)
    return entry


def delete_entry(planet: dict, entry_id: str) -> bool:
    """按 id 删除条目，返回是否删除成功"""
    if not planet:
        return False
    for key, items in planet.items():
        for i, e in enumerate(items):
            if e.get("id") == entry_id:
                items.pop(i)
                return True
    return False


def count_entries(planet: dict) -> dict:
    """统计各类别条目数，用于家长端星球概览"""
    counts = {"star": 0, "cloud": 0, "sprout": 0, "story": 0, "capsule": 0, "total": 0}
    if not planet:
        return counts
    for entry_type in ["star", "cloud", "sprout", "story", "capsule"]:
        plural = entry_type + "s"
        n = len(planet.get(plural, []) or [])
        counts[entry_type] = n
        counts["total"] += n
    return counts


# ---------------------------------------------------------------------------
# 星球生态可视化：天气 + 生态描述
# ---------------------------------------------------------------------------
def _is_recent(date_str: str, days: int = 7) -> bool:
    """判断日期是否在最近 N 天内"""
    dt = _parse_date(date_str)
    if dt is None:
        return False
    return (datetime.now() - dt).days < days


def get_planet_weather(planet: dict) -> dict:
    """根据最近心情云的情绪分布，返回星球天气描述

    Returns:
        {"weather": str, "emoji": str, "text": str, "description": str}
    """
    clouds = planet.get("clouds", []) if planet else []
    if not clouds:
        return {
            "weather": "sunny", "emoji": "☀️",
            "text": "晴朗", "description": "小星球天空晴朗，还没有云朵飘过。去种下第一朵心情云吧～"
        }

    # 取最近 7 天的心情云，不足 3 条则取最近 3 条
    recent = [c for c in clouds if _is_recent(c.get("date", ""), days=7)]
    source = recent if recent else clouds[-3:]

    moods = [c.get("mood", "pink") for c in source]
    pink = sum(1 for m in moods if m == "pink")
    blue = sum(1 for m in moods if m == "blue")
    gray = sum(1 for m in moods if m == "gray")
    yellow = sum(1 for m in moods if m == "yellow")
    total = len(moods)

    # 温暖的情绪多 → 好天气
    if pink >= total * 0.6:
        return {"weather": "rainbow", "emoji": "\U0001f308", "text": "彩虹心情",
                "description": "最近的心情像彩虹一样明亮温暖。"}
    if yellow >= total * 0.6:
        return {"weather": "sunny", "emoji": "☀️", "text": "阳光灿烂",
                "description": "小星球阳光灿烂，最近心里暖暖的。"}
    if pink + yellow >= total * 0.6:
        return {"weather": "partly_sunny", "emoji": "\U0001f324️", "text": "晴间多云",
                "description": "小星球大部分时候很明亮，偶尔飘过几朵云。"}
    if blue >= total * 0.6:
        return {"weather": "light_rain", "emoji": "\U0001f327️", "text": "下着小雨",
                "description": "最近心里好像藏了一些小水滴，没关系，雨后会天晴的。"}
    if gray >= total * 0.5:
        return {"weather": "cloudy", "emoji": "☁️", "text": "多云",
                "description": "云层有点厚，但每一朵云都在变化，不会一直停在同一个地方。"}
    # 混合情绪 → 温和中性
    return {"weather": "partly_cloudy", "emoji": "⛅", "text": "晴间多云",
            "description": "小星球上有阳光也有云朵，这就是最真实的天空。"}


def get_planet_ecosystem(planet: dict) -> dict:
    """返回星球生态全景描述（温暖的自然语言，无数字化）

    Returns:
        {"weather": ..., "elements": [{"icon": str, "label": str, "desc": str}, ...]}
    """
    weather = get_planet_weather(planet)

    def _count(key: str) -> int:
        items = planet.get(key, []) if planet else []
        return len(items) if items else 0

    star_n = _count("stars")
    cloud_n = _count("clouds")
    sprout_n = _count("sprouts")
    story_n = _count("stories")

    # 构建温暖的生态描述
    def _star_desc(n: int) -> str:
        if n == 0:
            return "天还没黑，等待第一颗星星亮起来 ✨"
        return f"天上有 {n} 颗星星在闪烁"

    def _cloud_desc(n: int) -> str:
        if n == 0:
            return "天空很干净，还没有云朵飘过"
        return f"飘着 {n} 朵云"

    def _sprout_desc(n: int) -> str:
        if n == 0:
            return "土地松软，等待第一棵小芽破土 \U0001f331"
        return f"长出了 {n} 棵小芽"

    def _story_desc(n: int) -> str:
        if n == 0:
            return "书架上还空着，等待第一个故事住进来 \U0001f4d6"
        return f"收藏了 {n} 个小故事"

    elements = [
        {"icon": "⭐", "label": "好奇星", "desc": _star_desc(star_n)},
        {"icon": "☁️", "label": "心情云", "desc": _cloud_desc(cloud_n)},
        {"icon": "\U0001f331", "label": "探索芽", "desc": _sprout_desc(sprout_n)},
        {"icon": "\U0001f4d6", "label": "故事册", "desc": _story_desc(story_n)},
    ]

    return {"weather": weather, "elements": elements}


# ---------------------------------------------------------------------------
# 时间胶囊 CRUD
# ---------------------------------------------------------------------------
def _next_capsule_id(capsules: list[dict]) -> str:
    existing_nums = []
    for c in capsules:
        cid = c.get("id", "")
        if isinstance(cid, str) and cid.startswith("ca"):
            try:
                existing_nums.append(int(cid[2:]))
            except ValueError:
                continue
    next_num = (max(existing_nums) + 1) if existing_nums else 1
    return f"ca{next_num}"


def create_capsule(planet: dict, capsule: dict) -> dict:
    """向 planet 中新增一条时间胶囊

    胶囊数据格式：
        {title, content, unlock_at (str date "M月D日" or "YYYY-MM-DD"),
         tags: list[str] (optional)}

    Returns 更新后的胶囊条目（含 id / type / created_at / unlocked）
    """
    if not planet:
        planet = {}
    capsules = planet.setdefault("capsules", [])

    if "id" not in capsule or not capsule["id"]:
        capsule["id"] = _next_capsule_id(capsules)
    capsule.setdefault("type", "capsule")
    capsule.setdefault("created_at", datetime.now().strftime("%m月%d日").lstrip("0"))
    capsule.setdefault("unlocked", False)

    capsules.append(capsule)
    return capsule


def check_capsules(planet: dict) -> list[dict]:
    """检查所有时间胶囊，自动解锁已到期的，返回新解锁的列表

    在页面加载时调用，返回的列表可用于展示解锁通知。
    """
    if not planet:
        return []
    capsules = planet.get("capsules", [])
    if not capsules:
        return []

    now = datetime.now()
    newly_unlocked: list[dict] = []

    for c in capsules:
        if c.get("unlocked", False):
            continue
        unlock_str = c.get("unlock_at", "")
        unlock_dt = _parse_date(unlock_str)
        if unlock_dt and unlock_dt <= now:
            c["unlocked"] = True
            newly_unlocked.append(c)

    return newly_unlocked


def get_capsule_countdown(capsule: dict) -> str:
    """返回胶囊的剩余天数描述（用于密封状态的卡片展示）

    Returns:
        "还有 3 天" / "明天" / "今天" / "" (已解锁或无日期)
    """
    if capsule.get("unlocked", False):
        return ""
    unlock_str = capsule.get("unlock_at", "")
    unlock_dt = _parse_date(unlock_str)
    if unlock_dt is None:
        return ""
    days_left = (unlock_dt - datetime.now()).days
    if days_left < 0:
        return "今天"
    if days_left == 0:
        return "今天"
    if days_left == 1:
        return "明天"
    return f"还有 {days_left} 天"
