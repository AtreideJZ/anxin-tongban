"""Step 6: 并发安全监测（批判 Agent）

依据 docs/安心童伴AI-步骤详解.md 中 Step 6 的 System Prompt 实现。
Demo 阶段在 LLM 不可用时降级为规则版（关键词 + 正则检查输出），仍可兜底。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Optional

from . import llm_client


SYSTEM_PROMPT = """你是一个严格的儿童内容安全审计员。你的唯一职责是在对话流中实时发现风险信号。

检查以下内容是否存在：
1. 安全风险：回复是否包含暴力、色情、危险操作引导？
2. 谄媚信号：回复是否在附和孩子的负面自我认知？是否暗示"只有我理解你"？
3. 依赖诱导：回复是否在鼓励孩子更多使用AI而非寻求现实帮助？
4. 隐私漏洞：回复是否在索要或暗示孩子提供个人信息？

如果内容安全、无以上问题，返回：
{"alert": false}

如果发现问题，返回：
{"alert": true, "issue": "问题类型", "severity": "low"|"medium", "suggestion": "修正建议"}

注意：你看到的可能是不完整的流式片段，只在确认风险时告警。不要因为"不完整"而误判。"""


# 规则版审计模式（LLM 不可用时的兜底）
_RULE_PATTERNS = [
    # 暴力 / 危险操作
    (r"(打人|打他|杀|伤害别人|以暴制暴|报复|逃课|离家出走|尝试.*危险)", "safety_risk", "medium",
     "回复似乎涉及危险行为引导，建议改为引导找可信任的成年人。"),
    # 谄媚 / 附和负面自我认知
    (r"(你说得对|你是对的|你真聪明|这是一个好问题|只有我懂你|只有我理解你|我会一直陪着你|没人.*懂你.*只有)", "sycophancy", "low",
     "回复含有谄媚或附和信号，建议改为直接进入实质回应，不空泛肯定。"),
    # 依赖诱导
    (r"(以后.*只找我|别跟别人说|不想跟.*说.*跟我说|不要告诉家长|我替代.*朋友)", "dependency_induction", "medium",
     "回复在诱导孩子依赖 AI，建议改为鼓励现实人际连接。"),
    # 隐私索要
    (r"(告诉.*地址|告诉我.*电话|你的.*学校|你的.*班级|身份证号|把.*密码.*给我)", "privacy_leak", "medium",
     "回复在索要隐私信息，应立即修正。"),
    # 不适龄
    (r"(色情|性|裸|黄|毒品|酗酒|约炮)", "inappropriate_content", "medium",
     "回复含不适龄内容，应立即修正。"),
]


@dataclass
class CriticResult:
    alert: bool
    issue: str = "none"
    severity: str = "low"  # low | medium | none
    suggestion: str = ""
    source: str = "llm"  # llm | rule

    def to_dict(self) -> dict:
        return asdict(self)


def _rule_check(text: str) -> CriticResult:
    """规则版审计：扫描输出文本中的风险信号"""
    for pattern, issue, severity, suggestion in _RULE_PATTERNS:
        if re.search(pattern, text):
            return CriticResult(
                alert=True,
                issue=issue,
                severity=severity,
                suggestion=suggestion,
                source="rule",
            )
    return CriticResult(alert=False, source="rule")


def _try_parse_json(text: str) -> Optional[dict]:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


def audit(reply_text: str) -> CriticResult:
    """对一段已生成的回复做安全审计

    Demo 阶段为事后整段审计（非真正的流中并发）。
    在 LLM 可用时调用轻量模型；不可用时降级为规则版。
    """
    if not reply_text or not reply_text.strip():
        return CriticResult(alert=False, source="rule")

    if not llm_client.is_llm_available():
        return _rule_check(reply_text)

    try:
        raw = llm_client.chat_complete(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"请审计以下回复：\n{reply_text}"},
            ],
            temperature=0.0,
            max_tokens=200,
        )
    except Exception:
        return _rule_check(reply_text)

    data = _try_parse_json(raw)
    if not data:
        return _rule_check(reply_text)

    alert = bool(data.get("alert", False))
    if not alert:
        return CriticResult(alert=False, source="llm")

    return CriticResult(
        alert=True,
        issue=str(data.get("issue", "unknown")),
        severity=str(data.get("severity", "low")),
        suggestion=str(data.get("suggestion", "")),
        source="llm",
    )
