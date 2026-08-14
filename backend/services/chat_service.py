"""对话服务：串联 core.pipeline 与持久层（v2.1 方案 4.5）

关键流程（先审计、后伪流式）：
1. 从 DB 组装 planet dict / chat_history / parent_preferences
2. 线程池中把 core.pipeline.run() 完整跑完（含 Step 6 批判审计与 6b 拦截）
3. 持久化对话、维护 usage_minutes、跑主动预警写 parent_alerts
4. 返回 SSE 回放所需的全部数据（路由层只负责回放，不再触碰 DB）

情景记忆（方案 3.4）：per-user 隔离，pipeline 通过 episodic_* 回调
读写 SQLite（backend/services/episodic_service.py）。

【安全不变量】任何回复文本必须在 pipeline 完整结束后才离开本服务。
"""
from __future__ import annotations

import asyncio
import functools
import time
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from core import pipeline
from core import daily_challenges
from core import proactive_engine
from core import recommendation_engine as rec_engine
from core import age_tiers

from ..database import SessionLocal
from ..models.parent import ParentAlert, ParentPreference
from ..models.session import ChatSession
from ..models.user import User
from . import episodic_service
from . import planet_service

# 触发主动预警的门槛（risk_level>=2 或 pipeline 判定需要家长提醒）
_ALERT_RISK_THRESHOLD = 2

# 持久化消息上限：最近 50 轮（100 条），防止 session.messages 单行 JSON 无限膨胀
_MAX_PERSISTED_MESSAGES = 100


def _with_write_retry(fn, attempts: int = 3, base_delay: float = 0.05):
    """SQLite 并发写偶发 database is locked：短退避重试（WAL + busy_timeout 之外的保险）"""
    for i in range(attempts):
        try:
            return fn()
        except OperationalError as exc:
            if "locked" not in str(exc).lower() or i == attempts - 1:
                raise
            time.sleep(base_delay * (2**i))

# 话题/模式 → 家长可读中文（守护模式摘要用，方案 4.2）
_TOPIC_CN = {
    "safe": "日常/知识",
    "privacy_leak": "隐私安全",
    "school_bullying": "校园欺凌",
    "emotional_low": "情绪低落",
    "self_harm": "自伤",
    "ai_dependency": "AI 依赖",
    "inappropriate_content": "不适龄内容",
}
_MODE_CN = {
    "chat": "聊天",
    "story": "故事",
    "encyclopedia": "百科探索",
    "emotion": "情绪树洞",
}


def build_guardian_summary_alert(
    user: User, result: "pipeline.PipelineResult", emotion_trend: dict
) -> ParentAlert:
    """守护/过渡模式的家长摘要（方案 4.2 + v2.2 三档化：摘要频率差异化）

    守护模式（5-7 / 8-10）：每次对话后都生成一条家长可读摘要（含话题、模式、风险等级）；
    过渡模式（11-13）：同款摘要按周度节奏生成（调用方控制频率）；
    信任模式（14）不生成此类摘要，仅高风险时告警。
    """
    topic_cn = _TOPIC_CN.get(result.topic, result.topic or "日常")
    mode_cn = _MODE_CN.get(result.mode, "聊天")
    risk = result.risk_level

    if risk >= 3:
        summary = (
            f"孩子表达了高风险信号（{topic_cn}），安心童伴已使用预置危机模板回应"
            "（引导联系家人或拨打 12355），未让 AI 自由生成回复。"
        )
        suggestion = (
            "🚨 请立即与孩子沟通。如需专业心理援助，请拨打 12355 青少年服务热线"
            "（24 小时）或联系学校心理老师。"
        )
    elif risk == 2:
        summary = (
            f"孩子聊到了需要关注的「{topic_cn}」话题（{mode_cn}），"
            "安心童伴已做安全引导并安抚孩子。"
        )
        suggestion = "建议以轻松的方式关心孩子，先倾听再引导，必要时与学校老师沟通。"
    else:
        summary = (
            f"孩子与安心童伴聊了「{topic_cn}」话题（{mode_cn}），"
            "未发现风险信号。"
        )
        suggestion = "无需处理。可以陪孩子一起继续探索感兴趣的话题。"

    return ParentAlert(
        user_id=user.id,
        topic=result.topic,
        risk_level=risk,
        summary=summary,
        suggestion=suggestion,
    )


def _has_recent_notification(db: Session, user_id: int, days: int = 7) -> bool:
    """近 N 天内是否已有任意家长通知（过渡模式周度摘要的去重判据）"""
    cutoff = datetime.now() - timedelta(days=days)
    return (
        db.query(ParentAlert)
        .filter(ParentAlert.user_id == user_id, ParentAlert.timestamp >= cutoff)
        .first()
        is not None
    )


def get_or_create_session(db: Session, user_id: int) -> ChatSession:
    """每用户一条会话行，首次对话时创建"""
    session = db.query(ChatSession).filter(ChatSession.user_id == user_id).first()
    if session is None:
        session = ChatSession(user_id=user_id, messages=[])
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


def load_parent_preferences(db: Session, user_id: int) -> Optional[dict]:
    """读出家长话题偏好，组装成 guardrails.detect 期望的形状

    形状：{"limited": [...], "forbidden": [...]}，值为话题中文名列表
    （allowed_topics 暂不参与 pipeline，仅存储供前端展示）。
    """
    pref = (
        db.query(ParentPreference)
        .filter(ParentPreference.user_id == user_id)
        .first()
    )
    if pref is None:
        return None
    return {
        "limited": list(pref.limited_topics or []),
        "forbidden": list(pref.forbidden_topics or []),
    }


async def process_message(
    db: Session,
    user: User,
    message: str,
    mode: str = "chat",
) -> dict:
    """完整执行一轮对话（pipeline + 持久化 + 预警），返回 SSE 回放数据"""
    planet = planet_service.build_planet_dict(db, user.id)
    session = get_or_create_session(db, user.id)
    chat_history = list(session.messages or [])
    preferences = load_parent_preferences(db, user.id)

    # 上一轮会话模式作为 Pipeline Step 2 的意图识别先验（方案 4.1）
    # 客户端不再手动选模式；本轮回话生效模式由 Pipeline 判定并回写会话
    prev_mode = session.mode or mode or "chat"

    # per-user 情景记忆桥接（方案 3.4）：pipeline 在默认线程池执行，
    # 回调内用独立会话（SessionLocal）读写，避免跨线程共享请求会话；
    # 写操作带 locked 重试（SQLite 并发写保险）
    def _episodic_store(summary) -> None:
        def _write() -> None:
            with SessionLocal() as s:
                episodic_service.store_episode(s, user.id, summary)

        _with_write_retry(_write)

    def _episodic_retriever(user_input: str):
        with SessionLocal() as s:
            return episodic_service.retrieve_by_topic(s, user.id, user_input)

    def _episodic_count() -> int:
        with SessionLocal() as s:
            return episodic_service.count_episodes(s, user.id)

    # 线程池中同步跑完整 Pipeline（先审计、后伪流式，方案 4.5）
    loop = asyncio.get_running_loop()
    runner = functools.partial(
        pipeline.run,
        message,
        age_tiers.normalize_age_tier(user.age_tier),
        prev_mode,
        planet,
        chat_history,
        preferences,
        episodic_retriever=_episodic_retriever,
        episodic_store=_episodic_store,
        episodic_count=_episodic_count,
    )
    result: pipeline.PipelineResult = await loop.run_in_executor(None, runner)

    # 持久化本轮对话（每轮后）；存储端截断到最近 50 轮，防止单行 JSON 无限膨胀
    now_iso = datetime.now().isoformat(timespec="seconds")
    chat_history.append({"role": "user", "content": message, "ts": now_iso})
    chat_history.append(
        {"role": "assistant", "content": result.final_reply, "ts": now_iso}
    )
    session.messages = chat_history[-_MAX_PERSISTED_MESSAGES:]
    session.mode = result.mode  # 回写 Step 2 判定的模式，供下一轮作为先验
    # MVP 估算：每轮对话约 1 分钟，用于合规 2h 使用提醒（方案 4.8）
    session.usage_minutes = (session.usage_minutes or 0) + 1
    session.updated_at = datetime.now()

    # per-user 情绪趋势（方案 3.4）：主动预警与推荐都按当前孩子独立统计
    with SessionLocal() as s:
        emotion_trend = episodic_service.get_emotion_trend(s, user.id, days=7)

    # 家长告警频率（方案 4.2，v2.2 三档化）：
    # - 守护模式（5-7 / 8-10）：每轮对话后生成家长摘要（家长可见性更高）
    # - 过渡模式（11-13）：周度摘要（7 天内已有通知则不重复）+ 高风险即时告警
    # - 信任模式（14）：仅高风险（risk>=2 / parent_alert）时告警，对话更私密
    group = age_tiers.visibility_group(user.age_tier)
    high_risk = result.risk_level >= _ALERT_RISK_THRESHOLD or result.parent_alert
    if group == age_tiers.VISIBILITY_GUARDIAN:
        db.add(build_guardian_summary_alert(user, result, emotion_trend))
    elif high_risk:
        alerts = proactive_engine.run_all_checks(
            planet=planet,
            conversation_topics=[],
            latest_pipeline=result,
            usage_minutes=session.usage_minutes,
            emotion_trend=emotion_trend,
        )
        for a in alerts:
            db.add(
                ParentAlert(
                    user_id=user.id,
                    timestamp=datetime.fromisoformat(a.triggered_at),
                    topic=result.topic,
                    risk_level=result.risk_level,
                    summary=a.summary,
                    suggestion=a.suggestion,
                )
            )
    elif group == age_tiers.VISIBILITY_TRANSITION and not _has_recent_notification(db, user.id):
        # 过渡模式周度摘要：近 7 天无任何通知时补一条常规摘要
        db.add(build_guardian_summary_alert(user, result, emotion_trend))
    _with_write_retry(db.commit)

    # 推荐卡片 + 每日挑战（pipeline 之外的增强内容）
    rec = rec_engine.recommend_after_reply(
        planet,
        age_tier=age_tiers.normalize_age_tier(user.age_tier),
        mode=result.mode,
        latest_topic=result.topic,
        emotion_trend=emotion_trend,
    )
    recommendations = [asdict(r) for r in rec.items] if rec else []
    challenge = daily_challenges.get_today_challenge()

    return {
        "result": result,
        "recommendations": recommendations,
        "challenge": challenge,
    }
