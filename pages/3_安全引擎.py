"""安心童伴 AI — 后台安全引擎页

依据 docs/安心童伴AI-初赛Demo拆解.md 第 4 节设计：
- 展示最近一次 Pipeline 运行的决策链
- 每一步的输入/输出/延迟
- Step 6 拦截记录（如有）
- 历史运行列表
"""
from __future__ import annotations

import json

import streamlit as st

from core import llm_client
from utils import state, styles

st.set_page_config(
    page_title="安全引擎",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

state.init_state()
styles.apply_theme()


st.markdown("## 🛡️ 安全引擎 · 决策链可视化")
st.caption("这是面向家长端的后台页面。每条消息从输入到回复都要经过 7 步安全 Pipeline，下方时间轴展示当前运行的链路。")


# ---------------------------------------------------------------------------
# 7 步 Pipeline 总览图（横向时间轴）
# ---------------------------------------------------------------------------
st.markdown("### 🔗 Pipeline 总览")
st.markdown(
    styles.pipeline_flow_html(),
    unsafe_allow_html=True,
)
legend_col1, legend_col2, legend_col3, legend_col4 = st.columns(4)
with legend_col1:
    st.markdown(
        '<div class="meta"><span style="display:inline-block;width:10px;height:10px;'
        'background:#3b82f6;border-radius:2px;vertical-align:middle;"></span> LLM 节点</div>',
        unsafe_allow_html=True,
    )
with legend_col2:
    st.markdown(
        f'<div class="meta"><span style="display:inline-block;width:10px;height:10px;'
        f'background:{styles.COLORS["risk_0"]};border-radius:2px;vertical-align:middle;"></span>'
        f' Python 节点</div>',
        unsafe_allow_html=True,
    )
with legend_col3:
    st.markdown(
        f'<div class="meta"><span style="display:inline-block;width:10px;height:10px;'
        f'background:{styles.COLORS["risk_3"]};border-radius:2px;vertical-align:middle;"></span>'
        f' 危机模板分支（risk=3）</div>',
        unsafe_allow_html=True,
    )
with legend_col4:
    st.markdown(
        f'<div class="meta"><span style="display:inline-block;width:10px;height:10px;'
        f'background:rgba(217,83,79,0.5);border-radius:2px;vertical-align:middle;"></span>'
        f' 输出拦截分支（Step 6b）</div>',
        unsafe_allow_html=True,
    )
st.markdown("")


# ---------------------------------------------------------------------------
# 模型状态 + 总览
# ---------------------------------------------------------------------------
col_a, col_b, col_c, col_d, col_e = st.columns(5)
all_runs = state.get_all_pipeline_runs()
total_runs = len(all_runs)
alerts = sum(1 for r in all_runs if r.parent_alert)
critic_alerts = sum(1 for r in all_runs if r.critic_alert)
crisis_count = sum(1 for r in all_runs if r.used_crisis_template)
intercepted_count = sum(1 for r in all_runs if getattr(r, "critic_intercepted", False))

with col_a:
    st.metric("总运行次数", total_runs)
with col_b:
    st.metric("家长风险提醒", alerts)
with col_c:
    st.metric("批判 Agent 告警", critic_alerts)
with col_d:
    st.metric("危机模板触发", crisis_count)
with col_e:
    st.metric("输出拦截替换", intercepted_count)

st.markdown(
    f"""
    <div class="anxin-card" style="margin: 12px 0 24px;">
        <span class="meta">主回复模型：</span><b>{llm_client.get_main_model_name()}</b>
        &nbsp;·&nbsp;
        <span class="meta">轻量模型：</span><b>{llm_client.get_small_model_name()}</b>
        &nbsp;·&nbsp;
        <span class="meta">LLM 状态：</span>
        <b>{'🟢 已接入' if llm_client.is_llm_available() else '🟡 脚本回退模式（无 API Key）'}</b>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# 最近一次 Pipeline 运行的决策链
# ---------------------------------------------------------------------------
latest = state.get_latest_pipeline()

st.markdown("### 最近一次运行的决策链")

if latest is None:
    st.info(
        "还没有运行记录。先到「儿童端」发一条消息或点击演示案例，再回到这里看决策链。"
    )
    if st.button("💬 去儿童端聊天", type="primary"):
        st.switch_page("pages/1_安心童伴.py")
    st.stop()


# 用户输入 + 风险概览
st.markdown(
    f"""
    <div class="anxin-card">
        <div class="meta">用户输入</div>
        <div style="font-size: 16px; margin: 4px 0 8px;">{latest.decision_record['user_input']}</div>
        <div>
            {styles.risk_badge(latest.risk_level)}
            &nbsp;<span class="meta">topic: <b>{latest.topic}</b></span>
            &nbsp;<span class="meta">strategy: <b>{latest.strategy}</b></span>
            &nbsp;{('⚠️ <b>家长提醒已触发</b>' if latest.parent_alert else '✓ 无家长提醒')}
            &nbsp;{('🔴 <b>批判 Agent 告警</b>' if latest.critic_alert else '✓ 批判 Agent 通过')}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("")
st.markdown("#### 本次运行链路")

# 本次运行的实际链路高亮（包括危机/拦截分支）
_active_steps = [s.step for s in latest.steps]
_flow_html = styles.pipeline_flow_html(
    active_steps=_active_steps,
    crisis_path=latest.used_crisis_template,
    intercepted=getattr(latest, "critic_intercepted", False),
)
st.markdown(_flow_html, unsafe_allow_html=True)

st.markdown("")
st.markdown("#### 7 步 Pipeline · 详细步骤")

for step in latest.steps:
    type_class = "llm" if step.type == "llm" else "python"
    type_label = "LLM" if step.type == "llm" else "Python"
    if step.step == "4-5":
        type_class = "crisis"
        type_label = "危机"
    elif step.step == "6b":
        type_class = "intercept"
        type_label = "拦截"
    st.markdown(
        f"""
        <div class="pipeline-step {type_class}">
            <div style="display:flex; justify-content:space-between; align-items:baseline;">
                <div>
                    <b>Step {step.step} · {step.name}</b>
                    <span style="margin-left: 8px; font-size: 11px; padding: 1px 6px; border-radius: 9999px;
                         background-color: rgba(28,28,28,0.06); color: #5f5f5d;">{type_label}</span>
                </div>
                <div class="meta">{step.latency_ms} ms</div>
            </div>
            <div class="meta" style="margin-top: 4px;">输入：{step.input_summary}</div>
            <div class="meta">输出：{step.output_summary}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 关键步骤的详情
    if step.step == "1":
        # 关键词检测详情
        d = step.detail
        hits = d.get("all_hits", [])
        if hits:
            for h in hits:
                # 家长话题偏好命中用特殊颜色标记
                cat = h.get("category", "")
                color_hint = ""
                if cat == "parent_forbidden_topic":
                    color_hint = "color: #D9534F;"
                elif cat == "parent_limited_topic":
                    color_hint = "color: #E89B47;"
                st.markdown(
                    f'<div class="meta" style="margin-left: 20px; {color_hint}">'
                    f'· {h["category_label"]}（{h["raw_confidence"]:.2f}）'
                    f' — 关键词：{", ".join(h["keywords"])}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="meta" style="margin-left: 20px;">· 无关键词命中</div>',
                unsafe_allow_html=True,
            )

    elif step.step == "2":
        d = step.detail
        st.markdown(
            f'<div class="meta" style="margin-left: 20px;">'
            f'topic=<b>{d["topic"]}</b>, risk_level=<b>{d["risk_level"]}</b>, '
            f'needs_parent_alert={d["needs_parent_alert"]}, source={d["source"]}<br>'
            f'原因：{d["reasoning"]}</div>',
            unsafe_allow_html=True,
        )

    elif step.step == "3":
        d = step.detail
        st.markdown(
            f'<div class="meta" style="margin-left: 20px;">'
            f'策略：{d["strategy_label"]}<br>原因：{d["reasoning"]}</div>',
            unsafe_allow_html=True,
        )

    elif step.step == "4":
        sp = step.detail.get("system_prompt", "")
        preview = sp if len(sp) < 800 else sp[:800] + "…（截断）"
        with st.expander("查看完整 System Prompt", expanded=False):
            st.code(preview, language="markdown")

    elif step.step == "5":
        d = step.detail
        st.markdown(
            f'<div class="meta" style="margin-left: 20px;">'
            f'模型：{d["model"]}<br>首字延迟：{d["first_token_ms"]} ms · 回复长度：{d["reply_length"]} 字'
            f'{" · ⚠️ 使用脚本回退" if d.get("used_fallback") else ""}</div>',
            unsafe_allow_html=True,
        )

    elif step.step == "6":
        d = step.detail
        if d.get("alert"):
            st.markdown(
                f'<div class="meta" style="margin-left: 20px; color: #D9534F;">'
                f'⚠️ 告警 · 问题类型：{d["issue"]} · 严重度：{d["severity"]}<br>'
                f'修正建议：{d["suggestion"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="meta" style="margin-left: 20px;">✓ 通过，未触发告警（source={d["source"]}）</div>',
                unsafe_allow_html=True,
            )

    elif step.step == "6b":
        d = step.detail
        st.markdown(
            f'<div class="meta" style="margin-left: 20px; color: #D9534F;">'
            f'🔴 输出拦截 · 问题类型：{d["reason"]} · 严重度：{d["severity"]}<br>'
            f'原始回复预览：{d["original_reply_preview"]}<br>'
            f'已替换为安全模板：{d["safe_template"]}</div>',
            unsafe_allow_html=True,
        )

    elif step.step == "4-5":
        # 危机模板
        st.markdown(
            f'<div class="meta" style="margin-left: 20px;">'
            f'risk_level=3，跳过 LLM 自由生成，使用预置危机模板：<br>'
            f'{step.detail.get("crisis_template", "")}</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# 最终回复
# ---------------------------------------------------------------------------
st.markdown("")
st.markdown("#### 最终回复（展示给儿童的）")
st.markdown(
    f'<div class="anxin-card" style="white-space: pre-wrap;">{latest.final_reply}</div>',
    unsafe_allow_html=True,
)

if getattr(latest, "critic_intercepted", False) and latest.original_intercepted_reply:
    with st.expander("🔴 查看被拦截的原始回复（未展示给孩子）", expanded=False):
        st.markdown(
            f'<div class="anxin-card" style="white-space: pre-wrap; '
            f'border-left: 4px solid #D9534F;">{latest.original_intercepted_reply}</div>',
            unsafe_allow_html=True,
        )
    st.warning(
        f"批判 Agent 发现问题：{latest.critic_detail.get('issue', '')} "
        f"（{latest.critic_detail.get('severity', '')}）— "
        f"已自动拦截并用安全模板替换。{latest.critic_detail.get('suggestion', '')}"
    )
elif latest.critic_alert:
    st.warning(
        f"批判 Agent 发现问题：{latest.critic_detail.get('issue', '')} "
        f"（{latest.critic_detail.get('severity', '')}）— "
        f"{latest.critic_detail.get('suggestion', '')}"
    )


# ---------------------------------------------------------------------------
# 完整决策记录 JSON
# ---------------------------------------------------------------------------
st.markdown("")
with st.expander("查看完整决策记录 JSON", expanded=False):
    st.json(latest.decision_record)


# ---------------------------------------------------------------------------
# 历史运行列表
# ---------------------------------------------------------------------------
st.markdown("")
st.markdown("### 历史运行记录")

if not all_runs:
    st.caption("（暂无）")
else:
    for i, r in enumerate(all_runs):
        risk_color = ["#7BB76E", "#E8C547", "#E89B47", "#D9534F"][r.risk_level]
        col_x, col_y, col_z, col_w = st.columns([3, 2, 2, 1])
        with col_x:
            st.markdown(
                f'<div><b>#{len(all_runs) - i}</b> · '
                f'<span style="color:{risk_color};">●</span> '
                f'{r.decision_record["user_input"][:30]}{"…" if len(r.decision_record["user_input"]) > 30 else ""}</div>'
                f'<div class="meta">topic: {r.topic} · strategy: {r.strategy}'
                f'{" · ⚠️家长提醒" if r.parent_alert else ""}'
                f'{" · 🔴批判告警" if r.critic_alert else ""}</div>',
                unsafe_allow_html=True,
            )
        with col_y:
            st.caption(f"时间：{r.decision_record['timestamp']}")
        with col_z:
            st.caption(f"风险等级：{r.risk_level}")
        with col_w:
            if st.button("查看", key=f"view_run_{i}"):
                # 把这条设为最新查看的（不覆盖 latest_pipeline，只是滚动定位）
                st.session_state["_view_run_idx"] = i
                st.rerun()


st.markdown("")
st.markdown("---")
nav1, nav2, nav3 = st.columns(3)
with nav1:
    if st.button("💬 回到聊天", use_container_width=True):
        st.switch_page("pages/1_安心童伴.py")
with nav2:
    if st.button("👨‍👩‍👧 家长守护", use_container_width=True):
        st.switch_page("pages/4_家长守护.py")
with nav3:
    if st.button("🧪 测试覆盖", use_container_width=True):
        st.switch_page("pages/5_测试覆盖.py")
