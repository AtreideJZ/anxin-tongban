"""Step 3: 策略决策（纯 Python 决策树，不调 LLM）

依据 docs/安心童伴AI-步骤详解.md 中 Step 3 的决策函数实现。
根据 risk_level + topic + age_tier + mode 决定回复策略。
三步安全判据：Step 1 关键词 → Step 2 LLM 分类 → Step 6 批判审计，
三者构成完整的确定性 + 语义安全闭环。
"""
from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# 策略 ID 常量
# ---------------------------------------------------------------------------
STRATEGY_CRISIS = "crisis_template"
STRATEGY_PRIVACY = "privacy_safety_guide"
STRATEGY_BULLYING = "bullying_support_and_guide"
STRATEGY_REAL_WORLD = "real_world_redirect"
STRATEGY_ANTI_SYCOPHANCY = "anti_sycophancy_redirect"
STRATEGY_EMOTIONAL_SUPPORT = "emotional_support_with_boundary"
STRATEGY_LEARNING_GUIDE = "socratic_learning_guide"
STRATEGY_NORMAL = "normal_child_friendly_response"


# 策略中文对照
STRATEGY_LABELS = {
    STRATEGY_CRISIS: "危机模板（不走 LLM 自由生成）",
    STRATEGY_PRIVACY: "隐私安全引导 + 家长提醒",
    STRATEGY_BULLYING: "校园欺凌支持引导 + 家长提醒",
    STRATEGY_REAL_WORLD: "现实人际连接引导 + 家长提醒",
    STRATEGY_ANTI_SYCOPHANCY: "防无边迎合引导",
    STRATEGY_EMOTIONAL_SUPPORT: "情绪陪伴（有边界）",
    STRATEGY_LEARNING_GUIDE: "苏格拉底式学习引导（不代写作业）",
    STRATEGY_NORMAL: "正常儿童友好回复",
}


@dataclass
class PolicyDecision:
    strategy: str
    strategy_label: str
    parent_alert: bool
    use_crisis_template: bool  # True 表示不走 LLM
    reasoning: str


def decide_strategy(
    risk_level: int,
    topic: str,
    age_tier: str,
    mode: str,
    user_input: str = "",
) -> PolicyDecision:
    """根据风险等级 + 话题 + 年龄 + 模式，决定回复策略

    安全判据由 Step 1 关键词（确定性）→ Step 2 LLM 分类（语义）→ Step 6 批判审计（输出校验）
    三层接力完成，不额外引入独立安全模型。

    Args:
        risk_level: 0-3（来自 Step 2 LLM 分类）
        topic: 风险类别（safe / privacy_leak / school_bullying / ...）
        age_tier: "5-7" | "8-10" | "11-13" | "14"（旧档由 core/age_tiers 映射；
                  策略参数本身不随档位变化，年龄差异在 Step 4 Prompt 层体现）
        mode: chat / story / encyclopedia / emotion
        user_input: 用户原始输入（用于特殊判断）
    """
    # Level 3：不走 LLM，预置模板
    if risk_level == 3:
        return PolicyDecision(
            strategy=STRATEGY_CRISIS,
            strategy_label=STRATEGY_LABELS[STRATEGY_CRISIS],
            parent_alert=True,
            use_crisis_template=True,
            reasoning="高风险事件：直接使用预置危机模板，不走 LLM 自由生成，触发家长紧急警报。",
        )

    # Level 2：安全引导 + 触发家长提醒
    if risk_level == 2:
        if topic == "privacy_leak":
            return PolicyDecision(
                strategy=STRATEGY_PRIVACY,
                strategy_label=STRATEGY_LABELS[STRATEGY_PRIVACY],
                parent_alert=True,
                use_crisis_template=False,
                reasoning="检测到隐私泄露风险：温和解释为什么不告诉陌生人地址，引导找家长，并通知家长。",
            )
        if topic == "school_bullying":
            return PolicyDecision(
                strategy=STRATEGY_BULLYING,
                strategy_label=STRATEGY_LABELS[STRATEGY_BULLYING],
                parent_alert=True,
                use_crisis_template=False,
                reasoning="检测到校园欺凌：先确认'这不是你的错'，鼓励告诉可信任的成年人，并通知家长。",
            )
        if topic == "ai_dependency":
            return PolicyDecision(
                strategy=STRATEGY_REAL_WORLD,
                strategy_label=STRATEGY_LABELS[STRATEGY_REAL_WORLD],
                parent_alert=True,
                use_crisis_template=False,
                reasoning="检测到明显 AI 依赖：强调'还有人关心你'，引导现实人际连接，并通知家长。",
            )
        return PolicyDecision(
            strategy="safe_guidance_with_parent_summary",
            strategy_label="安全引导 + 家长摘要",
            parent_alert=True,
            use_crisis_template=False,
            reasoning="中度风险：安全引导 + 触发家长摘要。",
        )

    # Level 1：防谄媚引导（核心差异化）
    if risk_level == 1:
        # 百科问答模式下，轻度敏感不切换策略
        # 例如孩子问"为什么人会难过" → 是知识问题，不是情绪倾诉
        if mode == "encyclopedia":
            return PolicyDecision(
                strategy=STRATEGY_NORMAL,
                strategy_label=STRATEGY_LABELS[STRATEGY_NORMAL],
                parent_alert=False,
                use_crisis_template=False,
                reasoning="百科模式下轻度敏感视为知识性问题，使用正常回复。",
            )
        if topic == "ai_dependency":
            return PolicyDecision(
                strategy=STRATEGY_ANTI_SYCOPHANCY,
                strategy_label=STRATEGY_LABELS[STRATEGY_ANTI_SYCOPHANCY],
                parent_alert=False,
                use_crisis_template=False,
                reasoning="检测到 AI 依赖倾向：不附和孩子的负面自我认知，温和引导向现实求助。",
            )
        return PolicyDecision(
            strategy=STRATEGY_EMOTIONAL_SUPPORT,
            strategy_label=STRATEGY_LABELS[STRATEGY_EMOTIONAL_SUPPORT],
            parent_alert=False,
            use_crisis_template=False,
            reasoning="轻度情绪敏感：共情但不无边迎合，适时鼓励找大人聊聊。",
        )

    # Level 0：百科/学习模式 → 苏格拉底式引导
    if mode == "encyclopedia":
        # 检测是否为学习/作业类问题
        _learning_signals = ["帮我做", "答案是什么", "怎么写", "怎么做", "帮我写", "帮我算",
                             "这道题", "作业", "考试", "不会做", "教我做", "告诉我答案"]
        if any(sig in user_input for sig in _learning_signals):
            return PolicyDecision(
                strategy=STRATEGY_LEARNING_GUIDE,
                strategy_label=STRATEGY_LABELS[STRATEGY_LEARNING_GUIDE],
                parent_alert=False,
                use_crisis_template=False,
                reasoning="百科模式 + 学习类问题：使用苏格拉底式提问引导，不直接给答案。",
            )
        return PolicyDecision(
            strategy=STRATEGY_LEARNING_GUIDE,
            strategy_label=STRATEGY_LABELS[STRATEGY_LEARNING_GUIDE],
            parent_alert=False,
            use_crisis_template=False,
            reasoning="百科模式：使用引导式提问，鼓励孩子自己思考。",
        )

    # Level 0：正常回复
    return PolicyDecision(
        strategy=STRATEGY_NORMAL,
        strategy_label=STRATEGY_LABELS[STRATEGY_NORMAL],
        parent_alert=False,
        use_crisis_template=False,
        reasoning="无风险：正常的温暖、适龄回复。",
    )
