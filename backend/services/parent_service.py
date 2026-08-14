"""家长端服务：孩子列表、仪表盘聚合、告警、偏好读写、星球概览"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from core import memory_manager as mm
from core import age_tiers

from ..models.parent import ParentAlert, ParentPreference
from ..models.session import ChatSession
from ..models.user import User
from . import planet_service


def get_children(db: Session, parent_id: int) -> list[User]:
    """当前家长关联的全部孩子账号"""
    return (
        db.query(User)
        .filter(User.parent_id == parent_id, User.role == "child")
        .all()
    )


def build_dashboard(db: Session, parent_id: int) -> dict:
    """家长仪表盘：7 日风险趋势 + 使用时长 + 话题分布"""
    children = get_children(db, parent_id)
    child_ids = [c.id for c in children]

    since = datetime.now() - timedelta(days=7)
    alerts: list[ParentAlert] = []
    if child_ids:
        alerts = (
            db.query(ParentAlert)
            .filter(ParentAlert.user_id.in_(child_ids), ParentAlert.timestamp >= since)
            .all()
        )

    # 7 日风险趋势：按天聚合（最高风险等级 + 告警数），无数据补 0
    trend = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).date()
        day_alerts = [a for a in alerts if a.timestamp.date() == day]
        trend.append(
            {
                "date": day.isoformat(),
                "max_risk_level": max((a.risk_level for a in day_alerts), default=0),
                "alert_count": len(day_alerts),
            }
        )

    usage = 0
    if child_ids:
        sessions = (
            db.query(ChatSession).filter(ChatSession.user_id.in_(child_ids)).all()
        )
        usage = sum(s.usage_minutes or 0 for s in sessions)

    topic_dist = Counter(a.topic for a in alerts if a.topic)

    return {
        "children": [
            {"id": c.id, "username": c.username, "age_tier": c.age_tier}
            for c in children
        ],
        "risk_trend_7d": trend,
        "usage_minutes_total": usage,
        "topic_distribution": dict(topic_dist),
        "alerts_7d": len(alerts),
        "unacknowledged_alerts": sum(1 for a in alerts if not a.acknowledged),
    }


def alert_to_api(a: ParentAlert) -> dict:
    return {
        "id": a.id,
        "child_user_id": a.user_id,
        "timestamp": a.timestamp.isoformat(timespec="seconds"),
        "topic": a.topic,
        "risk_level": a.risk_level,
        "summary": a.summary,
        "suggestion": a.suggestion,
        "acknowledged": a.acknowledged,
    }


def list_alerts(db: Session, parent_id: int, limit: int = 100) -> list[dict]:
    """关联孩子的全部告警（按时间倒序）"""
    child_ids = [c.id for c in get_children(db, parent_id)]
    if not child_ids:
        return []
    rows = (
        db.query(ParentAlert)
        .filter(ParentAlert.user_id.in_(child_ids))
        .order_by(ParentAlert.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [alert_to_api(a) for a in rows]


def get_preferences(db: Session, child_id: int) -> Optional[ParentPreference]:
    return (
        db.query(ParentPreference)
        .filter(ParentPreference.user_id == child_id)
        .first()
    )


def pref_to_api(pref: ParentPreference) -> dict:
    return {
        "child_user_id": pref.user_id,
        "allowed_topics": list(pref.allowed_topics or []),
        "limited_topics": list(pref.limited_topics or []),
        "forbidden_topics": list(pref.forbidden_topics or []),
    }


def upsert_preferences(
    db: Session,
    child_id: int,
    allowed_topics: list,
    limited_topics: list,
    forbidden_topics: list,
) -> ParentPreference:
    """更新话题偏好（真正写库，孩子的下一轮对话即生效，见方案 4.3）"""
    pref = get_preferences(db, child_id)
    if pref is None:
        pref = ParentPreference(user_id=child_id)
        db.add(pref)
    pref.allowed_topics = list(allowed_topics)
    pref.limited_topics = list(limited_topics)
    pref.forbidden_topics = list(forbidden_topics)
    db.commit()
    db.refresh(pref)
    return pref


def planet_overview(db: Session, child: User) -> dict:
    """星球概览（仅计数）：守护模式（5-10 岁）家长可见；

    过渡模式（11-13）星球内容默认私密、由孩子选择分享；
    信任模式（14）完全私密，家长不可见（方案 4.2 + v2.2 三档化）。
    """
    group = age_tiers.visibility_group(child.age_tier)
    if group != age_tiers.VISIBILITY_GUARDIAN:
        reason = (
            "过渡模式（11-13 岁）：星球内容默认对孩子私密，由孩子选择分享给家长"
            if group == age_tiers.VISIBILITY_TRANSITION
            else "信任模式（14 岁及以上）：星球内容对孩子完全私密，家长不可见"
        )
        return {"visible": False, "reason": reason}
    planet = planet_service.build_planet_dict(db, child.id)
    return {"visible": True, "counts": mm.count_entries(planet)}
