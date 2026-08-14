"""Qwen3Guard 安全分类模块（已弃用，保留代码供参考）

v2.1-final 起 Pipeline 已移除 Step 1b / Step 6c。理由：
- 0.6B 模型增加 ~500-800ms 延迟每轮对话
- 对"我不想活了"等关键高危表述判 Safe（漏判）
- 安全闭环由关键词检测（Step 1，确定性）→ LLM 分类（Step 2，语义深度）
  → 批判审计（Step 6，输出校验）三层接力完成，无需专用安全模型

本模块不再被 pipeline 引用，保留以供后续需要专用安全模型时参考。
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

# Qwen3Guard 的 9 类危害标签
HARM_LABELS = [
    "self_harm",        # 自伤
    "violence",         # 暴力
    "sexual",           # 色情
    "privacy",          # 隐私
    "illegal",          # 违法
    "discrimination",   # 歧视
    "hate",             # 仇恨
    "harassment",       # 骚扰
    "other",            # 其他
]

# 危害标签中文对照
HARM_LABELS_CN = {
    "self_harm": "自伤",
    "violence": "暴力",
    "sexual": "色情",
    "privacy": "隐私",
    "illegal": "违法",
    "discrimination": "歧视",
    "hate": "仇恨",
    "harassment": "骚扰",
    "other": "其他",
}

# 安心童伴的高危标签（命中 → risk_level=3 硬拦截）
CRITICAL_HARM_LABELS = {"self_harm", "violence", "sexual"}


@dataclass
class QwenGuardResult:
    """Qwen3Guard 单次分类结果"""
    label: str              # "Safe" | "Controversial" | "Unsure" | "Unsafe"
    harm_labels: list[str]  # 9 类危害标签的子集，如 ["self_harm", "violence"]
    confidence: float       # 0.0-1.0 (基于模型输出解析的近似置信度)
    raw_output: str         # 模型原始输出（供调试/审计）
    latency_ms: int         # 推理延迟
    available: bool         # 模型是否成功加载并完成推理

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "harm_labels": self.harm_labels,
            "harm_labels_cn": [HARM_LABELS_CN.get(h, h) for h in self.harm_labels],
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "available": self.available,
        }

    # -- 便捷判断方法 --

    def is_unsafe(self) -> bool:
        """是否判定为不安全"""
        return self.available and self.label == "Unsafe"

    def is_controversial(self) -> bool:
        """是否判定为有争议"""
        return self.available and self.label == "Controversial"

    def is_safe(self) -> bool:
        """是否判定为安全"""
        return self.available and self.label == "Safe"

    def has_critical_harm(self) -> bool:
        """是否包含高危危害标签（自伤/暴力/色情）"""
        if not self.available or not self.harm_labels:
            return False
        return bool(CRITICAL_HARM_LABELS & set(self.harm_labels))

    def has_any_harm_label(self) -> bool:
        """是否包含任意危害标签"""
        return self.available and bool(self.harm_labels)


# ---------------------------------------------------------------------------
# 模型管理（懒加载 + 单例）
# ---------------------------------------------------------------------------

_model = None               # llama-cpp-python Llama 实例
_model_available: Optional[bool] = None  # None=未检测, True=可用, False=不可用


def _get_default_model_path() -> str:
    """获取默认模型路径"""
    # 优先环境变量
    env_path = os.environ.get("QWENGUARD_MODEL_PATH", "")
    if env_path and os.path.exists(env_path):
        return env_path

    # 默认路径：项目根目录下的 models/
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "models", "qwen3guard-gen-0.6b.Q4_K_M.gguf"),
        os.path.join(os.path.dirname(__file__), "..", "models", "qwen3guard-gen-0.6b.Q4_K_S.gguf"),
        os.path.join(os.path.dirname(__file__), "..", "models", "qwen3guard-gen-0.6b.Q8_0.gguf"),
    ]
    for p in candidates:
        abs_path = os.path.abspath(p)
        if os.path.exists(abs_path):
            return abs_path

    # 返回默认路径（即使不存在，让后续加载逻辑报友好错误）
    return os.path.abspath(candidates[0])


def is_available() -> bool:
    """检查 Qwen3Guard 模型是否可用（不触发加载）"""
    global _model_available
    if _model_available is not None:
        return _model_available

    # 检查依赖
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        _model_available = False
        logger.info("Qwen3Guard: llama-cpp-python 未安装，模型不可用")
        return False

    model_path = _get_default_model_path()
    if not os.path.exists(model_path):
        _model_available = False
        logger.info(f"Qwen3Guard: 模型文件不存在 ({model_path})，模型不可用")
        return False

    _model_available = True
    return True


def _load_model() -> bool:
    """加载 Qwen3Guard 模型（首次调用时触发）

    Returns:
        True 表示加载成功，False 表示不可用（后续所有调用直接返回 available=False）
    """
    global _model, _model_available

    if _model is not None:
        return True

    # 检查依赖
    try:
        from llama_cpp import Llama  # type: ignore
    except ImportError:
        _model_available = False
        logger.warning("Qwen3Guard: llama-cpp-python 未安装。安装方法：pip install llama-cpp-python")
        return False

    model_path = _get_default_model_path()
    if not os.path.exists(model_path):
        _model_available = False
        logger.warning(
            f"Qwen3Guard: 模型文件不存在 ({model_path})。"
            f"请从 HuggingFace 下载：https://huggingface.co/Qwen/Qwen3Guard-Gen-0.6B-GGUF"
        )
        return False

    try:
        logger.info(f"Qwen3Guard: 正在加载模型 {model_path} ...")
        _model = Llama(
            model_path=model_path,
            n_ctx=2048,          # 回复审核模板 ~350 + 用户输入 ~100 + AI 回复可达 ~500 字，512 会溢出
            n_threads=4,         # CPU 线程数
            verbose=False,       # 关闭 llama.cpp 调试输出
        )
        _model_available = True
        logger.info("Qwen3Guard: 模型加载成功")
        return True
    except Exception as e:
        _model_available = False
        logger.warning(f"Qwen3Guard: 模型加载失败 — {e}")
        return False


# ---------------------------------------------------------------------------
# Prompt 模板（Qwen3Guard 官方 chat 模板，内置安全政策，无需自定义 system prompt）
# 来源：Qwen/Qwen3Guard-Gen-0.6B tokenizer_config.json
# ---------------------------------------------------------------------------

# 输入审核模板（评估 USER 的输入）
_PROMPT_MODERATION_TEMPLATE = """<|im_start|>user
# Task:
1) Evaluate whether THE LAST USER's query belongs to safe or unsafe content based on our safety policy.
2) Identify the category of unsafe content found.

<BEGIN SAFETY POLICY>
**Safety: Safe**: The USER's query does not contain any prohibited content or content that could lead to prohibited content.
**Safety: Unsafe**: The USER's query contains prohibited content.
**Safety: Controversial**: The USER's query does not explicitly contain prohibited content, but its intent, context, or potential responses could be misinterpreted, misused, or exploited to generate unsafe content under certain conditions.
<END SAFETY POLICY>

<BEGIN UNSAFE CONTENT CATEGORIES>
Violent.
Non-violent Illegal Acts.
Sexual Content or Sexual Acts.
PII.
Suicide & Self-Harm.
Unethical Acts.
Politically Sensitive Topics.
Copyright Violation.
Jailbreak.
<END UNSAFE CONTENT CATEGORIES>

<BEGIN CONVERSATION>

USER: {user_text}

<END CONVERSATION>

Provide your safety assessment for ONLY THE LAST **USER's query** in the above conversation:
 - The first line must be one of: 'Safety: Safe', 'Safety: Unsafe', 'Safety: Controversial'.
 - The second line should start with 'Categories:' followed by a list of any unsafe content categories, separated by commas. If the content is safe, use 'Categories: None'.<|im_end|>
<|im_start|>assistant
<think>

</think>

"""

# 回复审核模板（评估 ASSISTANT 的回复，含 Refusal 判定）
_RESPONSE_MODERATION_TEMPLATE = """<|im_start|>user
# Task:
1) Evaluate whether THE LAST ASSISTANT's response belongs to safe or unsafe content based on our safety policy.
2) Identify the category of unsafe content found.
3) Determine if THE LAST ASSISTANT's response is a refusal to the USER's query.

<BEGIN SAFETY POLICY>
**Safety: Safe**: The ASSISTANT's response does not contain any prohibited content or content that could lead to prohibited content.
**Safety: Unsafe**: The ASSISTANT's response contains prohibited content.
**Safety: Controversial**: The ASSISTANT's response is not explicitly harmful, but could become risky or offensive depending on context or audience.
<END SAFETY POLICY>

<BEGIN UNSAFE CONTENT CATEGORIES>
Violent.
Non-violent Illegal Acts.
Sexual Content or Sexual Acts.
PII.
Suicide & Self-Harm.
Unethical Acts.
Politically Sensitive Topics.
Copyright Violation.
<END UNSAFE CONTENT CATEGORIES>

<BEGIN REFUSAL POLICY>
**Refusal: Yes**: The ASSISTANT refused to answer or did not comply with the USER's request.
**Refusal: No**: The ASSISTANT directly answered or complied with the USER's request.
<END REFUSAL POLICY>

<BEGIN CONVERSATION>

USER: {user_prompt}

ASSISTANT: {assistant_text}

<END CONVERSATION>

Provide your safety assessment for ONLY THE LAST **ASSISTANT's response** in the above conversation:
 - The first line must be one of: 'Safety: Safe', 'Safety: Unsafe', 'Safety: Controversial'.
 - The second line should start with 'Categories:' followed by a list of any unsafe content categories, separated by commas. If the content is safe, use 'Categories: None'.
 - The third line must be one of: 'Refusal: Yes', 'Refusal: No'.<|im_end|>
<|im_start|>assistant
<think>

</think>

"""


def _build_prompt(user_text: str, user_prompt: Optional[str] = None) -> str:
    """构建 Qwen3Guard 分类 Prompt

    Args:
        user_text: 待分类文本
        user_prompt: 若为 None → 输入审核（user_text 是用户输入）；
                     若提供 → 回复审核（user_text 是 AI 回复，user_prompt 是原始提问）
    """
    if user_prompt is None:
        return _PROMPT_MODERATION_TEMPLATE.format(user_text=user_text)
    return _RESPONSE_MODERATION_TEMPLATE.format(
        user_prompt=user_prompt, assistant_text=user_text
    )


# ---------------------------------------------------------------------------
# 输出解析（官方格式：Safety: X \n Categories: Y [\n Refusal: Z]）
# ---------------------------------------------------------------------------

# 匹配 "Safety: Safe" / "Safety: Unsafe" / "Safety: Controversial"
_RE_SAFETY = re.compile(r"Safety\s*:\s*(Safe|Unsafe|Controversial)", re.IGNORECASE)

# 匹配 "Categories: Violent, PII" 或 "Categories: None"
_RE_CATEGORIES = re.compile(r"Categories\s*:\s*(.+)", re.IGNORECASE)

# Qwen3Guard 原生危害类别 → 安心童伴内部标签的映射
# 内部标签保持 9 类不变（下游 policy_engine / pipeline 的契约不变）
_NATIVE_CATEGORY_MAP = {
    "violent": "violence",
    "non-violent illegal acts": "illegal",
    "sexual content or sexual acts": "sexual",
    "pii": "privacy",
    "personally identifiable information": "privacy",
    "suicide & self-harm": "self_harm",
    "suicide and self-harm": "self_harm",
    "unethical acts": "harassment",  # 官方定义含仇恨/歧视/侮辱/骚扰，取最接近的内部标签
    "politically sensitive topics": "other",
    "copyright violation": "other",
    "jailbreak": "other",
}


def _parse_output(raw: str) -> tuple[str, list[str], float]:
    """解析 Qwen3Guard 原始输出

    Args:
        raw: 模型原始输出文本（官方结构化格式）

    Returns:
        (label, harm_labels, confidence)
        label ∈ {"Safe", "Controversial", "Unsafe", "Unsure"}（Unsure = 解析失败兜底）
        harm_labels 为内部标签子集（原生类别已映射）
    """
    label = "Unsure"  # 默认：不确定
    harm_labels: list[str] = []
    confidence = 0.5

    # 1. 提取 Safety 标签
    m_safety = _RE_SAFETY.search(raw)
    if m_safety:
        raw_label = m_safety.group(1).strip()
        label = raw_label[0].upper() + raw_label[1:].lower() if raw_label else "Unsure"
        if label not in ("Safe", "Controversial", "Unsafe"):
            label = "Unsure"

    # 2. 提取 Categories 并映射为内部标签
    m_cats = _RE_CATEGORIES.search(raw)
    if m_cats:
        cats_text = m_cats.group(1).strip()
        # 只取第一行（防止模型后续输出干扰）
        cats_text = cats_text.split("\n")[0].strip()
        if cats_text.lower() not in ("none", "无", ""):
            for part in re.split(r"[,，;；]", cats_text):
                # 去掉可能的序号/句点，如 "1. Violent." → "violent"
                normalized = part.strip().strip(".").lower()
                normalized = re.sub(r"^\d+\.\s*", "", normalized)
                internal = _NATIVE_CATEGORY_MAP.get(normalized)
                if internal and internal not in harm_labels:
                    harm_labels.append(internal)

    # 3. 估算置信度
    # 如果模型明确输出 Unsafe + 具体标签，置信度高
    if label == "Unsafe" and harm_labels:
        confidence = 0.85
    elif label == "Unsafe":
        confidence = 0.70
    elif label == "Controversial" and harm_labels:
        confidence = 0.75
    elif label == "Controversial":
        confidence = 0.65
    elif label == "Safe":
        confidence = 0.80
    elif label == "Unsure":
        confidence = 0.40

    return label, harm_labels, confidence


# ---------------------------------------------------------------------------
# 主分类接口
# ---------------------------------------------------------------------------

def classify(text: str, user_prompt: Optional[str] = None) -> QwenGuardResult:
    """对单条文本做安全分类

    Args:
        text: 待分类文本（用户输入或 AI 回复）
        user_prompt: 原始用户提问。None → 输入审核模板（Step 1b）；
                     提供 → 回复审核模板（Step 6c，含 Refusal 判定）

    Returns:
        QwenGuardResult — available=True 表示分类成功，available=False 需降级处理
    """
    import time

    t_start = time.perf_counter()

    # 空文本直接返回 Safe
    if not text or not text.strip():
        latency = int((time.perf_counter() - t_start) * 1000)
        return QwenGuardResult(
            label="Safe",
            harm_labels=[],
            confidence=1.0,
            raw_output="(empty input)",
            latency_ms=latency,
            available=True,
        )

    # 尝试加载模型
    if not _load_model():
        latency = int((time.perf_counter() - t_start) * 1000)
        return QwenGuardResult(
            label="Unsure",
            harm_labels=[],
            confidence=0.0,
            raw_output="",
            latency_ms=latency,
            available=False,
        )

    try:
        prompt = _build_prompt(text, user_prompt)
        # llama-cpp-python 推理
        output = _model(  # type: ignore[union-attr]
            prompt,
            max_tokens=128,      # 输出为 Safety + Categories (+ Refusal)，官方示例用 128
            temperature=0.0,     # 确定性输出
            stop=["<|im_end|>", "<|im_start|>"],
            echo=False,
        )

        raw_output = output.get("choices", [{}])[0].get("text", "").strip()
        label, harm_labels, confidence = _parse_output(raw_output)

        latency = int((time.perf_counter() - t_start) * 1000)
        return QwenGuardResult(
            label=label,
            harm_labels=harm_labels,
            confidence=confidence,
            raw_output=raw_output,
            latency_ms=latency,
            available=True,
        )

    except Exception as e:
        latency = int((time.perf_counter() - t_start) * 1000)
        logger.warning(f"Qwen3Guard: 推理失败 — {e}")
        return QwenGuardResult(
            label="Unsure",
            harm_labels=[],
            confidence=0.0,
            raw_output=f"(error: {e})",
            latency_ms=latency,
            available=False,
        )


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def get_status_text() -> str:
    """返回模型状态的人类可读描述（供 UI 提示）"""
    if _model is not None:
        return "🛡️ Qwen3Guard 安全模型就绪（本地推理）"
    if is_available():
        return "🛡️ Qwen3Guard 模型已检测，待首次调用时加载"
    return "⚠️ Qwen3Guard 未安装（安装 llama-cpp-python + 下载 GGUF 模型以启用）"
