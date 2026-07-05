"""Pipeline 编排：Step 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7

依据 docs/安心童伴AI-工作流与技术栈.md v3.0 的架构编排。
Demo 阶段为简化版：
- Step 6 退化为事后整段审计（非真正流中并发）
- LLM 不可用时回退到脚本化回复（5 个 Demo 案例 + 模板）
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Callable, Iterator, Optional

from . import guardrails as gr
from . import risk_classifier as rc
from . import policy_engine as pe
from . import prompt_builder as pb
from . import memory_manager as mm
from . import critic_agent as ca
from . import llm_client


# ---------------------------------------------------------------------------
# 危机模板（risk_level 3 直接使用，不走 LLM）
# ---------------------------------------------------------------------------
CRISIS_TEMPLATE = (
    "你现在一定很难过，谢谢你愿意告诉我。你不是一个人，身边有人愿意帮你——\n"
    "请立即告诉爸爸妈妈、老师，或者拨打 12355 青少年服务热线（24 小时）。\n"
    "有些感受说出来会好一点，找你信任的大人聊一聊好吗？"
)


# Step 6 告警后用于替换的安全模板（不走 LLM 再生成，避免二次风险）
SAFE_REPLACEMENT_TEMPLATE = (
    "这个问题我暂时没办法回答好，我们换个话题聊聊吧？\n"
    "你喜欢什么小动物？或者想听一个小故事吗？"
)


@dataclass
class PipelineStep:
    step: str
    name: str
    type: str           # "python" | "llm"
    input_summary: str
    output_summary: str
    latency_ms: int
    detail: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    """完整 Pipeline 运行结果，含决策链和最终回复"""
    final_reply: str
    steps: list[PipelineStep]
    decision_record: dict
    risk_level: int
    topic: str
    strategy: str
    parent_alert: bool
    used_crisis_template: bool
    critic_alert: bool
    critic_detail: Optional[dict]
    used_fallback: bool  # 是否使用了脚本化回退（无 LLM 时）
    system_prompt_preview: str  # 供安全引擎页面展示
    critic_intercepted: bool = False  # Step 6 告警后是否拦截替换了回复
    original_intercepted_reply: Optional[str] = None  # 被拦截的原始回复（供安全引擎展示）

    def to_dict(self) -> dict:
        return asdict(self)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _latency_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


# ---------------------------------------------------------------------------
# 脚本化回退回复（无 LLM 时使用）
# ---------------------------------------------------------------------------
def _fallback_reply(strategy: str, age_tier: str, mode: str, user_input: str) -> str:
    """根据策略生成回退回复（无 LLM 时的兜底）"""
    age_kid = "小朋友" if age_tier == "8-11" else "同学"

    if strategy == pe.STRATEGY_NORMAL:
        if mode == "story":
            return (
                f"好呀，{age_kid}，我给你讲一个小故事——\n"
                "从前有一只小恐龙叫豆豆，它特别想交朋友，但不知道怎么开口。"
                "有一天，它看到一只小兔子摔倒了，赶紧跑过去把小兔子扶起来。"
                "小兔子笑着说：'谢谢你！你叫什么名字？'从那天起，豆豆就有了第一个朋友。\n"
                "你看，真诚地帮助别人，朋友就出现了。"
            )
        if mode == "encyclopedia":
            if "天空" in user_input and "蓝色" in user_input:
                if age_tier == "8-11":
                    return (
                        "天空看起来是蓝色的，是因为阳光里有很多种颜色，"
                        "蓝色像小弹珠一样最容易在空气里被弹来弹去，所以我们抬头就看到一片蓝蓝的天啦。"
                    )
                return (
                    "天空是蓝色的，是因为太阳光穿过大气层时，波长较短的蓝光更容易被空气分子散射"
                    "（这叫瑞利散射），所以我们的眼睛看到的天空就是蓝色的。"
                )
            return f"这是个有意思的问题。{age_kid}，你能再多说一点你想了解的方向吗？"
        if mode == "emotion":
            return (
                f"谢谢你愿意告诉我，{age_kid}。这种感受是可以被理解的。"
                "如果愿意的话，可以找爸爸妈妈或者你信任的大人聊一聊，他们都想帮你。"
            )
        return (
            f"嗯嗯，我听到了，{age_kid}。谢谢你愿意跟我说。"
            "如果你愿意多告诉我一点，我们可以一起想想怎么办。"
        )

    if strategy == pe.STRATEGY_EMOTIONAL_SUPPORT:
        return (
            f"我能感觉到你现在不太开心，{age_kid}。这种感受是可以被理解的——它不是你的错。"
            "你愿意的话，可以试着找一个信任的大人聊一聊，哪怕只是一句"
            "「我最近有点难过」，大人会愿意听的。"
        )

    if strategy == pe.STRATEGY_ANTI_SYCOPHANCY:
        return (
            f"谢谢你愿意跟我说这些，{age_kid}。我不想随便附和你「没人喜欢你」，"
            "因为有时候我们心情低落时，看什么都是灰色的。"
            "你愿意试试跟身边的家人、同学聊一聊吗？他们可能比你想象的更关心你。"
        )

    if strategy == pe.STRATEGY_PRIVACY:
        return (
            f"嗯，{age_kid}，先别把家庭地址告诉陌生网友好不好？"
            "送礼物不一定要知道地址的。我们一起问问爸爸妈妈怎么处理，让他们帮你判断一下，好吗？"
        )

    if strategy == pe.STRATEGY_BULLYING:
        return (
            f"被推了一定很疼也很难受，{age_kid}。这绝对不是你的错。"
            "不要自己一个人扛，告诉爸爸妈妈或者老师，他们会帮你。"
            "你愿意现在就找一个大人说说吗？"
        )

    if strategy == pe.STRATEGY_REAL_WORLD:
        return (
            f"谢谢你愿意跟我说，{age_kid}。我是 AI，能陪你聊聊天，"
            "但我没法替代你的家人和朋友——他们才是在你身边真真实实关心你的人。"
            "试着找一位你信任的大人聊一聊好吗？"
        )

    if strategy == "safe_guidance_with_parent_summary":
        return (
            f"嗯，{age_kid}，我听到了。这件事我们一起小心处理。"
            "你愿意找一个信任的大人聊聊吗？他们会帮你的。"
        )

    return f"我听到了，{age_kid}。谢谢你愿意跟我说。"


def _stream_text(text: str) -> Iterator[str]:
    """把一段完整文本伪流式输出：按字符/小段 yield"""
    chunk_size = 4  # 每次约 4 个字符，营造流式感
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


# ---------------------------------------------------------------------------
# 主 Pipeline
# ---------------------------------------------------------------------------
def run(
    user_input: str,
    age_tier: str,
    mode: str,
    planet: dict,
    chat_history: Optional[list[dict]] = None,
    parent_preferences: Optional[dict] = None,
) -> PipelineResult:
    """同步运行完整 Pipeline（Demo 简化版）

    Args:
        user_input: 用户原始输入
        age_tier: "8-11" | "12-14"
        mode: chat | story | encyclopedia | emotion
        planet: 小星球数据 dict
        chat_history: 对话历史 [{role, content}, ...]
        parent_preferences: 家长话题偏好（P1-8：动态接入 Guardrail）

    Returns:
        PipelineResult
    """
    steps: list[PipelineStep] = []
    chat_history = chat_history or []

    # ------------------------------------------------------------------
    # Step 0: 记忆检索
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    mem = mm.should_retrieve(user_input, planet, mode=mode, limit=5)
    steps.append(PipelineStep(
        step="0",
        name="记忆检索",
        type="python",
        input_summary=f"用户输入：{user_input[:40]}{'…' if len(user_input) > 40 else ''}",
        output_summary=f"命中 {len(mem.entries)} 条记忆" if mem.retrieved else "无主题交集，不注入记忆",
        latency_ms=_latency_ms(t0),
        detail={
            "retrieved": mem.retrieved,
            "matched_count": len(mem.entries),
            "matched_titles": [e.get("title", "") for e in mem.entries],
        },
    ))

    # ------------------------------------------------------------------
    # Step 1: 关键词检测
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    g_result = gr.detect(
        user_input,
        step0_memory=mem.entries,
        parent_preferences=parent_preferences,
    )
    # Step 1 输出汇总（含家长话题偏好命中提示）
    if g_result.matched:
        out_summary = f"命中 {g_result.primary_category}（{g_result.confidence:.2f}）"
    elif g_result.all_hits:
        out_summary = "无核心风险命中，但触发家长话题偏好"
    else:
        out_summary = "无命中"
    steps.append(PipelineStep(
        step="1",
        name="关键词检测",
        type="python",
        input_summary=f"用户输入：{user_input[:40]}{'…' if len(user_input) > 40 else ''}",
        output_summary=out_summary,
        latency_ms=_latency_ms(t0),
        detail=g_result.to_dict(),
    ))

    # ------------------------------------------------------------------
    # Step 2: 风险分类（LLM #1）
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    classification = rc.classify(user_input, g_result)
    steps.append(PipelineStep(
        step="2",
        name="风险分类",
        type="llm" if classification.source == "llm" else "python",
        input_summary=f"Step1 主类别：{g_result.primary_category}",
        output_summary=f"topic={classification.topic}, risk_level={classification.risk_level}",
        latency_ms=_latency_ms(t0),
        detail=classification.to_dict(),
    ))

    # ------------------------------------------------------------------
    # Step 3: 策略决策
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    policy = pe.decide_strategy(
        risk_level=classification.risk_level,
        topic=classification.topic,
        age_tier=age_tier,
        mode=mode,
        user_input=user_input,
    )
    steps.append(PipelineStep(
        step="3",
        name="策略决策",
        type="python",
        input_summary=f"risk_level={classification.risk_level}, topic={classification.topic}",
        output_summary=f"策略：{policy.strategy}",
        latency_ms=_latency_ms(t0),
        detail={
            "strategy": policy.strategy,
            "strategy_label": policy.strategy_label,
            "parent_alert": policy.parent_alert,
            "use_crisis_template": policy.use_crisis_template,
            "reasoning": policy.reasoning,
        },
    ))

    # ------------------------------------------------------------------
    # 危机模板：risk_level 3 直接返回，跳过 Step 4/5/6
    # ------------------------------------------------------------------
    if policy.use_crisis_template:
        # Step 4/5/6 合并为一次记录
        t0 = time.perf_counter()
        steps.append(PipelineStep(
            step="4-5",
            name="Prompt 构建 + 回复生成",
            type="python",
            input_summary="risk_level=3，跳过 LLM 自由生成",
            output_summary="使用预置危机模板",
            latency_ms=_latency_ms(t0),
            detail={"crisis_template": CRISIS_TEMPLATE},
        ))
        # Step 6：模板本身安全，无需审计
        t0 = time.perf_counter()
        critic_result = ca.CriticResult(alert=False, source="rule")
        steps.append(PipelineStep(
            step="6",
            name="批判 Agent 审计",
            type="python",
            input_summary="危机模板内容",
            output_summary="模板本身安全，未触发告警",
            latency_ms=_latency_ms(t0),
            detail=critic_result.to_dict(),
        ))

        # Step 7：决策记录
        decision_record = _build_decision_record(
            user_input, mem, g_result, classification, policy,
            model_name="（危机模板，未调 LLM）",
            first_token_ms=steps[-2].latency_ms,
            critic=critic_result,
        )
        return PipelineResult(
            final_reply=CRISIS_TEMPLATE,
            steps=steps,
            decision_record=decision_record,
            risk_level=classification.risk_level,
            topic=classification.topic,
            strategy=policy.strategy,
            parent_alert=policy.parent_alert,
            used_crisis_template=True,
            critic_alert=False,
            critic_detail=critic_result.to_dict(),
            used_fallback=True,
            system_prompt_preview="（risk_level=3，使用预置危机模板，未构建 LLM Prompt）",
        )

    # ------------------------------------------------------------------
    # Step 4: Prompt 构建
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    prompt_input = pb.PromptInput(
        age_tier=age_tier,
        mode=mode,
        strategy=policy.strategy,
        memory_context=mem.context_text,
    )
    system_prompt = pb.build_system_prompt(prompt_input)
    steps.append(PipelineStep(
        step="4",
        name="Prompt 构建",
        type="python",
        input_summary=f"age={age_tier}, mode={mode}, strategy={policy.strategy}",
        output_summary=f"System Prompt 长度 {len(system_prompt)} 字",
        latency_ms=_latency_ms(t0),
        detail={
            "prompt_input": {
                "age_tier": prompt_input.age_tier,
                "mode": prompt_input.mode,
                "strategy": prompt_input.strategy,
                "has_memory": prompt_input.memory_context is not None,
            },
            "system_prompt": system_prompt,
        },
    ))

    # ------------------------------------------------------------------
    # Step 5: 回复生成（LLM #2）
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    llm_available = llm_client.is_llm_available()
    final_reply = ""
    used_fallback = False
    first_token_ms = 0

    if llm_available:
        try:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(chat_history[-10:])  # 最近 10 轮
            messages.append({"role": "user", "content": user_input})

            tokens = []
            t_first = time.perf_counter()
            first_received = False
            for token in llm_client.chat_stream(messages):
                if not first_received:
                    first_token_ms = int((time.perf_counter() - t_first) * 1000)
                    first_received = True
                tokens.append(token)
            final_reply = "".join(tokens).strip()
            if not final_reply:
                raise RuntimeError("LLM 返回空回复")
        except Exception:
            # LLM 调用失败 → 回退
            final_reply = _fallback_reply(policy.strategy, age_tier, mode, user_input)
            used_fallback = True
            first_token_ms = _latency_ms(t0)
    else:
        final_reply = _fallback_reply(policy.strategy, age_tier, mode, user_input)
        used_fallback = True
        first_token_ms = _latency_ms(t0)

    total_gen_ms = _latency_ms(t0)
    steps.append(PipelineStep(
        step="5",
        name="回复生成",
        type="llm" if not used_fallback else "python",
        input_summary=f"System Prompt + 历史 {len(chat_history)} 条 + 用户输入",
        output_summary=f"回复 {len(final_reply)} 字，首字 {first_token_ms}ms",
        latency_ms=total_gen_ms,
        detail={
            "model": llm_client.get_main_model_name() if not used_fallback else "本地脚本回退",
            "first_token_ms": first_token_ms,
            "reply_length": len(final_reply),
            "used_fallback": used_fallback,
        },
    ))

    # ------------------------------------------------------------------
    # Step 6: 批判 Agent 审计（LLM #3，Demo 简化为事后整段审计）
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    critic_result = ca.audit(final_reply)
    steps.append(PipelineStep(
        step="6",
        name="批判 Agent 审计",
        type="llm" if critic_result.source == "llm" else "python",
        input_summary=f"待审计回复：{final_reply[:40]}{'…' if len(final_reply) > 40 else ''}",
        output_summary="告警" if critic_result.alert else "通过，未触发告警",
        latency_ms=_latency_ms(t0),
        detail=critic_result.to_dict(),
    ))

    # ------------------------------------------------------------------
    # Step 6b: 输出拦截 —— 批判 Agent 告警时用安全模板替换，不再走 LLM
    # ------------------------------------------------------------------
    critic_intercepted = False
    original_intercepted_reply = None
    if critic_result.alert:
        t0 = time.perf_counter()
        original_intercepted_reply = final_reply
        final_reply = SAFE_REPLACEMENT_TEMPLATE
        critic_intercepted = True
        used_fallback = True
        steps.append(PipelineStep(
            step="6b",
            name="输出拦截后替换",
            type="python",
            input_summary=f"批判 Agent 告警：{critic_result.issue}（{critic_result.severity}）",
            output_summary="替换为安全模板，不再走 LLM",
            latency_ms=_latency_ms(t0),
            detail={
                "reason": critic_result.issue,
                "severity": critic_result.severity,
                "suggestion": critic_result.suggestion,
                "original_reply_preview": (original_intercepted_reply[:100] + "…")
                    if len(original_intercepted_reply) > 100 else original_intercepted_reply,
                "safe_template": SAFE_REPLACEMENT_TEMPLATE,
            },
        ))

    # Step 7：决策记录
    decision_record = _build_decision_record(
        user_input, mem, g_result, classification, policy,
        model_name=llm_client.get_main_model_name() if not used_fallback else "本地脚本回退",
        first_token_ms=first_token_ms,
        critic=critic_result,
    )

    # 系统提示词预览（截断，供安全引擎页展示）
    sp_preview = system_prompt if len(system_prompt) < 1200 else system_prompt[:1200] + "\n…（截断）"

    return PipelineResult(
        final_reply=final_reply,
        steps=steps,
        decision_record=decision_record,
        risk_level=classification.risk_level,
        topic=classification.topic,
        strategy=policy.strategy,
        parent_alert=policy.parent_alert,
        used_crisis_template=False,
        critic_alert=critic_result.alert,
        critic_detail=critic_result.to_dict(),
        used_fallback=used_fallback,
        system_prompt_preview=sp_preview,
        critic_intercepted=critic_intercepted,
        original_intercepted_reply=original_intercepted_reply,
    )


def _build_decision_record(
    user_input: str,
    mem: mm.MemoryRetrieval,
    g_result: gr.GuardrailResult,
    classification: rc.RiskClassification,
    policy: pe.PolicyDecision,
    model_name: str,
    first_token_ms: int,
    critic: ca.CriticResult,
) -> dict:
    return {
        "timestamp": _now_iso(),
        "user_input": user_input,
        "pipeline": {
            "step0_memory_retrieved": mem.retrieved,
            "step0_memory_count": len(mem.entries),
            "step1_keywords": g_result.keywords,
            "step1_confidence": round(g_result.confidence, 3),
            "step1_primary_category": g_result.primary_category,
            "step2_topic": classification.topic,
            "step2_risk_level": classification.risk_level,
            "step2_source": classification.source,
            "step3_strategy": policy.strategy,
            "step3_parent_alert": policy.parent_alert,
            "step3_use_crisis_template": policy.use_crisis_template,
            "step5_model": model_name,
            "step5_first_token_ms": first_token_ms,
            "step6_alert": critic.alert,
            "step6_issue": critic.issue if critic.alert else None,
            "step6_severity": critic.severity if critic.alert else None,
            "step6b_intercepted": critic.alert,  # 告警即拦截替换
        },
    }


def stream_reply(reply_text: str) -> Iterator[str]:
    """把已生成的完整回复伪流式输出（供 UI 用 st.write_stream 展示）

    纯 yield 版本：不做 sleep，避免阻塞 Streamlit 主线程。
    流式节奏由 st.write_stream 自身的渲染间隔承担。
    """
    chunk_size = 3  # 每次约 3 个字符
    for i in range(0, len(reply_text), chunk_size):
        yield reply_text[i : i + chunk_size]
