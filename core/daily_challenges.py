"""每日小挑战模块（纯 Python，无 LLM 调用）

每天轮换一条线下行动提示，鼓励孩子将在线互动延伸到真实世界。
不追踪、不积分、不打分——纯展示 + 温和鼓励。

设计理念参考 TRAE 创造力大赛「创造力实验室」的每周创意挑战机制，
以及「探索芽」的真实世界经历记录定位。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# 挑战池（约 20 条，按类型分组）
# ---------------------------------------------------------------------------
_CHALLENGES = [
    # 社交类
    {"text": "今天试着跟一个你信任的人说一件困扰你的事", "type": "social"},
    {"text": "主动跟一个平时不太说话的同学打个招呼", "type": "social"},
    {"text": "告诉爸爸妈妈一件今天发生在学校的事", "type": "social"},
    {"text": "跟朋友分享一件你觉得有趣的事", "type": "social"},
    {"text": "如果你今天帮了别人一个忙，记得来告诉安心童伴", "type": "social"},

    # 探索 / 发现类
    {"text": "去发现一件你觉得有趣的东西，然后来告诉安心童伴", "type": "discovery"},
    {"text": "观察窗外的一棵树或一朵花，看看它今天跟昨天有什么不同", "type": "discovery"},
    {"text": "找一个你以前没注意过的角落，看看那里有什么", "type": "discovery"},
    {"text": "问爸爸妈妈一个你一直想知道但没问过的问题", "type": "discovery"},
    {"text": "试着用一个新词来描述你今天的心情", "type": "discovery"},

    # 情绪类
    {"text": "把你今天最开心的一件事记下来，种一朵心情云", "type": "emotion"},
    {"text": "如果今天有点不开心，试着跟一朵云（或枕头）说一说", "type": "emotion"},
    {"text": "画一画你今天的感受——用颜色和形状来表达", "type": "emotion"},
    {"text": "闭上眼睛做三次深呼吸，然后告诉我你感觉到了什么", "type": "emotion"},

    # 家庭类
    {"text": "给爸爸妈妈一个拥抱", "type": "family"},
    {"text": "帮家里做一件小事：收拾桌子、浇花、或者摆碗筷", "type": "family"},
    {"text": "跟爸爸妈妈一起读一个故事", "type": "family"},

    # 创造 / 身体类
    {"text": "用纸和笔画一个你想像中的星球", "type": "creative"},
    {"text": "跳绳或跑一圈，然后回来告诉我你做到了", "type": "creative"},
    {"text": "编一个只有三句话的小故事，说给安心童伴听", "type": "creative"},
]


def get_today_challenge() -> dict:
    """基于当天日期 hash 选取一条挑战，确保同一天同一用户看到同一条

    Returns:
        {"text": str, "type": str}
    """
    today = datetime.now().strftime("%Y%m%d")
    index = hash(today) % len(_CHALLENGES)
    return _CHALLENGES[abs(index)]


def get_challenge_by_date(date_str: str) -> Optional[dict]:
    """按指定日期获取挑战（用于测试或回顾）

    Args:
        date_str: "YYYYMMDD" 格式日期字符串

    Returns:
        {"text": str, "type": str} 或 None
    """
    try:
        datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        return None
    index = hash(date_str) % len(_CHALLENGES)
    return _CHALLENGES[abs(index)]


def get_challenge_count() -> int:
    """返回挑战池总数"""
    return len(_CHALLENGES)
