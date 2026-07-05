"""Step 0: 记忆检索 + 前置过滤（纯 Python，不调 LLM）

依据 docs/安心童伴AI-步骤详解.md 中 Step 0 的逻辑实现。
读 JSON → 标签/内容主题交集判断 → 排序取前 3-5 条 → 生成记忆上下文片段。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


# 类型到中文名+图标的映射
TYPE_META = {
    "star":   {"label": "好奇星", "icon": "⭐"},
    "cloud":  {"label": "心情云", "icon": "☁️"},
    "sprout": {"label": "勇敢芽", "icon": "🌱"},
    "story":  {"label": "故事册", "icon": "📖"},
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
    for entry_type in ["stars", "clouds", "sprouts", "stories", "star", "cloud", "sprout", "story"]:
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
    return f"{prefix}{next_num}"


def create_entry(planet: dict, entry: dict) -> dict:
    """向 planet 中新增一条条目，返回更新后的 entry（含 id）"""
    if not planet:
        planet = {}
    entry_type = entry.get("type", "star")
    plural_key = entry_type + "s" if not entry_type.endswith("s") else entry_type
    items = planet.setdefault(plural_key, [])

    prefix = entry_type[:2] if entry_type else "en"
    if "id" not in entry or not entry["id"]:
        entry["id"] = _next_id(items, prefix)
    if "date" not in entry or not entry["date"]:
        entry["date"] = datetime.now().strftime("%-m月%d日") if hasattr(datetime, "strftime") else datetime.now().strftime("%m月%d日").lstrip("0")

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
    counts = {"star": 0, "cloud": 0, "sprout": 0, "story": 0, "total": 0}
    if not planet:
        return counts
    for entry_type in ["star", "cloud", "sprout", "story"]:
        plural = entry_type + "s"
        n = len(planet.get(plural, []) or [])
        counts[entry_type] = n
        counts["total"] += n
    return counts
