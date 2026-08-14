"""情节记忆 (Episodic Memory) — 三层记忆架构 Tier 2

每轮对话结束后，调用轻量 LLM 自动生成结构化摘要。原始对话文本丢弃，
仅保留摘要（符合数据最小化原则）。摘要用于跨会话个性化 + 苏格拉底引导。

存储：JSON 文件，最多 200 条，30 天滚动窗口。
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional

from .age_tiers import normalize_age_tier

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class EpisodeSummary:
    """单轮对话的情节摘要"""
    timestamp: str                     # ISO datetime
    topics: list[str]                  # ["天文", "光的散射"]
    knowledge_gaps: list[str]          # ["还没理解'波长'的概念"]
    emotion_trend: str                 # "positive" | "neutral" | "slightly_negative" | "negative"
    socratic_hints: list[str]          # ["用比喻效果好", "喜欢恐龙类比"]
    interest_signals: list[str]        # ["主动追问了两次", "说'好神奇'"]
    child_age_tier: str                # "5-7" | "8-10" | "11-13" | "14"（旧档见 core/age_tiers）

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EpisodeSummary":
        return cls(
            timestamp=d.get("timestamp", ""),
            topics=d.get("topics", []) or [],
            knowledge_gaps=d.get("knowledge_gaps", []) or [],
            emotion_trend=d.get("emotion_trend", "neutral"),
            socratic_hints=d.get("socratic_hints", []) or [],
            interest_signals=d.get("interest_signals", []) or [],
            child_age_tier=normalize_age_tier(d.get("child_age_tier")),
        )


# ---------------------------------------------------------------------------
# 存储路径管理
# ---------------------------------------------------------------------------
MAX_EPISODES = 200
RETENTION_DAYS = 30

_store_path: Optional[str] = None


def init_store(path: str) -> None:
    """初始化情节记忆存储路径。在应用启动时调用一次。

    Args:
        path: JSON 文件路径，或 ":memory:" 使用内存存储（部署环境）
    """
    global _store_path
    _store_path = path

    if path == ":memory:":
        # 内存模式：初始化空列表
        _save_episodes([])
        return

    # 文件模式：加载已有数据并清理过期条目
    if os.path.exists(path):
        cleanup()
    else:
        _save_episodes([])


# 内存存储（部署环境用）
_memory_store: list[dict] = []


def _load_episodes() -> list[dict]:
    """从存储加载所有情节摘要（文件或内存）"""
    global _memory_store
    if _store_path == ":memory:":
        return _memory_store
    if not _store_path or not os.path.exists(_store_path):
        return []
    try:
        with open(_store_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _save_episodes(episodes: list[dict]) -> None:
    """保存情节摘要到存储（文件或内存）"""
    global _memory_store
    if _store_path == ":memory:":
        _memory_store = episodes
        return
    if not _store_path:
        return
    try:
        os.makedirs(os.path.dirname(_store_path), exist_ok=True)
        with open(_store_path, "w", encoding="utf-8") as f:
            json.dump(episodes, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# 摘要生成（调用轻量 LLM）
# ---------------------------------------------------------------------------
_SUMMARY_SYSTEM_PROMPT = """你是一个儿童对话记忆摘要器。根据一轮对话的输入和输出，输出一个 JSON 摘要。

规则：
- topics: 这轮对话涉及的 1-3 个知识主题（如"天文""数学""情绪"）。如果没有明显知识主题，写 ["日常聊天"]
- knowledge_gaps: 孩子可能还没完全理解的概念（空列表或 1-2 个），没有则 []
- emotion_trend: 孩子在这轮对话中的情绪色彩——"positive" / "neutral" / "slightly_negative" / "negative"
- socratic_hints: 关于引导方式的观察（如"用比喻效果好""对恐龙类话题特别感兴趣"），没有则 []
- interest_signals: 孩子表现出兴趣的信号（如"主动追问""说好神奇""想了解更多"），没有则 []

严格输出 JSON，不要任何其他文字：
{"topics": [...], "knowledge_gaps": [...], "emotion_trend": "...", "socratic_hints": [...], "interest_signals": [...]}"""


def _rule_summarize(
    user_input: str,
    ai_reply: str,
    age_tier: str,
    mode: str,
    topics: Optional[list[str]] = None,
) -> EpisodeSummary:
    """规则版摘要生成（LLM 不可用时的兜底）

    基于关键词匹配 + 简单情绪检测，不调 LLM。
    质量低于 LLM 版，但保证了情节记忆永不丢失——
    即使没有 API Key 也能积累跨会话个性化上下文。
    """
    # -- 1. 主题提取：匹配预定义主题词库 --
    _TOPIC_KEYWORDS: dict[str, list[str]] = {
        "天文": ["天空", "星星", "太阳", "月亮", "宇宙", "地球", "行星", "黑洞", "银河"],
        "动物": ["动物", "恐龙", "小猫", "小狗", "兔子", "鸟", "鱼", "大象", "蚂蚁"],
        "数学": ["数学", "计算", "数字", "题目", "加法", "减法", "乘法", "除法", "算式"],
        "物理": ["光", "颜色", "声音", "力", "速度", "重力", "浮力", "电", "磁"],
        "自然": ["天气", "雨", "风", "云", "彩虹", "火山", "地震", "海洋", "森林"],
        "情绪": ["难过", "开心", "生气", "害怕", "孤独", "紧张", "委屈", "焦虑"],
        "学习": ["作业", "考试", "题目", "学习", "课本", "成绩", "作文", "笔记"],
        "故事": ["故事", "童话", "讲个", "从前", "主人公", "结局"],
        "安全": ["安全", "保护", "危险", "陌生人", "求助", "小心", "遇到危险"],
        "社交": ["朋友", "同学", "老师", "爸爸妈妈", "家人", "邻居", "同桌"],
        "科技": ["电脑", "手机", "机器人", "AI", "互联网", "编程"],
        "艺术": ["画画", "唱歌", "音乐", "颜色", "舞蹈", "手工"],
    }
    found_topics = list(topics) if topics else []
    combined = user_input + ai_reply[:200]
    for topic, kws in _TOPIC_KEYWORDS.items():
        if any(kw in combined for kw in kws):
            if topic not in found_topics:
                found_topics.append(topic)
    if not found_topics:
        found_topics = ["日常聊天"]

    # -- 2. 情绪检测：简单正/负向词计数 --
    _POSITIVE = ["开心", "高兴", "喜欢", "有趣", "好神奇", "太棒", "哈哈", "谢谢",
                 "好玩", "酷", "厉害", "棒", "了不起", "有趣", "神奇", "惊喜"]
    _NEGATIVE = ["难过", "伤心", "生气", "害怕", "孤独", "不开心", "没意思", "烦",
                 "讨厌", "无聊", "哭", "痛苦", "担心", "焦虑", "委屈", "绝望"]

    pos_count = sum(1 for w in _POSITIVE if w in user_input)
    neg_count = sum(1 for w in _NEGATIVE if w in user_input)

    if neg_count > pos_count + 1:
        emotion = "negative" if neg_count >= 3 else "slightly_negative"
    elif pos_count > neg_count + 1:
        emotion = "positive"
    else:
        emotion = "neutral"

    # -- 3. 知识缺口检测：孩子可能不理解的概念 --
    _GAP_SIGNALS = ["不知道", "不懂", "不明白", "不会", "什么是", "为什么", "怎么做到的"]
    gaps = []
    for signal in _GAP_SIGNALS:
        if signal in user_input:
            # 提取信号后的关键词作为可能的 gap
            idx = user_input.find(signal)
            gap_context = user_input[idx:idx + 30]
            gaps.append(gap_context.replace(signal, "").strip("？?，。 "))
    knowledge_gaps = gaps[:2] if gaps else []

    # -- 4. 兴趣信号检测 --
    _INTEREST_SIGNALS = ["为什么", "好神奇", "再讲", "然后呢", "还想听", "后来呢",
                         "太有趣了", "我想学", "教我"]
    interest = [s for s in _INTEREST_SIGNALS if s in user_input]

    # -- 5. 苏格拉底引导提示 --
    socratic_hints = []
    if mode == "encyclopedia":
        socratic_hints.append("知识探索模式")
    if any(kw in user_input for kw in ["比喻", "像", "比如"]):
        socratic_hints.append("对类比/比喻有良好反应")

    return EpisodeSummary(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        topics=found_topics[:3],
        knowledge_gaps=knowledge_gaps,
        emotion_trend=emotion,
        socratic_hints=socratic_hints,
        interest_signals=interest,
        child_age_tier=age_tier,
    )


def summarize_conversation(
    user_input: str,
    ai_reply: str,
    age_tier: str,
    mode: str,
    topics: Optional[list[str]] = None,
) -> Optional[EpisodeSummary]:
    """调用轻量 LLM 为本轮对话生成情节摘要

    LLM 可用时调用 LLM；不可用时回退到规则版摘要。
    规则版摘要质量低于 LLM 版，但保证了情节记忆永不丢失。

    Args:
        user_input: 孩子本轮输入
        ai_reply: AI 本轮回复
        age_tier: "5-7" | "8-10" | "11-13" | "14"（旧档自动映射）
        mode: chat | story | encyclopedia | emotion
        topics: 已提取的话题标签（来自 Step 2），可选

    Returns:
        EpisodeSummary，仅在极端异常时返回 None
    """
    from . import llm_client

    # -- 优先尝试 LLM 摘要 --
    if llm_client.is_llm_available():
        topic_hint = f"已知话题标签：{', '.join(topics)}" if topics else ""
        user_prompt = (
            f"孩子（{age_tier}岁，{mode}模式）：{user_input[:300]}\n"
            f"AI回复摘要：{ai_reply[:200]}\n"
            f"{topic_hint}"
        )

        try:
            raw = llm_client.chat_complete(
                messages=[
                    {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=200,
            )
            data = _try_parse_json(raw)
            if data:
                return EpisodeSummary(
                    timestamp=datetime.now().isoformat(timespec="seconds"),
                    topics=data.get("topics", []) or [],
                    knowledge_gaps=data.get("knowledge_gaps", []) or [],
                    emotion_trend=data.get("emotion_trend", "neutral"),
                    socratic_hints=data.get("socratic_hints", []) or [],
                    interest_signals=data.get("interest_signals", []) or [],
                    child_age_tier=age_tier,
                )
        except Exception:
            logger.warning("情节摘要 LLM 调用失败，回退规则版摘要", exc_info=True)

    # -- 规则版兜底：情节记忆不丢失 --
    return _rule_summarize(user_input, ai_reply, age_tier, mode, topics)


def _try_parse_json(text: str) -> Optional[dict]:
    """从 LLM 输出中提取 JSON 对象（容忍前后多余文字）"""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


# ---------------------------------------------------------------------------
# 存储与检索
# ---------------------------------------------------------------------------
def store_episode(summary: EpisodeSummary) -> None:
    """存储一条情节摘要，触发自动清理"""
    episodes = _load_episodes()
    episodes.append(summary.to_dict())

    # 超过容量限制时裁剪最旧的
    if len(episodes) > MAX_EPISODES:
        episodes = episodes[-MAX_EPISODES:]

    _save_episodes(episodes)
    cleanup()


def retrieve_recent(days: int = 7, limit: int = 10) -> list[EpisodeSummary]:
    """检索最近 N 天的情节摘要

    Args:
        days: 回溯天数
        limit: 最多返回条数

    Returns:
        EpisodeSummary 列表（按时间倒序）
    """
    episodes = _load_episodes()
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_iso = cutoff.isoformat(timespec="seconds")

    recent = [e for e in episodes if e.get("timestamp", "") >= cutoff_iso]
    summaries = [EpisodeSummary.from_dict(e) for e in recent[-limit:]]
    summaries.reverse()  # 反转为时间倒序（最新在前），与返回值 docstring 约定一致
    return summaries


def rank_episodes(
    user_input: str, episodes: list[EpisodeSummary], limit: int = 8
) -> list[EpisodeSummary]:
    """按用户输入关键词为摘要列表做相关性排序（供各存储后端复用）

    关键词匹配评分：topic 匹配 +2, knowledge_gap 匹配 +3, interest 匹配 +1。
    无关键词时按时间倒序返回最近 limit 条（episodes 需为时间正序）。

    Args:
        user_input: 用户当前输入
        episodes: 候选摘要（时间正序）
        limit: 最多返回条数
    """
    from .memory_manager import _extract_keywords

    input_kw = _extract_keywords(user_input)
    if not input_kw:
        return list(reversed(episodes[-limit:]))

    scored: list[tuple[int, EpisodeSummary]] = []
    for summary in episodes:
        score = 0
        for topic in summary.topics:
            topic_kw = _extract_keywords(topic)
            score += len(input_kw & topic_kw) * 2
        for gap in summary.knowledge_gaps:
            gap_kw = _extract_keywords(gap)
            score += len(input_kw & gap_kw) * 3
        for hint in summary.interest_signals:
            hint_kw = _extract_keywords(hint)
            score += len(input_kw & hint_kw) * 1

        if score > 0:
            scored.append((score, summary))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:limit]]


def retrieve_by_topic(user_input: str, days: int = 14, limit: int = 8) -> list[EpisodeSummary]:
    """根据用户输入关键词检索相关情节摘要（全局 JSON 存储）

    用简易关键词匹配（与 memory_manager 一致，不调 LLM）。
    """
    from .memory_manager import _extract_keywords

    input_kw = _extract_keywords(user_input)
    if not input_kw:
        return retrieve_recent(days=7, limit=5)

    episodes = _load_episodes()
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_iso = cutoff.isoformat(timespec="seconds")

    recent = [
        EpisodeSummary.from_dict(e)
        for e in episodes
        if e.get("timestamp", "") >= cutoff_iso
    ]
    return rank_episodes(user_input, recent, limit=limit)


def build_episodic_context(episodes: list[EpisodeSummary]) -> Optional[str]:
    """将情节摘要列表构建为 Prompt 注入文本

    Args:
        episodes: 情节摘要列表

    Returns:
        注入 Prompt 的文本，无有效摘要时返回 None
    """
    if not episodes:
        return None

    # 聚合所有摘要
    all_topics: list[str] = []
    all_gaps: list[str] = []
    all_hints: list[str] = []
    emotion_counts: dict[str, int] = {}

    for ep in episodes:
        all_topics.extend(ep.topics)
        all_gaps.extend(ep.knowledge_gaps)
        all_hints.extend(ep.socratic_hints)
        emotion_counts[ep.emotion_trend] = emotion_counts.get(ep.emotion_trend, 0) + 1

    # 去重 + 取高频
    unique_topics = list(dict.fromkeys(all_topics))[:6]  # 去重保序
    unique_gaps = list(dict.fromkeys(all_gaps))[:3]
    unique_hints = list(dict.fromkeys(all_hints))[:3]

    # 主导情绪
    dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"
    emotion_labels = {
        "positive": "稳定偏积极",
        "neutral": "平稳",
        "slightly_negative": "略有低落",
        "negative": "需要关注",
    }

    lines: list[str] = ["## 情节记忆（最近对话摘要，作为对话背景参考）"]

    if unique_topics:
        lines.append(f"· 最近探索的知识主题：{'、'.join(unique_topics)}")
    if unique_gaps:
        lines.append(f"· 已知理解障碍：{'；'.join(unique_gaps)}")
    if unique_hints:
        lines.append(f"· 有效的引导方式：{'；'.join(unique_hints)}")
    lines.append(f"· 近期情绪基线：{emotion_labels.get(dominant_emotion, dominant_emotion)}")

    lines.append("\n——以上为背景信息，当话题自然相关时才引用，不要刻意提及。")

    return "\n".join(lines)


def cleanup() -> int:
    """删除超过 RETENTION_DAYS 天的旧情节摘要

    Returns:
        删除的条目数
    """
    episodes = _load_episodes()
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    cutoff_iso = cutoff.isoformat(timespec="seconds")

    before = len(episodes)
    kept = [e for e in episodes if e.get("timestamp", "") >= cutoff_iso]
    after = len(kept)

    if before != after:
        _save_episodes(kept)

    return before - after


def count_episodes() -> int:
    """返回当前情节记忆条目数"""
    return len(_load_episodes())


def get_emotion_trend(days: int = 7) -> dict:
    """获取最近 N 天的情绪趋势统计

    Returns:
        {"positive": N, "neutral": N, "slightly_negative": N, "negative": N}
    """
    episodes = retrieve_recent(days=days)
    counts = {"positive": 0, "neutral": 0, "slightly_negative": 0, "negative": 0}
    for ep in episodes:
        if ep.emotion_trend in counts:
            counts[ep.emotion_trend] += 1
    return counts
