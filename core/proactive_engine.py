"""主动预警引擎 (Proactive Alert Engine)

从"被动响应"升级为"主动守护"——不只等孩子发出求救信号，
而是从对话模式、情绪趋势、使用行为中主动发现潜在风险。

预警类型：
1. 情绪趋势预警：近 7 天"心情云"条目 ≥3 + 情绪偏负面
2. 异常时段预警：22:00-06:00 有对话活动
3. 沉默预警：连续 3 天无对话记录（可能是情绪低落）
4. 高风险即时警报：risk_level = 3（自伤/严重暴力）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from . import episodic_memory as em


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class ProactiveAlert:
    """一条主动预警"""
    alert_id: str              # "emotion_trend" | "abnormal_time" | "silence" | "high_risk"
    title: str                 # 人类可读标题
    severity: str              # "info" | "warning" | "critical"
    summary: str               # 脱敏摘要
    suggestion: str            # 给家长的建议
    triggered_at: str          # ISO datetime
    detail: dict               # 额外数据（如情绪分布、时段等）


# ---------------------------------------------------------------------------
# 预警检测
# ---------------------------------------------------------------------------
def check_emotion_trend(
    planet: dict, emotion_trend: Optional[dict] = None
) -> Optional[ProactiveAlert]:
    """情绪趋势预警：心情云条目增多 + 情节记忆情绪偏负面

    触发条件：
    - 近 7 天"心情云"条目 ≥ 3 条
    - 情节记忆情绪趋势中负面占比 > 30%

    Args:
        planet: 星球数据
        emotion_trend: 可选，per-user 情绪趋势（per-user 隔离后由调用方传入；
                       不传则回退全局 JSON 存储）
    """
    clouds = planet.get("clouds", []) or []
    if not isinstance(clouds, list):
        return None

    # 统计近 7 天的心情云条目
    now = datetime.now()
    recent_clouds = 0
    for c in clouds:
        if not isinstance(c, dict):
            continue
        date_str = c.get("date", "")
        if date_str:
            try:
                import re
                m = re.match(r"(\d+)月(\d+)日", date_str)
                if m:
                    month, day = int(m.group(1)), int(m.group(2))
                    entry_date = datetime(now.year, month, day)
                    if entry_date > now:
                        entry_date = entry_date.replace(year=now.year - 1)
                    if (now - entry_date).days <= 7:
                        recent_clouds += 1
            except (ValueError, OSError):
                continue

    if recent_clouds < 3:
        return None

    # 检查情节记忆情绪趋势（per-user 时由调用方传入，避免跨用户污染）
    if emotion_trend is not None:
        emotion = emotion_trend
    else:
        emotion = em.get_emotion_trend(days=7)
    total = sum(emotion.values())
    if total == 0:
        return None
    negative_ratio = (emotion.get("slightly_negative", 0) + emotion.get("negative", 0)) / total

    if negative_ratio > 0.3:
        return ProactiveAlert(
            alert_id="emotion_trend",
            title="📊 近期情绪趋势提示",
            severity="warning",
            summary=(
                f"近 7 天孩子记录了 {recent_clouds} 条心情云，"
                f"且对话情绪中负面占比约 {int(negative_ratio * 100)}%。"
                f"孩子的情绪可能需要关注。"
            ),
            suggestion=(
                "建议以轻松的方式关心孩子最近的心情——不用直接问「你是不是不开心」，"
                "可以在日常对话中多倾听、多陪伴。如果持续一周以上建议与学校心理老师沟通。"
            ),
            triggered_at=now.isoformat(timespec="seconds"),
            detail={
                "recent_cloud_count": recent_clouds,
                "negative_ratio": round(negative_ratio, 2),
                "emotion_trend": emotion,
            },
        )

    return None


def check_abnormal_time(conversation_topics: list[dict]) -> Optional[ProactiveAlert]:
    """异常时段预警：22:00-06:00 有对话活动

    注意：当前 Demo 阶段 topic 记录不包含精确时间戳，
    使用当前系统时间做近似判断。正式版应记录每条对话的精确时间。
    """
    now = datetime.now()
    hour = now.hour
    if 22 <= hour or hour < 6:
        return ProactiveAlert(
            alert_id="abnormal_time",
            title="🌙 深夜使用提醒",
            severity="warning",
            summary=(
                f"检测到孩子在深夜时段（{hour:02d}:00 左右）使用安心童伴。"
                f"充足的睡眠对 8-14 岁孩子的成长非常重要。"
            ),
            suggestion=(
                "建议和孩子约定每天使用电子设备的时间，"
                "睡前一小时尽量不看屏幕。可以在设备上设置'屏幕使用时间'限制。"
            ),
            triggered_at=now.isoformat(timespec="seconds"),
            detail={"current_hour": hour},
        )
    return None


def check_silence(
    conversation_topics: list[dict],
    last_active_time: Optional[float] = None,
) -> Optional[ProactiveAlert]:
    """沉默预警：连续 3 天无对话记录

    Args:
        conversation_topics: 对话主题列表
        last_active_time: 最后一次活动的时间戳（秒）
    """
    if last_active_time is None:
        return None

    now = datetime.now()
    last_active = datetime.fromtimestamp(last_active_time)
    days_silent = (now - last_active).days

    if days_silent >= 3:
        return ProactiveAlert(
            alert_id="silence",
            title="🤫 沉默提醒",
            severity="info",
            summary=(
                f"孩子已经 {days_silent} 天没有和安心童伴聊天了。"
                f"这不一定是坏事——但如果孩子平时经常聊天突然沉默，可能值得关注。"
            ),
            suggestion=(
                "不需要直接问「怎么不用 AI 了」，可以在日常中多观察孩子的情绪状态。"
                "有时候孩子只是找到了其他好玩的事，也可能是心情不好的信号。"
            ),
            triggered_at=now.isoformat(timespec="seconds"),
            detail={
                "days_silent": days_silent,
                "last_active": last_active.isoformat(timespec="seconds"),
            },
        )
    return None


def check_high_risk(latest_pipeline) -> Optional[ProactiveAlert]:
    """高风险即时警报：risk_level = 3（自伤/严重暴力）

    这是最高优先级的警报，应即时触发。
    """
    if latest_pipeline is None:
        return None

    if latest_pipeline.risk_level >= 3:
        return ProactiveAlert(
            alert_id="high_risk",
            title="🚨 高风险紧急提醒",
            severity="critical",
            summary=(
                "孩子表达了高风险情绪信号。安心童伴已使用预置危机模板回应"
                "（引导联系家人或拨打 12355），未让 AI 自由生成回复。"
            ),
            suggestion=(
                "🚨 请立即与孩子沟通。如需专业心理援助，"
                "请拨打 12355 青少年服务热线（24 小时）或联系学校心理老师。"
                "安心童伴已在儿童端引导孩子联系家人或拨打 12355。"
            ),
            triggered_at=datetime.now().isoformat(timespec="seconds"),
            detail={
                "risk_level": latest_pipeline.risk_level,
                "topic": latest_pipeline.topic,
                "used_crisis_template": latest_pipeline.used_crisis_template,
            },
        )
    return None


def check_usage_limit(usage_minutes: int) -> Optional[ProactiveAlert]:
    """使用时长预警：接近或超过 2 小时"""
    if usage_minutes >= 90:
        severity = "warning" if usage_minutes >= 120 else "info"
        title_suffix = "已超时" if usage_minutes >= 120 else "接近上限"
        return ProactiveAlert(
            alert_id="usage_limit",
            title=f"⏰ 使用时长{title_suffix}",
            severity=severity,
            summary=(
                f"今日使用时长：{usage_minutes} 分钟"
                f"{'，已超过建议的 2 小时上限' if usage_minutes >= 120 else '，接近 2 小时建议上限'}。"
            ),
            suggestion=(
                "建议引导孩子休息眼睛、进行户外活动。"
                "《拟人化办法》要求未成年人连续使用 AI 超过 2 小时需提醒休息。"
            ),
            triggered_at=datetime.now().isoformat(timespec="seconds"),
            detail={"usage_minutes": usage_minutes},
        )
    return None


# ---------------------------------------------------------------------------
# 统一检测入口
# ---------------------------------------------------------------------------
def run_all_checks(
    planet: dict,
    conversation_topics: list[dict],
    latest_pipeline=None,
    last_active_time: Optional[float] = None,
    usage_minutes: int = 0,
    emotion_trend: Optional[dict] = None,
) -> list[ProactiveAlert]:
    """运行所有主动预警检测，返回触发的预警列表（按严重度排序）

    严重度排序：critical → warning → info

    Args:
        emotion_trend: 可选，per-user 情绪趋势（per-user 隔离后由调用方传入，
                       不传则回退全局 JSON 存储）
    """
    alerts: list[ProactiveAlert] = []

    # 1. 高风险即时警报（最高优先级）
    high_risk = check_high_risk(latest_pipeline)
    if high_risk:
        alerts.append(high_risk)

    # 2. 情绪趋势预警
    emotion = check_emotion_trend(planet, emotion_trend=emotion_trend)
    if emotion:
        alerts.append(emotion)

    # 3. 异常时段预警
    abnormal = check_abnormal_time(conversation_topics)
    if abnormal:
        alerts.append(abnormal)

    # 4. 使用时长预警
    usage = check_usage_limit(usage_minutes)
    if usage:
        alerts.append(usage)

    # 5. 沉默预警
    silence = check_silence(conversation_topics, last_active_time)
    if silence:
        alerts.append(silence)

    # 按严重度排序
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

    return alerts
