"""内容推荐引擎 (Recommendation Engine) — 基于小星球记忆的个性化推荐

纯 Python 算法，不调 LLM，<5ms 延迟。

三种推荐策略：
1. 兴趣推荐：从近期星球条目中提取高频标签 → 推荐同标签话题
2. 复习推荐：基于艾宾浩斯遗忘曲线，对 7 天前创建的知识条目进行复习提醒
3. 情绪关怀推荐：若近期"心情云"条目增多且情绪偏负面，推荐情绪调节内容
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .age_tiers import AGE_TIERS, DEFAULT_AGE_TIER, normalize_age_tier


# ---------------------------------------------------------------------------
# 推荐内容库（基于标签的适龄话题推荐）
# ---------------------------------------------------------------------------
# 标签 → 推荐话题映射
_TAG_RECOMMENDATIONS: dict[str, list[dict]] = {
    "天文": [
        {"title": "为什么星星会眨眼？", "type": "encyclopedia", "age": "8-10",
         "hint": "和光线穿过空气有关哦"},
        {"title": "月亮为什么有时候是弯的？", "type": "encyclopedia", "age": "8-10",
         "hint": "太阳、地球和月亮玩的一个影子游戏"},
        {"title": "黑洞是什么？", "type": "encyclopedia", "age": "11-13",
         "hint": "宇宙中最神秘的'大胃王'"},
    ],
    "动物": [
        {"title": "恐龙为什么会灭绝？", "type": "encyclopedia", "age": "8-10",
         "hint": "一颗巨大的陨石改变了地球"},
        {"title": "小蚂蚁的超级力量", "type": "story", "age": "8-10",
         "hint": "一只小蚂蚁发现自己的力量可以帮到朋友"},
        {"title": "为什么候鸟要迁徙？", "type": "encyclopedia", "age": "11-13",
         "hint": "一场跨越大陆的旅行"},
    ],
    "自然": [
        {"title": "彩虹是怎么形成的？", "type": "encyclopedia", "age": "8-10",
         "hint": "阳光和水滴一起画了一幅画"},
        {"title": "为什么树叶秋天会变色？", "type": "encyclopedia", "age": "8-10",
         "hint": "树叶里藏着不同的颜色"},
        {"title": "台风是怎么形成的？", "type": "encyclopedia", "age": "11-13",
         "hint": "海洋和大气的一次'对话'"},
    ],
    "数学": [
        {"title": "为什么 1+1=2？", "type": "encyclopedia", "age": "8-10",
         "hint": "从数苹果开始的故事"},
        {"title": "神奇的斐波那契数列", "type": "encyclopedia", "age": "11-13",
         "hint": "兔子、向日葵和一个神秘的数列"},
    ],
    "物理": [
        {"title": "为什么天空是蓝色的？", "type": "encyclopedia", "age": "8-10",
         "hint": "阳光和空气玩了一个游戏"},
        {"title": "苹果为什么会掉下来？", "type": "encyclopedia", "age": "8-10",
         "hint": "牛顿和万有引力的故事"},
    ],
    "情绪": [
        {"title": "小兔子学会了说不", "type": "story", "age": "8-10",
         "hint": "一个关于勇敢表达的故事"},
        {"title": "当生气来敲门", "type": "story", "age": "8-10",
         "hint": "学习如何和'生气'这个小怪兽相处"},
        {"title": "我不是一个人在战斗", "type": "story", "age": "11-13",
         "hint": "一个关于寻求帮助的故事"},
    ],
    "科学": [
        {"title": "为什么冰会浮在水上？", "type": "encyclopedia", "age": "8-10",
         "hint": "水的秘密：固态比液态轻"},
        {"title": "人的身体里有多少水？", "type": "encyclopedia", "age": "8-10",
         "hint": "你其实是一个'水人'"},
    ],
    "故事": [
        {"title": "小恐龙的第一次飞行", "type": "story", "age": "8-10",
         "hint": "一只不会飞的小恐龙找到了自己的方式"},
        {"title": "月亮上的小兔子", "type": "story", "age": "8-10",
         "hint": "一个关于孤独和友谊的故事"},
    ],
    "安全": [
        {"title": "小红的网络安全冒险", "type": "story", "age": "8-10",
         "hint": "一个关于保护个人信息的故事"},
        {"title": "勇敢说出来", "type": "story", "age": "8-10",
         "hint": "当遇到不舒服的事，该怎么办？"},
    ],
}

# 情绪关怀推荐内容（当检测到近期情绪偏负面时使用）
_EMOTION_CARE_RECOMMENDATIONS: list[dict] = [
    {"title": "小刺猬的拥抱", "type": "story", "age": "8-10",
     "hint": "一个关于接纳自己情绪的故事"},
    {"title": "深呼吸，像大海一样", "type": "story", "age": "8-10",
     "hint": "一个帮助放松的小练习"},
    {"title": "今天发生的三件好事", "type": "chat", "age": "8-10",
     "hint": "我们一起回忆一下今天让你开心的事"},
    {"title": "彩色心情日记", "type": "chat", "age": "11-13",
     "hint": "用颜色记录每天的心情变化"},
]

# 通用兜底推荐（没有标签匹配时使用）
_FALLBACK_RECOMMENDATIONS: list[dict] = [
    {"title": "为什么天空是蓝色的？", "type": "encyclopedia", "age": "8-10",
     "hint": "一个关于光和颜色的故事"},
    {"title": "小恐龙交朋友", "type": "story", "age": "8-10",
     "hint": "一只害羞的小恐龙学会了交朋友"},
    {"title": "海底两万里大冒险", "type": "story", "age": "8-10",
     "hint": "探索深海里的神秘世界"},
    {"title": "植物的秘密生活", "type": "encyclopedia", "age": "11-13",
     "hint": "植物比你想的更聪明"},
]


@dataclass
class Recommendation:
    """单条推荐"""
    title: str
    type: str           # "encyclopedia" | "story" | "chat"
    age_tier: str       # "5-7" | "8-10" | "11-13" | "14"
    hint: str           # 推荐语
    reason: str         # 推荐理由（如"基于你最近对天文的兴趣"）


@dataclass
class RecommendationResult:
    """推荐结果"""
    items: list[Recommendation]
    source: str         # "interest" | "review" | "emotion_care" | "fallback"
    source_detail: str  # 人类可读的推荐来源说明


# ---------------------------------------------------------------------------
# 推荐算法
# ---------------------------------------------------------------------------
def recommend(
    planet: dict,
    age_tier: str = DEFAULT_AGE_TIER,
    mode: str = "chat",
    emotion_trend: Optional[dict] = None,
    max_results: int = 2,
) -> Optional[RecommendationResult]:
    """基于小星球记忆生成个性化推荐

    Args:
        planet: 小星球数据 dict
        age_tier: "5-7" | "8-10" | "11-13" | "14"（旧档自动映射）
        mode: 当前对话模式
        emotion_trend: 近期情绪趋势（来自 episodic_memory.get_emotion_trend）
        max_results: 最多返回几条推荐

    Returns:
        RecommendationResult，若无足够数据则返回 None
    """
    if not planet:
        return None

    age_tier = normalize_age_tier(age_tier)

    # 1. 情绪关怀优先：如果近期情绪偏负面 + 心情云条目增多
    if emotion_trend:
        negative_ratio = _calc_negative_ratio(emotion_trend)
        cloud_count = len(planet.get("clouds", []) or [])
        if negative_ratio > 0.3 and cloud_count >= 2:
            items = _filter_by_age(_EMOTION_CARE_RECOMMENDATIONS, age_tier, max_results)
            if items:
                return RecommendationResult(
                    items=items,
                    source="emotion_care",
                    source_detail="最近心情有点低落，来听一个温暖的故事吧",
                )

    # 2. 兴趣推荐：从近期星球条目提取高频标签
    tag_counts = _extract_tag_frequencies(planet)
    if tag_counts:
        top_tags = [tag for tag, _ in tag_counts.most_common(3)]
        interest_items: list[Recommendation] = []
        for tag in top_tags:
            candidates = _TAG_RECOMMENDATIONS.get(tag, [])
            age_filtered = _closest_age_candidates(candidates, age_tier)
            if age_filtered:
                picked = random.choice(age_filtered)
                interest_items.append(Recommendation(
                    title=picked["title"],
                    type=picked["type"],
                    age_tier=picked["age"],
                    hint=picked["hint"],
                    reason=f"基于你最近对「{tag}」的兴趣",
                ))
        if interest_items:
            return RecommendationResult(
                items=interest_items[:max_results],
                source="interest",
                source_detail=f"你最近对{'、'.join(top_tags[:2])}很感兴趣呢",
            )

    # 3. 复习推荐：基于艾宾浩斯遗忘曲线，提醒 7 天前的知识条目
    review_items = _find_review_candidates(planet, age_tier)
    if review_items:
        return RecommendationResult(
            items=review_items[:max_results],
            source="review",
            source_detail="还记得之前学过的知识吗？来复习一下吧",
        )

    # 4. 兜底推荐（通用适龄内容）
    fallback = _filter_by_age(_FALLBACK_RECOMMENDATIONS, age_tier, max_results)
    if fallback:
        return RecommendationResult(
            items=fallback,
            source="fallback",
            source_detail="还想了解更多有趣的知识吗？",
        )

    return None


def recommend_after_reply(
    planet: dict,
    age_tier: str = DEFAULT_AGE_TIER,
    mode: str = "chat",
    latest_topic: str = "",
    emotion_trend: Optional[dict] = None,
) -> Optional[RecommendationResult]:
    """在 AI 回复后生成推荐（供聊天页调用）

    相比 recommend()，增加了当前话题感知：
    - 如果刚聊完某个话题，优先推荐同类内容
    """
    result = recommend(planet, age_tier, mode, emotion_trend, max_results=2)
    if result and latest_topic:
        # 如果当前话题有对应标签，尝试在推荐中体现
        for tag, recs in _TAG_RECOMMENDATIONS.items():
            if tag in latest_topic or latest_topic in tag:
                # 当前话题相关推荐优先
                related = _filter_by_age(recs, age_tier, 1)
                if related:
                    related_rec = Recommendation(
                        title=related[0]["title"],
                        type=related[0]["type"],
                        age_tier=related[0]["age"],
                        hint=related[0]["hint"],
                        reason=f"顺着刚才聊的「{tag}」，继续探索吧",
                    )
                    result.items.insert(0, related_rec)
                    break
    return result


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------
def _extract_tag_frequencies(planet: dict) -> Counter:
    """从星球条目中提取标签频率（加权：近期条目权重更高）"""
    tag_counts: Counter = Counter()
    now = datetime.now()
    all_entries: list[dict] = []
    for key in ["stars", "clouds", "sprouts", "stories"]:
        for entry in (planet.get(key, []) or []):
            if isinstance(entry, dict):
                all_entries.append(entry)

    for entry in all_entries:
        tags = entry.get("tags", []) or []
        # 时间加权：7 天内权重 3，30 天内权重 2，其他权重 1
        date_str = entry.get("date", "")
        weight = 1
        if date_str:
            try:
                # 尝试解析中文日期格式 "7月15日"
                import re
                m = re.match(r"(\d+)月(\d+)日", date_str)
                if m:
                    month, day = int(m.group(1)), int(m.group(2))
                    entry_date = datetime(now.year, month, day)
                    if entry_date > now:
                        entry_date = entry_date.replace(year=now.year - 1)
                    days_ago = (now - entry_date).days
                    if days_ago < 7:
                        weight = 3
                    elif days_ago < 30:
                        weight = 2
            except (ValueError, OSError):
                pass
        for tag in tags:
            tag_counts[tag] += weight

    return tag_counts


def _calc_negative_ratio(emotion_trend: dict) -> float:
    """计算负面情绪占比"""
    total = sum(emotion_trend.values())
    if total == 0:
        return 0.0
    negative = emotion_trend.get("slightly_negative", 0) + emotion_trend.get("negative", 0)
    return negative / total


def _find_review_candidates(planet: dict, age_tier: str) -> list[Recommendation]:
    """找 7 天前创建的知识类条目，生成复习推荐"""
    now = datetime.now()
    candidates: list[Recommendation] = []
    for entry in (planet.get("stars", []) or []):
        if not isinstance(entry, dict):
            continue
        date_str = entry.get("date", "")
        if not date_str:
            continue
        try:
            import re
            m = re.match(r"(\d+)月(\d+)日", date_str)
            if m:
                month, day = int(m.group(1)), int(m.group(2))
                entry_date = datetime(now.year, month, day)
                if entry_date > now:
                    entry_date = entry_date.replace(year=now.year - 1)
                days_ago = (now - entry_date).days
                # 7-30 天前的知识条目适合复习
                if 7 <= days_ago <= 30:
                    title = entry.get("title", "未命名")
                    candidates.append(Recommendation(
                        title=f"复习：{title}",
                        type="encyclopedia",
                        age_tier=age_tier,
                        hint=f"你还记得{days_ago}天前学过的这个知识吗？",
                        reason=f"好记性不如再回顾一次",
                    ))
        except (ValueError, OSError):
            continue
    return candidates


def _age_distance(content_age: str, user_tier: str) -> int:
    """内容标注档位与用户档位的距离（四档升序下的下标差，无法识别视为最远）"""
    c = normalize_age_tier(content_age)
    u = normalize_age_tier(user_tier)
    try:
        return abs(AGE_TIERS.index(c) - AGE_TIERS.index(u))
    except ValueError:
        return 99


def _closest_age_candidates(recs: list[dict], age_tier: str) -> list[dict]:
    """取与用户档位距离最近的一组候选（距离 ≤1 视为适龄，优先精确命中）"""
    if not recs:
        return []
    exact = [r for r in recs if _age_distance(r.get("age", ""), age_tier) == 0]
    if exact:
        return exact
    near = [r for r in recs if _age_distance(r.get("age", ""), age_tier) <= 1]
    return near or list(recs)  # 兜底：不限年龄


def _filter_by_age(recs: list[dict], age_tier: str, limit: int) -> list[Recommendation]:
    """按年龄过滤推荐内容（精确命中优先，相邻档位视为适龄兜底）"""
    result: list[Recommendation] = []
    for r in _closest_age_candidates(recs, age_tier):
        result.append(Recommendation(
            title=r["title"],
            type=r["type"],
            age_tier=r.get("age", age_tier),
            hint=r["hint"],
            reason="",
        ))
        if len(result) >= limit:
            break
    return result
