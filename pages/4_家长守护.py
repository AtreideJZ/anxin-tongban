"""安心童伴 AI — 家长守护（已迁移）

家长守护面板已独立为单独的应用入口。
"""
from __future__ import annotations

import streamlit as st

from utils import state, styles

st.set_page_config(
    page_title="家长守护",
    page_icon="👨‍👩‍👧",
    layout="centered",
    initial_sidebar_state="collapsed",
)

state.init_state()
styles.apply_theme()

st.markdown("## 👨‍👩‍👧 家长守护已迁移")

st.markdown(
    """
    <div class="anxin-card" style="text-align:center; margin: 24px 0;">
        <div style="font-size: 48px; margin-bottom: 12px;">📦</div>
        <p style="font-size: 16px;">家长守护面板现在是一个<b>独立的应用入口</b>。</p>
        <p class="meta">请在终端中运行以下命令打开家长端：</p>
        <div style="background:rgba(28,28,28,0.04); padding:12px 16px; border-radius:8px;
             font-family: monospace; font-size: 14px; margin: 12px 0;">
            streamlit run parent_app.py
        </div>
        <p class="meta">家长端与儿童端共享数据，但作为独立应用部署，支持分别访问。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

nav1, nav2 = st.columns(2)
with nav1:
    if st.button("💬 回到儿童端", use_container_width=True, type="primary"):
        st.switch_page("pages/1_安心童伴.py")
with nav2:
    if st.button("📖 使用指南", use_container_width=True):
        st.switch_page("pages/0_使用指南.py")
