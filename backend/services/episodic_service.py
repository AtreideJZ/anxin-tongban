"""情景记忆服务：SQLite 持久化 + per-user 隔离（v2.1 方案 3.4）

episodic_memories 表实现情景记忆的按用户隔离存储，解决 MVP 阶段
全局 JSON 存储导致的跨用户数据污染。

core/episodic_memory.py 保留为「摘要生成 + 上下文构建」的纯逻辑；
本服务只负责把 EpisodeSummary 读写到 SQLite，并通过
pipeline.run() 的可选回调（episodic_retriever / episodic_store /
episodic_count）接入。

注意：这些函数在 pipeline 的线程池线程中执行，调用方应传入
独立的会话（推荐用 SessionLocal() 新建，避免跨线程共享请求会话）。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from core import episodic_memory as em
from core.age_tiers import normalize_age_tier

from ..models.memory import EpisodicMemory

# 有效情绪取值（与 core/episodic_memory 的 emotion_trend 契约一致）
_EMOTION_KEYS = ("positive", "neutral", "slightly_negative", "negative")


def _row_to_summary(row: EpisodicMemory) -> em.EpisodeSummary:
    return em.EpisodeSummary(
        timestamp=row.timestamp.isoformat(timespec="seconds"),
        topics=list(row.topics or []),
        knowledge_gaps=list(row.knowledge_gaps or []),
        emotion_trend=row.emotion_trend or "neutral",
        socratic_hints=list(row.socratic_hints or []),
        interest_signals=list(row.interest_signals or []),
        child_age_tier=normalize_age_tier(row.age_tier),
    )


def store_episode(
    session: Session, user_id: int, summary: em.EpisodeSummary
) -> EpisodicMemory:
    """存储一条情节摘要（per-user）"""
    row = EpisodicMemory(
        user_id=user_id,
        timestamp=datetime.now(),
        topics=list(summary.topics or []),
        knowledge_gaps=list(summary.knowledge_gaps or []),
        emotion_trend=summary.emotion_trend or "neutral",
        socratic_hints=list(summary.socratic_hints or []),
        interest_signals=list(summary.interest_signals or []),
        age_tier=normalize_age_tier(summary.child_age_tier),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def retrieve_recent(
    session: Session, user_id: int, days: int = 7, limit: int = 10
) -> list[em.EpisodeSummary]:
    """检索某用户最近 N 天的情节摘要（时间倒序）"""
    cutoff = datetime.now() - timedelta(days=days)
    rows = (
        session.query(EpisodicMemory)
        .filter(EpisodicMemory.user_id == user_id, EpisodicMemory.timestamp >= cutoff)
        .order_by(EpisodicMemory.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [_row_to_summary(r) for r in rows]


def retrieve_by_topic(
    session: Session,
    user_id: int,
    user_input: str,
    days: int = 14,
    limit: int = 8,
) -> list[em.EpisodeSummary]:
    """按用户输入关键词检索该用户的相关情节摘要（复用 core 的评分逻辑）"""
    cutoff = datetime.now() - timedelta(days=days)
    rows = (
        session.query(EpisodicMemory)
        .filter(EpisodicMemory.user_id == user_id, EpisodicMemory.timestamp >= cutoff)
        .order_by(EpisodicMemory.timestamp.asc())  # 时间正序，rank_episodes 按此约定
        .all()
    )
    summaries = [_row_to_summary(r) for r in rows]
    return em.rank_episodes(user_input, summaries, limit=limit)


def count_episodes(session: Session, user_id: int) -> int:
    """某用户的情节记忆条目数"""
    return (
        session.query(func.count(EpisodicMemory.id))
        .filter(EpisodicMemory.user_id == user_id)
        .scalar()
        or 0
    )


def get_emotion_trend(
    session: Session, user_id: int, days: int = 7
) -> dict:
    """某用户最近 N 天的情绪趋势统计

    Returns:
        {"positive": N, "neutral": N, "slightly_negative": N, "negative": N}
    """
    cutoff = datetime.now() - timedelta(days=days)
    rows = (
        session.query(EpisodicMemory.emotion_trend)
        .filter(EpisodicMemory.user_id == user_id, EpisodicMemory.timestamp >= cutoff)
        .all()
    )
    counts = {k: 0 for k in _EMOTION_KEYS}
    for (emotion,) in rows:
        if emotion in counts:
            counts[emotion] += 1
    return counts


def aggregate_emotion_trend(
    session: Session, user_ids: list[int], days: int = 7
) -> dict:
    """聚合多个孩子（同一家长）的情绪趋势（用于未指定 child 时的家长端展示）"""
    counts = {k: 0 for k in _EMOTION_KEYS}
    if not user_ids:
        return counts
    cutoff = datetime.now() - timedelta(days=days)
    rows = (
        session.query(EpisodicMemory.emotion_trend)
        .filter(
            EpisodicMemory.user_id.in_(user_ids),
            EpisodicMemory.timestamp >= cutoff,
        )
        .all()
    )
    for (emotion,) in rows:
        if emotion in counts:
            counts[emotion] += 1
    return counts
