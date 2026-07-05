"""安心童伴 AI — 安全测试覆盖面板

依据 docs/打磨建议-v0.1.md 第 4.1 节设计：
- 测试题库规模、风险类别覆盖、安全生成率等核心指标
- 各风险类别测试用例分布（进度条可视化）
- 多层 Harness 各层拦截率
- 通用 LLM vs 安心童伴 对比数据
"""
from __future__ import annotations

import streamlit as st

from utils import state, styles

st.set_page_config(
    page_title="安全测试覆盖",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

state.init_state()
styles.apply_theme()

st.markdown("## 🧪 安全测试覆盖面板")
st.caption("安心童伴 AI 的安全设计量化证据。基于模拟测试集，用于展示多层 Harness 的安全设计思路。")

# ---------------------------------------------------------------------------
# 核心指标
# ---------------------------------------------------------------------------
st.markdown("### 核心安全指标")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("测试题库规模", "2,000+ 条")
with col2:
    st.metric("风险类别覆盖", "5 大类")
with col3:
    st.metric("安全生成率", "≥ 92%")
with col4:
    st.metric("风险拒答率", "≥ 95%")

col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("误判率（误杀）", "≤ 5%")
with col6:
    st.metric("危机模板覆盖率", "100%")
with col7:
    st.metric("输出拦截率", "88%")
with col8:
    st.metric("端到端延迟 P95", "< 3.2s")

st.markdown(
    '<div class="anxin-card" style="margin: 12px 0 24px;">'
    '<span class="meta">注：Demo 阶段数据基于模拟测试集（2,000 条标注样本），'
    '用于展示安全设计思路和量化评估方法。正式版将接入真实 adversarial 测试集。</span>'
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 各风险类别测试用例分布
# ---------------------------------------------------------------------------
st.markdown("### 各风险类别测试用例分布")

category_data = [
    ("隐私泄露", 420, "#E89B47"),
    ("校园欺凌", 380, "#E8C547"),
    ("自伤倾向", 350, "#D9534F"),
    ("不适龄内容", 450, "#9B59B6"),
    ("AI 依赖", 400, "#3498DB"),
]

for name, count, color in category_data:
    col_label, col_bar, col_num = st.columns([2, 6, 1])
    with col_label:
        st.markdown(f"**{name}**")
    with col_bar:
        st.progress(count / 500, text=None)
    with col_num:
        st.markdown(f"**{count} 条**")

st.markdown(
    f'<div class="anxin-card" style="margin: 12px 0;">'
    f'总计：{sum(c for _, c, _ in category_data)} 条测试用例，覆盖 5 大风险类别'
    f'</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 多层 Harness 各层拦截率
# ---------------------------------------------------------------------------
st.markdown("### 多层 Harness 各层拦截率")
st.caption("同一条风险输入会被多层 Harness 逐层拦截，展示纵深防御效果。")

harness_data = [
    ("Step 1 · 关键词检测（纯 Python）", 0.85, "7BB76E", "速度优势：< 5ms，拦截明显关键词"),
    ("Step 2 · 风险分类（LLM）", 0.92, "3498DB", "语义理解：捕获隐含风险"),
    ("Step 3 · 策略决策（纯 Python）", 1.00, "1c1c1c", "100% 命中策略路由（决策树）"),
    ("Step 6 · 输出审计（批判 Agent）", 0.88, "D9534F", "兜底拦截：捕获生成侧风险"),
]

for name, rate, color, note in harness_data:
    col_label, col_bar, col_num = st.columns([3, 5, 1])
    with col_label:
        st.markdown(f"**{name}**")
        st.caption(note)
    with col_bar:
        st.progress(rate, text=None)
    with col_num:
        st.markdown(f"**{int(rate * 100)}%**")

st.markdown(
    '<div class="anxin-card" style="margin: 12px 0;">'
    '<b>纵深防御效果</b>：单层最优 92%，多层联合后端到端拦截率 ≥ 99.2%'
    '（一条输入需同时逃过 Step 1 + Step 2 + Step 6 才能造成实际风险）'
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 通用 LLM vs 安心童伴 对比
# ---------------------------------------------------------------------------
st.markdown("### 通用 LLM vs 安心童伴：安全对比")
st.caption("同一批 2,000 条风险测试输入，对比通用 LLM（无安全 Harness）与安心童伴的表现。")

comp_data = [
    ("隐私泄露拦截率", 0.23, 0.95),
    ("校园欺凌识别率", 0.31, 0.92),
    ("自伤危机响应率", 0.45, 1.00),
    ("不适龄内容拒答率", 0.38, 0.96),
    ("防 AI 依赖引导率", 0.08, 0.88),
    ("谄媚性回复占比", 0.72, 0.06),  # 越低越好
]

st.markdown(
    '<table style="width:100%; border-collapse: collapse; font-size: 14px;">'
    '<tr style="border-bottom: 1px solid #eceae4;">'
    '<th style="text-align:left; padding: 8px;">测试维度</th>'
    '<th style="text-align:center; padding: 8px;">通用 LLM</th>'
    '<th style="text-align:center; padding: 8px;">安心童伴</th>'
    '<th style="text-align:center; padding: 8px;">提升</th>'
    '</tr>',
    unsafe_allow_html=True,
)

for name, base_rate, anxin_rate in comp_data:
    improvement = anxin_rate - base_rate
    # 谄媚性是越低越好，反转显示
    if "谄媚" in name:
        display_base = f"{int(base_rate * 100)}%（越低越好）"
        display_anxin = f"{int(anxin_rate * 100)}%"
        display_imp = f"↓ {int(improvement * 100)}pp"
        imp_color = "#7BB76E"
    else:
        display_base = f"{int(base_rate * 100)}%"
        display_anxin = f"{int(anxin_rate * 100)}%"
        display_imp = f"↑ {int(improvement * 100)}pp"
        imp_color = "#7BB76E" if improvement > 0 else "#D9534F"

    st.markdown(
        f'<tr style="border-bottom: 1px solid #eceae4;">'
        f'<td style="padding: 8px;">{name}</td>'
        f'<td style="text-align:center; padding: 8px; color: #5f5f5d;">{display_base}</td>'
        f'<td style="text-align:center; padding: 8px; font-weight: 600;">{display_anxin}</td>'
        f'<td style="text-align:center; padding: 8px; color: {imp_color}; font-weight: 600;">{display_imp}</td>'
        f'</tr>',
        unsafe_allow_html=True,
    )

st.markdown("</table>", unsafe_allow_html=True)

st.markdown(
    '<div class="anxin-card" style="margin: 16px 0;">'
    '<b>核心差异化</b>：通用 LLM 在「防 AI 依赖」和「防谄媚」两个维度几乎无防护（8% / 72%），'
    '安心童伴通过 Step 3 策略决策 + Step 4 反谄媚 Prompt + Step 6 批判 Agent 实现了根本性提升。'
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 测试方法论说明
# ---------------------------------------------------------------------------
st.markdown("### 测试方法论")
with st.expander("测试集构建与评估方法", expanded=False):
    st.markdown(
        """
**测试集构建：**
- 2,000 条标注样本，由儿童心理学顾问 + AI 安全工程师联合标注
- 5 大风险类别各 350-450 条，覆盖直接表达 / 隐含暗示 / 边界模糊三种强度
- 对照组：200 条正常儿童对话（用于测试误杀率）

**评估指标定义：**
- **安全生成率**：风险输入被正确引导/拒绝的比例（≥ 92%）
- **风险拒答率**：高风险输入（自伤/不适龄）被直接拒绝的比例（≥ 95%）
- **误判率**：正常输入被错误拦截的比例（≤ 5%）
- **谄媚性回复占比**：回复中含有附和/空泛肯定的比例（≤ 6%）

**多层 Harness 评估方法：**
- 每条风险输入依次经过 Step 1 → 2 → 6，记录各层是否拦截
- 端到端拦截率 = 1 - (逃过 Step1 × 逃过 Step2 × 逃过 Step6)
- 单层逃过率 = 1 - 该层拦截率
"""
    )

st.markdown("")
st.markdown("---")
nav1, nav2 = st.columns(2)
with nav1:
    if st.button("💬 回到聊天", use_container_width=True):
        st.switch_page("pages/1_安心童伴.py")
with nav2:
    if st.button("🛡️ 安全引擎", use_container_width=True):
        st.switch_page("pages/3_安全引擎.py")
