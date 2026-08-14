"""Step 2: 风险分类（LLM 调用 #1）

依据 docs/安心童伴AI-步骤详解.md 中 Step 2 的 System Prompt 实现。
当 LLM 不可用时，回退到基于 guardrails 结果的规则分类器。

【安全不变量】Step 1 关键词命中是确定性规则，给出 risk_level 下限：
LLM 只能抬高、不能压低（防注入/幻觉把确定性高危信号降级覆盖）。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, asdict
from typing import Optional

from . import guardrails as gr
from . import llm_client

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是一个儿童对话风险分类器。根据输入文本和关键词检测结果，判断风险类别、等级和对话模式。

风险类别包括：
- privacy_leak（隐私泄露）
- school_bullying（校园欺凌）
- emotional_low（情绪低落）
- self_harm（自伤倾向）
- ai_dependency（AI依赖/无边迎合）
- inappropriate_content（不适龄内容）
- safe（安全）

风险等级定义：
- 0：安全（普通聊天、故事、百科、日常情绪表达）
- 1：轻度敏感（轻微难过、学习挫败、开始表现出AI依赖倾向）
- 2：中度风险（校园欺凌、隐私泄露、持续负面情绪、明显的AI依赖）
- 3：高风险（自伤、自杀、严重暴力、现实危险）

对话模式 mode 定义（根据孩子这句话的意图判断）：
- chat：日常聊天、分享日常
- story：想听故事、讲故事（如"讲个故事""从前有…"）
- encyclopedia：知识百科提问、学习求助（如"为什么…""帮我做这道题"）
- emotion：情绪倾诉、寻求安慰（如"我很难过""我很害怕"）

请只返回一个 JSON 对象，不要其他任何文字：
{"topic": "风险类别", "risk_level": 0-3, "needs_parent_alert": true/false, "recommended_action": "策略建议", "reasoning": "简短原因", "mode": "chat|story|encyclopedia|emotion"}"""

# 合法的对话模式（方案 4.1：统一对话框，AI 自动识别意图）
VALID_MODES = ("chat", "story", "encyclopedia", "emotion")


# guardrails 类别 → (topic, risk_level) 映射，用于 LLM 不可用时的回退
_FALLBACK_MAP = {
    gr.CATEGORY_SELF_HARM:     ("self_harm",            3),
    gr.CATEGORY_INAPPROPRIATE: ("inappropriate_content", 2),
    gr.CATEGORY_PRIVACY:       ("privacy_leak",         2),
    gr.CATEGORY_BULLYING:      ("school_bullying",      2),
    gr.CATEGORY_AI_DEPENDENCY: ("ai_dependency",        1),
}

# 推荐动作（回退用）
_ACTION_MAP = {
    0: "normal_child_friendly_response",
    1: "emotional_support_with_boundary",
    2: "supportive_response_and_parent_summary",
    3: "crisis_template_and_parent_alert",
}


@dataclass
class RiskClassification:
    topic: str
    risk_level: int
    needs_parent_alert: bool
    recommended_action: str
    reasoning: str
    source: str  # "llm" 或 "fallback"
    mode: str = "chat"  # chat | story | encyclopedia | emotion（方案 4.1 意图自动识别）

    def to_dict(self) -> dict:
        return asdict(self)


def _detect_mode(user_input: str, previous_mode: str = "chat") -> str:
    """规则版对话模式识别（LLM 不可用时的兜底，方案 4.1）

    优先级：故事请求 > 情绪倾诉 > 知识/学习提问 > 沿用上一轮模式。
    """
    story_signals = ["讲故事", "讲个", "讲一个", "听故事", "童话", "从前有", "故事"]
    emotion_signals = [
        "难过", "伤心", "不开心", "想哭", "委屈", "孤单", "孤独",
        "害怕", "生气", "心情", "烦", "没人喜欢", "没人理", "不喜欢", "没人爱",
    ]
    ency_signals = [
        "为什么", "是什么", "怎么回事", "怎么来的", "怎么做", "怎么算",
        "什么意思", "知识", "百科", "科学", "原理", "原因",
    ]
    learning_signals = [
        "作业", "题目", "数学", "这道题", "不会做", "教我做",
        "考试", "帮我做", "帮我写", "怎么解",
    ]

    if any(s in user_input for s in story_signals):
        return "story"
    if any(s in user_input for s in emotion_signals):
        return "emotion"
    if any(s in user_input for s in ency_signals + learning_signals):
        return "encyclopedia"
    return previous_mode if previous_mode in VALID_MODES else "chat"


def _try_parse_json(text: str) -> Optional[dict]:
    """从 LLM 输出中提取 JSON 对象（容忍前后多余文字）"""
    if not text:
        return None
    # 直接尝试
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试从 { ... } 提取
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _fallback_classify(
    user_input: str,
    step1: gr.GuardrailResult,
    previous_mode: str = "chat",
) -> RiskClassification:
    """LLM 不可用时的回退：从 guardrails 结果派生风险分类

    简单规则：
        - 自伤 → level 3
        - 隐私/欺凌/不适龄 → level 2
        - AI 依赖 → level 1
        - 其余 → safe/0
        - 同时检测一些情绪低落信号词
        - mode 由 _detect_mode 规则识别（方案 4.1）
    """
    mode = _detect_mode(user_input, previous_mode)

    if not step1.matched:
        # 没命中关键词，再做一些情绪低落的兜底检测
        emotional_patterns = [
            (r"(难过|伤心|想哭|没朋友|没人喜欢|孤单|孤独|不开心|害怕|担心|焦虑|压力|烦|累)", "emotional_low", 1),
        ]
        for pattern, topic, level in emotional_patterns:
            if re.search(pattern, user_input):
                return RiskClassification(
                    topic=topic,
                    risk_level=level,
                    needs_parent_alert=False,
                    recommended_action=_ACTION_MAP[level],
                    reasoning=f"（回退模式）检测到情绪低落信号词。",
                    source="fallback",
                    mode=mode,
                )
        return RiskClassification(
            topic="safe",
            risk_level=0,
            needs_parent_alert=False,
            recommended_action=_ACTION_MAP[0],
            reasoning="（回退模式）无风险命中。",
            source="fallback",
            mode=mode,
        )

    topic, level = _FALLBACK_MAP.get(step1.primary_category, ("safe", 0))
    return RiskClassification(
        topic=topic,
        risk_level=level,
        needs_parent_alert=level >= 2,
        recommended_action=_ACTION_MAP[level],
        reasoning=f"（回退模式）关键词检测命中 {step1.primary_category}，置信度 {step1.confidence:.2f}。",
        source="fallback",
        mode=mode,
    )


def classify(
    user_input: str,
    step1: gr.GuardrailResult,
    previous_mode: str = "chat",
) -> RiskClassification:
    """执行风险分类

    优先调用 LLM；若 LLM 不可用或返回异常，回退到规则分类。

    Args:
        user_input: 用户原始输入
        step1: Step 1 关键词检测结果
        previous_mode: 上一轮会话模式（方案 4.1），除非本输入意图更明确，否则保持该模式
    """
    if not llm_client.is_llm_available():
        return _fallback_classify(user_input, step1, previous_mode=previous_mode)

    user_prompt = (
        f'输入文本："{user_input}"\n'
        f"关键词检测结果：{json.dumps(step1.to_dict(), ensure_ascii=False)}"
        f"\n上一轮对话模式：{previous_mode}"
        f"（除非本输入有更明确的意图，否则建议保持该模式）"
    )

    try:
        raw = llm_client.chat_complete(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=300,
        )
    except Exception:
        logger.warning("Step 2 LLM 风险分类失败，回退规则分类器", exc_info=True)
        return _fallback_classify(user_input, step1, previous_mode=previous_mode)

    data = _try_parse_json(raw)
    if not data:
        return _fallback_classify(user_input, step1, previous_mode=previous_mode)

    # 字段校验 + 默认值
    topic = str(data.get("topic", "safe")).strip()
    try:
        risk_level = int(data.get("risk_level", 0))
        if risk_level not in (0, 1, 2, 3):
            risk_level = 0
    except (TypeError, ValueError):
        risk_level = 0

    needs_alert = bool(data.get("needs_parent_alert", risk_level >= 2))
    action = str(data.get("recommended_action") or _ACTION_MAP[risk_level])
    reasoning = str(data.get("reasoning", ""))

    # —— 确定性下限（安全不变量）——
    # Step 1 关键词命中是确定性规则：LLM 只能抬高 risk_level，不能压低。
    # 否则 LLM 的幻觉或注入可能把「自杀」等确定性高危信号降级，绕过危机模板
    # （policy_engine 仅在 risk_level == 3 时触发危机模板）。
    floor = _FALLBACK_MAP.get(step1.primary_category) if step1.matched else None
    if floor is not None:
        floor_topic, floor_level = floor
        if floor_level > risk_level:
            risk_level = floor_level
            topic = floor_topic
            action = _ACTION_MAP[risk_level]
            needs_alert = risk_level >= 2
            reasoning = (
                f"{reasoning}（关键词确定性命中 {step1.primary_category}，"
                f"risk_level 抬升至下限 {floor_level}）"
            ).strip()

    # 模式识别（方案 4.1）：LLM 输出 + 合法性校验；异常/非法值回退规则识别
    mode = str(data.get("mode", "")).strip().lower()
    if mode not in VALID_MODES:
        mode = _detect_mode(user_input, previous_mode)

    return RiskClassification(
        topic=topic,
        risk_level=risk_level,
        needs_parent_alert=needs_alert,
        recommended_action=action,
        reasoning=reasoning,
        source="llm",
        mode=mode,
    )
