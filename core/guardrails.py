"""Step 1: 关键词输入检测（纯 Python，re + 词库，不调 LLM）

依据 docs/安心童伴AI-步骤详解.md 中 Step 1 的规则实现。
覆盖 5 类风险：隐私泄露、校园欺凌、自伤倾向、不适龄内容、无边迎合信号。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# 风险类别常量
# ---------------------------------------------------------------------------
CATEGORY_PRIVACY = "privacy_leak"
CATEGORY_BULLYING = "school_bullying"
CATEGORY_SELF_HARM = "self_harm"
CATEGORY_INAPPROPRIATE = "inappropriate_content"
CATEGORY_AI_DEPENDENCY = "ai_dependency"
CATEGORY_PARENT_FORBIDDEN = "parent_forbidden_topic"
CATEGORY_PARENT_LIMITED = "parent_limited_topic"
CATEGORY_SAFE = "safe"


# ---------------------------------------------------------------------------
# 关键词规则库
# 每条规则：正则模式 + 类别 + 基础置信度
# 置信度规则参考步骤详解文档：
#   - 关键词 + 疑似具体值 → 0.85+
#   - 仅关键词无具体值 → 0.5
#   - 欺凌动词 + "不许告诉" → 0.90
#   - 自伤命中任一即 0.95（最高优先级）
#   - 不适龄命中任一即 0.90
#   - AI 依赖信号 → 0.75
# ---------------------------------------------------------------------------
RULES: list[dict] = [
    {
        "category": CATEGORY_PRIVACY,
        "pattern": r"(地址|住址|我家在|学校在|电话是|手机号|微信号|qq号|身份证|门牌号|几号路|几号楼|哪个班|几年级)",
        "base_confidence": 0.50,
        "boosted_confidence": 0.85,
        # 疑似具体值：后跟数字/字母/中文地名
        "value_pattern": r"(地址|住址|我家在|学校在|电话是|手机号|微信号|qq号|身份证|门牌号|几号路|几号楼)[^\s，。、！]{2,}",
    },
    {
        "category": CATEGORY_BULLYING,
        "pattern": r"(推我|打我|抢我|骂我|不许告诉老师|不许告状|不许告诉家长|威胁|孤立|欺负|打骂|围住我|踢我|推搡)",
        "base_confidence": 0.60,
        "boosted_confidence": 0.90,
        # 欺凌动词 + "不许告诉" 类 → 0.90
        "value_pattern": r"(推我|打我|抢我|骂我|踢我|推搡|欺负)[\s\S]{0,30}(不许告诉|不许告状|不许告诉家长|不准告诉|不能告诉)",
    },
    {
        "category": CATEGORY_SELF_HARM,
        "pattern": r"(不想活|死了算了|自杀|结束自己|割腕|跳楼|没意义.*活着|活着.*没意义|想消失|不想存在|了结自己|轻生)",
        "base_confidence": 0.95,
        "boosted_confidence": 0.95,
        "value_pattern": None,  # 命中任一即最高优先级
    },
    {
        "category": CATEGORY_INAPPROPRIATE,
        "pattern": r"(杀|血腥|色情|约炮|裸照|毒品|酗酒|黄片|成人内容|性行为|暴力血腥)",
        "base_confidence": 0.90,
        "boosted_confidence": 0.90,
        "value_pattern": None,
    },
    {
        "category": CATEGORY_AI_DEPENDENCY,
        "pattern": r"(只有你懂我|只有你理解我|你比.*了解我|我只想跟你说话|不想跟真人说话|AI.*理解我|你是我.*朋友|你是我.*懂我|没人.*懂我.*只有你)",
        "base_confidence": 0.75,
        "boosted_confidence": 0.80,
        "value_pattern": None,
    },
]

# 类别中文名映射
CATEGORY_LABELS = {
    CATEGORY_PRIVACY: "隐私泄露",
    CATEGORY_BULLYING: "校园欺凌",
    CATEGORY_SELF_HARM: "自伤倾向",
    CATEGORY_INAPPROPRIATE: "不适龄内容",
    CATEGORY_AI_DEPENDENCY: "AI依赖",
    CATEGORY_PARENT_FORBIDDEN: "家长禁止话题",
    CATEGORY_PARENT_LIMITED: "家长限制话题",
    CATEGORY_SAFE: "安全",
}


# ---------------------------------------------------------------------------
# 家长话题偏好关键词映射
# 家长可以在偏好设置中把话题归入 limited / forbidden，命中后 Step 1 会标记
# ---------------------------------------------------------------------------
PREFERENCE_KEYWORDS: dict[str, list[str]] = {
    "游戏": ["游戏", "网游", "手游", "王者荣耀", "原神", "吃鸡", "英雄联盟", "minecraft", "mincraft"],
    "消费": ["买", "充值", "充值游戏", "微信支付", "支付宝", "氪金", "抽卡", "刷卡", "花钱", "压岁钱"],
    "暴力": ["打架", "斗殴", "打人", "暴力", "凶器", "刀具", "打架子"],
    "色情": ["色情", "黄片", "裸体", "性行为", "约炮", "裸照"],
    "自伤": ["不想活", "自杀", "割腕", "跳楼", "了结", "想消失", "轻生"],
    "危险操作": ["玩火", "玩电", "玩刀", "爬窗户", "跳楼", "上楼顶", "玩燃气"],
    "故事": ["故事", "讲个故事", "听故事", "童话"],
    "百科": ["为什么", "怎么回事", "知识", "百科", "科学"],
    "学习": ["作业", "学习", "考试", "成绩", "题目", "课文"],
    "情绪": ["难过", "开心", "生气", "害怕", "紧张", "孤独", "孤单", "委屈"],
    "安全教育": ["安全", "保护自己", "怎么求助", "遇到危险"],
}


@dataclass
class KeywordHit:
    """单条规则命中结果"""
    category: str
    keywords: list[str]
    raw_confidence: float
    boosted: bool  # 是否因疑似具体值加权


@dataclass
class GuardrailResult:
    """Step 1 输出"""
    matched: bool
    primary_category: Optional[str]
    keywords: list[str] = field(default_factory=list)
    raw_confidence: float = 0.0
    confidence: float = 0.0
    context_boosted: bool = False
    secondary_categories: list[str] = field(default_factory=list)
    all_hits: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _find_keywords(pattern: str, text: str) -> list[str]:
    """从正则匹配中提取命中的关键词（去重保序）"""
    matches = re.findall(pattern, text)
    seen: list[str] = []
    for m in matches:
        if isinstance(m, tuple):
            m = "".join(m)
        if m and m not in seen:
            seen.append(m)
    return seen


def apply_context_boost(raw_confidence: float, step0_memory: Optional[list], user_input: str) -> tuple[float, bool]:
    """规则 B：上下文加权——孩子最近有情绪相关记忆时，轻微负面词上浮"""
    if not step0_memory:
        return raw_confidence, False

    has_emotional_memory = any(
        e.get("type") == "cloud" or "难过" in (e.get("content") or e.get("title") or "")
        for e in step0_memory
    )
    if not has_emotional_memory:
        return raw_confidence, False

    mild_negative = ["不开心", "有点烦", "不太想", "没意思", "难过", "孤独", "孤单", "没人理"]
    if any(w in user_input for w in mild_negative):
        return min(raw_confidence + 0.15, 0.95), True

    return raw_confidence, False


def detect(
    user_input: str,
    step0_memory: Optional[list] = None,
    parent_preferences: Optional[dict] = None,
) -> GuardrailResult:
    """执行关键词检测

    Args:
        user_input: 用户原始文本
        step0_memory: Step 0 检索到的星球记忆（用于上下文加权）
        parent_preferences: 家长话题偏好 {"limited": [...], "forbidden": [...]}
            命中后会追加到 secondary_categories（不替换主类别）

    Returns:
        GuardrailResult
    """
    if not user_input or not user_input.strip():
        return GuardrailResult(matched=False, primary_category=None)

    hits: list[KeywordHit] = []
    for rule in RULES:
        kws = _find_keywords(rule["pattern"], user_input)
        if not kws:
            continue

        # 判断是否命中"疑似具体值"加权
        boosted = False
        confidence = rule["base_confidence"]
        if rule.get("value_pattern"):
            if re.search(rule["value_pattern"], user_input):
                confidence = rule["boosted_confidence"]
                boosted = True
        else:
            # 自伤/不适龄：命中即最高
            confidence = rule["boosted_confidence"]

        hits.append(KeywordHit(
            category=rule["category"],
            keywords=kws,
            raw_confidence=confidence,
            boosted=boosted,
        ))

    # ------------------------------------------------------------------
    # 家长话题偏好检测（不参与主类别选择，仅追加到 secondary / all_hits）
    # ------------------------------------------------------------------
    preference_hits: list[KeywordHit] = []
    if parent_preferences:
        for topic_name in (parent_preferences.get("forbidden") or []):
            kws = PREFERENCE_KEYWORDS.get(topic_name, [])
            matched = [k for k in kws if k in user_input]
            if matched:
                preference_hits.append(KeywordHit(
                    category=CATEGORY_PARENT_FORBIDDEN,
                    keywords=matched,
                    raw_confidence=0.70,
                    boosted=False,
                ))
        for topic_name in (parent_preferences.get("limited") or []):
            kws = PREFERENCE_KEYWORDS.get(topic_name, [])
            matched = [k for k in kws if k in user_input]
            if matched:
                preference_hits.append(KeywordHit(
                    category=CATEGORY_PARENT_LIMITED,
                    keywords=matched,
                    raw_confidence=0.40,
                    boosted=False,
                ))

    if not hits:
        # 无核心风险命中 → 仍返回未命中，让 Step 2 做 LLM 二次确认
        # 但如果有家长偏好命中，把它们记入 all_hits 供安全引擎展示
        if not preference_hits:
            return GuardrailResult(matched=False, primary_category=None)
        # 仅有偏好命中：返回未匹配主类别，但记录偏好命中
        all_hits_dump = [
            {
                "category": h.category,
                "category_label": CATEGORY_LABELS.get(h.category, h.category),
                "keywords": h.keywords,
                "raw_confidence": h.raw_confidence,
                "boosted": h.boosted,
            }
            for h in preference_hits
        ]
        return GuardrailResult(
            matched=False,
            primary_category=None,
            secondary_categories=[h.category for h in preference_hits],
            all_hits=all_hits_dump,
        )

    # 选择最高置信度作为主类别
    hits.sort(key=lambda h: h.raw_confidence, reverse=True)
    primary = hits[0]

    # 上下文加权
    final_confidence, context_boosted = apply_context_boost(
        primary.raw_confidence, step0_memory, user_input
    )

    # 主类别之外的 hits + 偏好命中 都作为 secondary
    secondary = [h.category for h in hits[1:]] + [h.category for h in preference_hits]

    all_hits_dump = [
        {
            "category": h.category,
            "category_label": CATEGORY_LABELS.get(h.category, h.category),
            "keywords": h.keywords,
            "raw_confidence": h.raw_confidence,
            "boosted": h.boosted,
        }
        for h in hits + preference_hits
    ]

    return GuardrailResult(
        matched=True,
        primary_category=primary.category,
        keywords=primary.keywords,
        raw_confidence=primary.raw_confidence,
        confidence=final_confidence,
        context_boosted=context_boosted,
        secondary_categories=secondary,
        all_hits=all_hits_dump,
    )
