"""年龄档位定义（v2.2 分龄工程 P0）

四档年龄分层：
- "5-7"   Little Explorers：温暖伙伴，超简短回复，复杂问题转家长
- "8-10"  Curious Kids：热心大哥哥/姐姐（原 8-11 层微调）
- "11-13" Young Learners：酷 mentor，身份探索支持
- "14"    Teenagers：可信赖老友，保留边界，可深度话题

旧档位兼容映射（v2.1 存量数据）："8-11" → "8-10"，"12-14" → "11-13"
（保守映射，不自动升到 14 档，见 docs/v2.2-拓展方向.md 3.3）。

家长可见性三档（摘要频率差异化，方案 4.2 的 v2.2 扩展）：
- 守护模式（5-7 / 8-10）：每轮对话后生成家长摘要
- 过渡模式（11-13）：周度摘要（7 天内已有通知则不重复）+ 高风险即时告警
- 信任模式（14）：仅高风险（risk>=2 / parent_alert）时告警
"""
from __future__ import annotations

from typing import Optional

# 四档年龄分层（顺序即年龄升序，推荐引擎用它计算档位距离）
AGE_TIERS = ("5-7", "8-10", "11-13", "14")

# 旧档位 → 新档位映射（v2.1 存量数据兼容）
LEGACY_AGE_TIER_MAP = {
    "8-11": "8-10",
    "12-14": "11-13",
}

DEFAULT_AGE_TIER = "8-10"

# 家长可见性分组
VISIBILITY_GUARDIAN = "guardian"        # 守护模式：每轮摘要
VISIBILITY_TRANSITION = "transition"    # 过渡模式：周度摘要
VISIBILITY_TRUST = "trust"              # 信任模式：仅高风险告警

_VISIBILITY_BY_TIER = {
    "5-7": VISIBILITY_GUARDIAN,
    "8-10": VISIBILITY_GUARDIAN,
    "11-13": VISIBILITY_TRANSITION,
    "14": VISIBILITY_TRUST,
}

# 前端展示用中文标签
AGE_TIER_LABELS = {
    "5-7": "5-7 岁",
    "8-10": "8-10 岁",
    "11-13": "11-13 岁",
    "14": "14 岁及以上",
}

VISIBILITY_LABELS = {
    VISIBILITY_GUARDIAN: "守护模式",
    VISIBILITY_TRANSITION: "过渡模式",
    VISIBILITY_TRUST: "信任模式",
}


def normalize_age_tier(age_tier: Optional[str]) -> str:
    """把任意历史/外部输入的年龄档位归一到新四档

    旧档位按 LEGACY_AGE_TIER_MAP 映射；无法识别时回退 DEFAULT_AGE_TIER。
    """
    if not age_tier:
        return DEFAULT_AGE_TIER
    if age_tier in AGE_TIERS:
        return age_tier
    return LEGACY_AGE_TIER_MAP.get(age_tier, DEFAULT_AGE_TIER)


def visibility_group(age_tier: Optional[str]) -> str:
    """年龄档位 → 家长可见性分组（guardian / transition / trust）"""
    return _VISIBILITY_BY_TIER[normalize_age_tier(age_tier)]


def is_younger_tier(age_tier: Optional[str]) -> bool:
    """是否为低龄档（5-7 / 8-10）：影响称呼、解释方式等"""
    return normalize_age_tier(age_tier) in ("5-7", "8-10")
