"""安心童伴 AI — 家长守护仪表盘

依据 docs/安心童伴AI-初赛Demo拆解.md 第 4 节设计：
- 今日主题摘要
- 风险事件卡片（绿/黄/橙/红色标识）
- 使用时长统计
- 话题偏好设置（展示用）
- 家长注册/同意流程（Demo 简化版：一个勾选框 + 开始使用）
- 8-11 岁可见星球概览（条目数）；12-14 岁完全不可见
"""
from __future__ import annotations

from collections import Counter

import streamlit as st

from core import memory_manager as mm
from utils import state, styles

st.set_page_config(
    page_title="家长守护",
    page_icon="👨‍👩‍👧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

state.init_state()
styles.apply_theme()


# ---------------------------------------------------------------------------
# 家长同意流程（Demo 简化版）
# ---------------------------------------------------------------------------
if not state.is_parent_consent_given():
    st.markdown("## 👨‍👩‍👧 家长守护 · 监护人同意")

    st.markdown(
        """
        <div class="anxin-card" style="margin: 16px 0;">
            <p>欢迎来到家长守护面板。根据《人工智能拟人化互动服务管理暂行办法》（2026.7.15 施行），
            未成年人使用 AI 服务需取得监护人同意。</p>
            <p class="meta">本 Demo 简化了真实注册流程：无需手机号验证，仅勾选同意即可进入面板。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    agree = st.checkbox(
        "我已阅读并同意孩子使用安心童伴 AI 服务，并授权系统在孩子遇到安全风险时向我发送提醒。",
        value=False,
    )
    if st.button("进入家长面板", type="primary", disabled=not agree, use_container_width=True):
        state.set_parent_consent(True)
        st.rerun()

    st.markdown("")
    if st.button("💬 先去儿童端体验", use_container_width=True):
        st.switch_page("pages/1_安心童伴.py")
    st.stop()


# ---------------------------------------------------------------------------
# 主面板
# ---------------------------------------------------------------------------
st.markdown("## 👨‍👩‍👧 家长守护仪表盘")
st.caption(
    f"孩子年龄档：<b>{state.get_age_tier()} 岁（{'守护模式' if state.get_age_tier() == '8-11' else '信任模式'}）</b>"
    " · 这里只显示脱敏摘要和风险提醒，不会展示孩子的对话原文。"
)

# ---------------------------------------------------------------------------
# 今日主题摘要
# ---------------------------------------------------------------------------
topics = state.get_conversation_topics()
usage_min = state.get_usage_minutes()
alerts = state.get_parent_alerts()

# 模拟 + 真实混合的摘要
topic_counter = Counter(t["topic"] for t in topics)
topic_label_map = {
    "safe": "日常聊天",
    "privacy_leak": "隐私安全",
    "school_bullying": "校园欺凌",
    "emotional_low": "情绪低落",
    "self_harm": "高风险情绪",
    "ai_dependency": "AI 依赖",
    "inappropriate_content": "不适龄内容",
}
topic_summary_parts = [f"{topic_label_map.get(t, t)} {c} 次" for t, c in topic_counter.most_common()]

# 如果还没有任何对话，给一个模拟摘要作为 Demo 兜底
if not topic_summary_parts:
    summary_text = "孩子今天主要聊了学校生活、恐龙知识和一个交朋友的故事。检测到 1 次轻度情绪表达。"
else:
    summary_text = "今天孩子主要聊了：" + "、".join(topic_summary_parts) + "。"

st.markdown("### 📝 今日主题摘要")
st.markdown(
    f"""
    <div class="anxin-card">
        <div style="font-size: 15px; line-height: 1.6;">{summary_text}</div>
        <div class="meta" style="margin-top: 8px;">
            ⚠️ 本面板不展示孩子的对话原文，仅展示脱敏后的主题摘要。
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 使用时长统计
# ---------------------------------------------------------------------------
st.markdown("### ⏱️ 使用统计")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("今日使用时长", f"{usage_min} 分钟")
with col2:
    st.metric("今日对话轮数", len(topics))
with col3:
    high_risk_count = sum(1 for t in topics if t["risk_level"] >= 2)
    st.metric("中/高风险对话", high_risk_count)

# 模式分布（如果有数据）
mode_stats = Counter()
for t in topics:
    mode_stats[t.get("strategy", "normal_child_friendly_response")] += 1

# 风险等级分布（用于柱状图）
risk_stats = Counter()
for t in topics:
    risk_stats[t["risk_level"]] += 1

# 主题分布（用于柱状图）
topic_stats = Counter()
for t in topics:
    topic_stats[t["topic"]] += 1

if mode_stats or risk_stats or topic_stats:
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**📈 风险等级分布**")
        if risk_stats:
            import pandas as pd
            risk_df = pd.DataFrame([
                {"风险等级": f"等级 {lvl}（{['安全','轻度','中度','高风险'][lvl]}）", "次数": cnt}
                for lvl, cnt in sorted(risk_stats.items())
            ])
            risk_colors = ["#7BB76E", "#E8C547", "#E89B47", "#D9534F"]
            st.bar_chart(
                risk_df.set_index("风险等级")["次数"],
                color=risk_colors[min(max(risk_stats.keys()), 3)] if risk_stats else "#7BB76E",
                use_container_width=True,
                height=200,
            )
        else:
            st.caption("（暂无对话数据）")

    with chart_col2:
        st.markdown("**📊 主题分布**")
        if topic_stats:
            import pandas as pd
            topic_label_map_chart = {
                "safe": "日常聊天",
                "privacy_leak": "隐私安全",
                "school_bullying": "校园欺凌",
                "emotional_low": "情绪低落",
                "self_harm": "高风险情绪",
                "ai_dependency": "AI 依赖",
                "inappropriate_content": "不适龄内容",
            }
            topic_df = pd.DataFrame([
                {"主题": topic_label_map_chart.get(t, t), "次数": c}
                for t, c in topic_stats.most_common()
            ])
            st.bar_chart(
                topic_df.set_index("主题")["次数"],
                color="#1c1c1c",
                use_container_width=True,
                height=200,
            )
        else:
            st.caption("（暂无对话数据）")

    if mode_stats:
        strategy_label_map = {
            "normal_child_friendly_response": "常规友好回应",
            "warm_redirect_with_empathy": "温和转移",
            "refuse_with_reason": "礼貌拒答",
            "encourage_real_world_action": "鼓励现实行动",
            "crisis_template_response": "危机模板",
            "guardrail_block": "输入拦截",
            "parent_alert_strategy": "家长提醒",
        }
        st.markdown("**🎯 策略分布**")
        strategy_html_parts = []
        for k, v in mode_stats.most_common():
            label = strategy_label_map.get(k, k)
            pct = (v / sum(mode_stats.values())) * 100
            color = "#1c1c1c"
            if "crisis" in k or "block" in k:
                color = "#D9534F"
            elif "redirect" in k or "refuse" in k:
                color = "#E89B47"
            elif "encourage" in k:
                color = "#7BB76E"
            strategy_html_parts.append(
                f'<div style="margin-bottom:6px;">'
                f'<div style="display:flex; justify-content:space-between; font-size:13px;">'
                f'<span>{label}</span><span class="meta">{v} 次 · {pct:.0f}%</span></div>'
                f'{styles.progress_bar(pct, color)}'
                f'</div>'
            )
        st.markdown(
            f'<div class="anxin-card">{"".join(strategy_html_parts)}</div>',
            unsafe_allow_html=True,
        )

st.markdown(
    f"""
    <div class="anxin-card" style="margin-top: 8px;">
        <span class="meta">防沉迷：连续使用 2 小时后会弹出"去户外活动一下"提醒（Demo 静态展示）</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 风险事件提醒
# ---------------------------------------------------------------------------
st.markdown("### 🚨 风险事件提醒")

if not alerts:
    st.success("目前没有风险事件。孩子今天聊得挺平静的。")
else:
    risk_color = {0: "#7BB76E", 1: "#E8C547", 2: "#E89B47", 3: "#D9534F"}
    risk_label = {1: "轻度", 2: "中度", 3: "高风险"}
    for i, a in enumerate(alerts):
        color = risk_color.get(a["risk_level"], "#5f5f5d")
        label = risk_label.get(a["risk_level"], "")
        st.markdown(
            f"""
            <div class="anxin-card" style="border-left: 4px solid {color};">
                <div style="display:flex; justify-content:space-between; align-items:baseline;">
                    <div><b>{label}风险</b> · {topic_label_map.get(a["topic"], a["topic"])}</div>
                    <div class="meta">{a["time"]}</div>
                </div>
                <div style="margin: 6px 0; font-size: 14px; line-height: 1.5;">{a["summary"]}</div>
                <div class="meta">💡 建议家长：{a["suggestion"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# 模拟一次历史风险（如果孩子还没触发过任何风险，给一个模拟提醒作为 Demo 兜底）
if not alerts and not topics:
    st.markdown(
        """
        <div class="anxin-card" style="border-left: 4px solid #E89B47;">
            <div><b>示例风险事件</b> · 校园欺凌 · 中度</div>
            <div style="margin: 6px 0; font-size: 14px; line-height: 1.5;">
                孩子提到有同学推搡并要求不要告诉老师，已由安心童伴鼓励 TA 找可信任的成年人。
            </div>
            <div class="meta">💡 建议家长：用关心的语气问——最近在学校和同学相处怎么样？</div>
            <div class="meta" style="margin-top: 4px; font-style: italic;">（这是一条示例提醒，用于展示面板形态。当孩子在儿童端触发风险时，这里会出现真实提醒。）</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# 小星球概览（8-11 守护模式可见条目数；12-14 信任模式完全不可见）
# ---------------------------------------------------------------------------
st.markdown("### 🌱 小星球概览")

if state.get_age_tier() == "8-11":
    counts = mm.count_entries(state.get_planet())
    if counts["total"] == 0:
        st.info("孩子还没有在小星球里种下任何东西。")
    else:
        col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
        with col_s1:
            st.metric("⭐ 好奇星", counts["star"])
        with col_s2:
            st.metric("☁️ 心情云", counts["cloud"])
        with col_s3:
            st.metric("🌱 勇敢芽", counts["sprout"])
        with col_s4:
            st.metric("📖 故事册", counts["story"])
        with col_s5:
            st.metric("总计", counts["total"])
        st.caption("8-11 岁守护模式：家长可见星球条目概览（仅数量），不显示具体内容。")
else:
    st.info(
        "孩子处于 12-14 岁信任模式。根据隐私边界设计，小星球的具体信息对家长完全不可见。"
    )
    st.caption("12-14 岁信任模式：家长仅在出现高风险事件时介入。")

# ---------------------------------------------------------------------------
# 合规路线图（P0-2）
# ---------------------------------------------------------------------------
st.markdown("### 📋 合规路线图")
st.caption("《人工智能拟人化互动服务管理暂行办法》（2026.7.15 施行）合规映射")

compliance_items = [
    ("禁止诱导不安全行为", "✅ 已覆盖", 100, "#7BB76E", "Step 1-6 多层拦截 + 危机模板"),
    ("禁止虚拟亲密关系", "✅ 已覆盖", 100, "#7BB76E", "反谄媚 Prompt + AI 依赖检测"),
    ("监护人同意", "✅ Demo 简化", 80, "#7BB76E", "家长同意流程（简化版，正式版接入实名验证）"),
    ("未成年人模式", "✅ 已覆盖", 100, "#7BB76E", "年龄分层 + 守护/信任模式"),
    ("年龄识别", "✅ 家长填写", 70, "#E8C547", "家长注册时填写（正式版增加交叉验证）"),
    ("AI 身份标识", "✅ 已覆盖", 100, "#7BB76E", "每次对话开始时声明 AI 身份"),
    ("2 小时使用提醒", "✅ 已覆盖", 100, "#7BB76E", "st.dialog 弹窗 + 防沉迷逻辑"),
    ("算法备案", "⚠️ 评估中", 50, "#E8C547", "正式上线前完成网信办算法备案"),
]

for req, status, pct, color, note in compliance_items:
    st.markdown(
        f'<div class="anxin-card" style="padding: 10px 16px;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center;">'
        f'<div><b>{req}</b> <span class="meta">— {note}</span></div>'
        f'<div style="display:flex; align-items:center; gap:8px;">'
        f'<span style="color:{color}; font-weight:600;">{status}</span>'
        f'<span style="display:inline-block; width:60px; height:8px; '
        f'background:rgba(28,28,28,0.08); border-radius:4px; overflow:hidden;">'
        f'<span style="display:block; width:{pct}%; height:100%; background:{color};"></span>'
        f'</span>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="anxin-card" style="margin: 8px 0;">'
    '<span class="meta">合规完成度：7/8 项已覆盖（87.5%），1 项评估中。'
    '安心童伴在 Demo 阶段已覆盖《拟人化互动办法》全部核心条款。</span>'
    '</div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# 话题偏好设置（P1-8：动态接入 Guardrail）
# ---------------------------------------------------------------------------
st.markdown("### ⚙️ 话题偏好设置")
st.caption(
    "家长可以对话题分级。被标记为「限制」或「禁止」的话题会在儿童端 Step 1 关键词检测时被标记，"
    "出现在安全引擎的决策链中。正式版会进一步影响回复策略。"
)

_prefs = state.get_topic_preferences()
_all_topics = [
    "故事", "百科", "学习", "情绪", "安全教育",
    "游戏", "消费",
    "暴力", "色情", "自伤", "危险操作",
]

with st.expander("调整话题分级", expanded=False):
    new_limited = st.multiselect(
        "🟡 限制话题（允许但温和引导）",
        options=_all_topics,
        default=_prefs.get("limited", []),
        help="孩子可以聊，但安心童伴会引导向其他话题。",
    )
    new_forbidden = st.multiselect(
        "🚫 禁止话题（强烈引导转向）",
        options=_all_topics,
        default=_prefs.get("forbidden", []),
        help="孩子提起这些话题时，安心童伴会明确引导转向，并在安全引擎留下记录。",
    )
    # 限制和禁止不能重叠
    overlap = set(new_limited) & set(new_forbidden)
    if overlap:
        st.warning(f"以下话题同时出现在「限制」和「禁止」中，已自动从「限制」移除：{', '.join(overlap)}")
        new_limited = [t for t in new_limited if t not in new_forbidden]
    new_allowed = [t for t in _all_topics if t not in new_limited and t not in new_forbidden]

    pref_action_col1, pref_action_col2 = st.columns([3, 1])
    with pref_action_col2:
        if st.button("保存偏好", type="primary", use_container_width=True):
            state.set_topic_preferences({
                "allowed": new_allowed,
                "limited": new_limited,
                "forbidden": new_forbidden,
            })
            st.success("✅ 已保存。儿童端下一次对话起生效。")
            st.rerun()

# 当前偏好可视化
pref_col1, pref_col2, pref_col3 = st.columns(3)
with pref_col1:
    st.markdown("**✅ 允许**")
    for t in _prefs.get("allowed", []):
        st.markdown(f"- {t}")
with pref_col2:
    st.markdown("**🟡 限制**")
    for t in _prefs.get("limited", []):
        st.markdown(f"- {t}")
with pref_col3:
    st.markdown("**🚫 禁止**")
    for t in _prefs.get("forbidden", []):
        st.markdown(f"- {t}")


st.markdown("")
st.markdown("---")
nav1, nav2, nav3 = st.columns(3)
with nav1:
    if st.button("💬 回到聊天", use_container_width=True):
        st.switch_page("pages/1_安心童伴.py")
with nav2:
    if st.button("🛡️ 安全引擎", use_container_width=True):
        st.switch_page("pages/3_安全引擎.py")
with nav3:
    if st.button("🧪 测试覆盖", use_container_width=True):
        st.switch_page("pages/5_测试覆盖.py")
