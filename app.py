"""安心童伴 AI — 首页

面向 8-14 岁中小学生的安全 AI 陪伴伙伴。
"""
from __future__ import annotations

import streamlit as st

from utils import state, styles

st.set_page_config(
    page_title="安心童伴 AI",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

state.init_state()
styles.apply_theme()

C = styles.COLORS

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
_feature_pills = "".join([
    styles.pill("三层安全架构", "#5b8b4d", "rgba(123,183,110,0.18)"),
    styles.pill("策展式记忆", "#2563eb", "rgba(59,130,246,0.15)"),
    styles.pill("反谄媚机制", "#a08a2c", "rgba(232,197,71,0.22)"),
    styles.pill("合规先行", "#b03a37", "rgba(217,83,79,0.14)"),
])

st.markdown(
    f"""
    <div style="text-align:center; padding: 56px 24px 40px; margin-bottom: 16px;
                background: linear-gradient(135deg, rgba(123,183,110,0.08) 0%,
                    rgba(232,197,71,0.06) 50%, rgba(217,83,79,0.06) 100%);
                border: 1px solid {C['border']}; border-radius: 16px;">
        <div style="font-size: 56px; line-height: 1; letter-spacing: 10px;">🌱🤝🛡️</div>
        <h1 style="margin: 20px 0 10px; font-size: 60px; font-weight: 600;
                   letter-spacing: -1.5px; line-height: 1.1;">安心童伴 AI</h1>
        <p style="margin: 0; font-size: 18px; line-height: 1.38; color: {C['muted_gray']};">
            有边界的可信 AI 伙伴 · 为 8-14 岁中小学生而生
        </p>
        <div style="margin-top: 18px;">{_feature_pills}</div>
        <div class="meta" style="margin-top: 14px; font-size: 12px;">
            对应《人工智能拟人化互动服务管理暂行办法》（2026.7.15 施行）
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 简介
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="anxin-card" style="text-align:center; padding: 24px 28px;">
        <p style="font-size:16px; line-height:1.7; margin:0;">
        安心童伴是一款专为 8-14 岁孩子设计的 AI 陪伴伙伴。<br>
        不同于通用聊天机器人，它在每一次对话中都会经过多层安全检测——<br>
        保护隐私、识别风险、拒绝谄媚，引导孩子走向真实世界的连接。<br>
        <b>让 AI 成为孩子走向世界的桥梁，而非虚拟的避难所。</b>
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 入口卡片
# ---------------------------------------------------------------------------
c1, c2 = st.columns(2)
with c1:
    st.markdown(
        f"""
        <div class="anxin-card hoverable" style="text-align:center; padding: 28px 16px 22px;">
            <div style="font-size: 44px; line-height: 1;">💬</div>
            <div style="font-weight: 600; font-size: 18px; margin: 12px 0 4px; letter-spacing: -0.3px;">儿童端</div>
            <div class="meta" style="font-size: 13px;">安全聊天 · 故事陪伴 · 百科问答 · 情绪树洞</div>
            <div style="margin-top: 14px; font-size: 13px; color: {C['charcoal']};">进入 →</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("进入儿童端", use_container_width=True, type="primary"):
        st.switch_page("pages/1_安心童伴.py")
with c2:
    st.markdown(
        f"""
        <div class="anxin-card hoverable" style="text-align:center; padding: 28px 16px 22px;">
            <div style="font-size: 44px; line-height: 1;">👨‍👩‍👧</div>
            <div style="font-weight: 600; font-size: 18px; margin: 12px 0 4px; letter-spacing: -0.3px;">家长端</div>
            <div class="meta" style="font-size: 13px;">主动预警 · 情绪趋势 · 话题偏好 · 使用统计</div>
            <div style="margin-top: 14px; font-size: 13px; color: {C['charcoal']};">独立入口 ↗</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("家长端为独立应用入口：`streamlit run parent_app.py`")

# ---------------------------------------------------------------------------
# Stats bar（数据来自 pages/0 安全测试指标与测试方法论）
# ---------------------------------------------------------------------------
_stats = [
    ("7 步", "安全决策 Pipeline"),
    ("5 类", "风险场景覆盖"),
    ("2,000+", "模拟测试样本"),
    ("99.2%", "多层联合拦截率"),
]
_stats_html = "".join(
    f'<div style="flex:1 1 0; min-width:120px; text-align:center; padding: 6px 4px;">'
    f'<div style="font-size:44px; font-weight:600; letter-spacing:-1.2px; line-height:1.1; '
    f'color:{C["charcoal"]};">{num}</div>'
    f'<div class="meta" style="margin-top:6px;">{label}</div>'
    f'</div>'
    for num, label in _stats
)
st.markdown(
    f'<div class="anxin-card" style="display:flex; flex-wrap:wrap; '
    f'justify-content:space-between; padding: 22px 20px; margin-top: 20px;">'
    f'{_stats_html}</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 了解更多
# ---------------------------------------------------------------------------
guide_col1, guide_col2, guide_col3 = st.columns([1, 1, 1])
with guide_col2:
    if st.button("📖 使用指南 · 了解更多功能与安全设计", use_container_width=True):
        st.switch_page("pages/0_使用指南.py")

# ---------------------------------------------------------------------------
# 页脚
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div style="text-align: center; margin-top: 32px; padding-top: 20px;
                border-top: 1px solid #eceae4;">
        <span class="meta">安心童伴 AI · 有边界的可信 AI 伙伴</span>
    </div>
    """,
    unsafe_allow_html=True,
)
