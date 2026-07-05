"""Lovable 风格主题样式（依据 docs/DESIGN-lovable.md）

将 Lovable 的奶油底色 / 暖色边框 / 圆角 / 内阴影等视觉特征，
通过注入 CSS 映射到 Streamlit 的元素上。
"""
from __future__ import annotations

import streamlit as st


# 核心色板（与 .streamlit/config.toml 一致）
COLORS = {
    "cream":         "#f7f4ed",  # 页面背景
    "cream_surface": "#f7f4ed",  # 卡片背景
    "charcoal":      "#1c1c1c",  # 主文字
    "off_white":     "#fcfbf8",  # 深色按钮文字
    "muted_gray":    "#5f5f5d",  # 次要文字
    "border":        "#eceae4",  # 暖色边框
    "border_strong": "rgba(28,28,28,0.4)",
    "focus_shadow":  "rgba(0,0,0,0.1) 0px 4px 12px",
    "blue_ring":     "rgba(59,130,246,0.5)",
    # 风险等级色（用于安全引擎/家长端）
    "risk_0":        "#7BB76E",  # 安全绿
    "risk_1":        "#E8C547",  # 轻度黄
    "risk_2":        "#E89B47",  # 中度橙
    "risk_3":        "#D9534F",  # 高风险红
}


# 内阴影（深色按钮的标志性细节）
_BUTTON_INSET = (
    "rgba(255,255,255,0.2) 0px 0.5px 0px 0px inset,"
    "rgba(0,0,0,0.2) 0px 0px 0px 0.5px inset,"
    "rgba(0,0,0,0.05) 0px 1px 2px 0px"
)


_CSS = f"""
<style>
/* ===== 全局 ===== */
.stApp, .stApp > header, .stApp > .st-emotion-cache-uf99v3 {{
    background-color: {COLORS['cream']};
    color: {COLORS['charcoal']};
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", "PingFang SC",
                 "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}}

/* 主标题紧致、editorial 风格 */
h1, h2, h3 {{
    color: {COLORS['charcoal']};
    font-weight: 600 !important;
    letter-spacing: -0.6px;
    line-height: 1.15;
}}
h1 {{ letter-spacing: -1.2px; }}
h2 {{ letter-spacing: -0.9px; }}

/* 次要文字 */
p, li, span {{
    color: {COLORS['charcoal']};
}}

/* ===== 侧边栏 ===== */
section[data-testid="stSidebar"] {{
    background-color: {COLORS['cream']};
    border-right: 1px solid {COLORS['border']};
}}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {{
    color: {COLORS['charcoal']};
}}

/* ===== 按钮 ===== */
.stButton > button, .stDownloadButton > button {{
    border-radius: 6px;
    border: 1px solid {COLORS['border_strong']};
    background-color: {COLORS['cream']};
    color: {COLORS['charcoal']};
    padding: 8px 16px;
    font-weight: 400;
    transition: all 0.15s ease;
}}
/* 按钮内部文字（p/span）必须继承按钮颜色，否则全局 p{{color}} 会让深色按钮文字不可见 */
.stButton > button p,
.stButton > button span,
.stButton > button div,
.stDownloadButton > button p,
.stDownloadButton > button span,
.stDownloadButton > button div {{
    color: inherit !important;
}}
.stButton > button:hover {{
    background-color: rgba(28,28,28,0.04);
    border-color: {COLORS['border_strong']};
    color: {COLORS['charcoal']};
}}

/* 主按钮（深色）——仅匹配 kind=primary，避免把所有按钮都染黑 */
.stButton > button[kind="primary"] {{
    background-color: {COLORS['charcoal']};
    color: {COLORS['off_white']} !important;
    border: 1px solid {COLORS['charcoal']};
    box-shadow: {_BUTTON_INSET};
}}
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
.stButton > button[kind="primary"] div {{
    color: {COLORS['off_white']} !important;
}}
.stButton > button[kind="primary"]:hover {{
    opacity: 0.85;
    background-color: {COLORS['charcoal']};
    color: {COLORS['off_white']} !important;
}}
.stButton > button[kind="primary"]:hover p,
.stButton > button[kind="primary"]:hover span,
.stButton > button[kind="primary"]:hover div {{
    color: {COLORS['off_white']} !important;
}}

/* 禁用状态按钮：保持文字可读 */
.stButton > button:disabled,
.stButton > button[disabled] {{
    opacity: 0.5;
    color: {COLORS['muted_gray']} !important;
}}
.stButton > button:disabled p,
.stButton > button:disabled span,
.stButton > button:disabled div {{
    color: {COLORS['muted_gray']} !important;
}}

/* ===== 输入框 ===== */
.stTextInput > div > input,
.stTextArea > div > textarea,
.stChatInput > div > textarea {{
    background-color: {COLORS['cream']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    color: {COLORS['charcoal']};
}}
.stTextInput > div > input:focus,
.stTextArea > div > textarea:focus {{
    border-color: {COLORS['border_strong']};
    box-shadow: 0 0 0 2px {COLORS['blue_ring']};
}}

/* stChatInput 容器 */
div[data-testid="stChatInput"] {{
    border-color: {COLORS['border']} !important;
}}

/* ===== 卡片 / 容器 ===== */
.anxin-card {{
    background-color: {COLORS['cream']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
}}

/* 风险等级徽章 */
.risk-badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 600;
    color: {COLORS['off_white']};
}}
.risk-0 {{ background-color: {COLORS['risk_0']}; }}
.risk-1 {{ background-color: {COLORS['risk_1']}; color: {COLORS['charcoal']}; }}
.risk-2 {{ background-color: {COLORS['risk_2']}; }}
.risk-3 {{ background-color: {COLORS['risk_3']}; }}

/* 演示案例按钮（侧边栏） */
.case-btn {{
    text-align: left !important;
    border: 1px solid {COLORS['border']} !important;
    background-color: {COLORS['cream']} !important;
    color: {COLORS['charcoal']} !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    margin-bottom: 6px !important;
    font-size: 13px !important;
    width: 100%;
    transition: all 0.15s ease;
}}
.case-btn:hover {{
    background-color: rgba(28,28,28,0.04) !important;
    border-color: {COLORS['border_strong']} !important;
}}

/* 聊天消息气泡：保持 Streamlit 原生结构，仅微调背景 */
[data-testid="stChatMessage"] {{
    background-color: {COLORS['cream']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 12px 16px;
}}

/* 小星球卡片网格 */
.planet-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
}}
.planet-card {{
    background-color: {COLORS['cream']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 14px 16px;
    transition: all 0.15s ease;
}}
.planet-card:hover {{
    border-color: {COLORS['border_strong']};
}}

/* Pipeline 步骤时间轴 */
.pipeline-step {{
    background-color: {COLORS['cream']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    border-left: 3px solid {COLORS['charcoal']};
}}
.pipeline-step.llm {{
    border-left-color: #3b82f6;
}}
.pipeline-step.python {{
    border-left-color: #7BB76E;
}}
.pipeline-step.crisis {{
    border-left-color: {COLORS['risk_3']};
    background-color: rgba(217, 83, 79, 0.06);
}}
.pipeline-step.intercept {{
    border-left-color: {COLORS['risk_3']};
    background-color: rgba(217, 83, 79, 0.1);
}}

/* 横向流程图（时间轴概览） */
.pipeline-flow {{
    display: flex;
    flex-wrap: wrap;
    align-items: stretch;
    gap: 4px;
    margin: 16px 0 24px;
    padding: 14px 16px;
    background-color: {COLORS['cream']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}
.pipeline-node {{
    flex: 1 1 0;
    min-width: 90px;
    text-align: center;
    padding: 10px 6px;
    border-radius: 10px;
    border: 1px solid {COLORS['border']};
    background-color: {COLORS['off_white']};
    position: relative;
    transition: all 0.15s ease;
}}
.pipeline-node:hover {{
    border-color: {COLORS['border_strong']};
    transform: translateY(-1px);
}}
.pipeline-node .node-emoji {{
    font-size: 20px;
    line-height: 1;
    display: block;
    margin-bottom: 4px;
}}
.pipeline-node .node-step {{
    font-size: 10px;
    color: {COLORS['muted_gray']};
    letter-spacing: 0.4px;
    text-transform: uppercase;
}}
.pipeline-node .node-name {{
    font-size: 12px;
    font-weight: 600;
    color: {COLORS['charcoal']};
    margin-top: 2px;
    line-height: 1.3;
}}
.pipeline-node.llm {{
    border-color: #3b82f6;
    background-color: rgba(59, 130, 246, 0.06);
}}
.pipeline-node.llm .node-step {{
    color: #3b82f6;
}}
.pipeline-node.python {{
    border-color: {COLORS['risk_0']};
    background-color: rgba(123, 183, 110, 0.08);
}}
.pipeline-node.python .node-step {{
    color: #5b8b4d;
}}
.pipeline-node.crisis {{
    border-color: {COLORS['risk_3']};
    background-color: rgba(217, 83, 79, 0.08);
}}
.pipeline-node.crisis .node-step {{
    color: {COLORS['risk_3']};
}}
.pipeline-node.intercept {{
    border-color: {COLORS['risk_3']};
    background-color: rgba(217, 83, 79, 0.12);
}}
.pipeline-node.intercept .node-step {{
    color: {COLORS['risk_3']};
}}
.pipeline-node.active {{
    box-shadow: 0 0 0 2px {COLORS['charcoal']};
}}
.pipeline-arrow {{
    display: flex;
    align-items: center;
    color: {COLORS['muted_gray']};
    font-size: 14px;
    padding: 0 2px;
}}

/* 进度条 */
.anxin-progress {{
    width: 100%;
    height: 6px;
    background-color: rgba(28,28,28,0.06);
    border-radius: 9999px;
    overflow: hidden;
    margin: 6px 0;
}}
.anxin-progress > span {{
    display: block;
    height: 100%;
    border-radius: 9999px;
}}

/* 元信息小字 */
.meta {{
    color: {COLORS['muted_gray']};
    font-size: 13px;
}}

/* 分隔线 */
hr, .stHorizontalBlock hr {{
    border-color: {COLORS['border']};
}}

/* metrics 数字（家长仪表盘） */
[data-testid="stMetricValue"] {{
    color: {COLORS['charcoal']};
    font-weight: 600 !important;
    letter-spacing: -0.6px;
}}

/* 警告/提示框 */
.stAlert > div {{
    border-radius: 8px;
    border: 1px solid {COLORS['border']};
}}
</style>
"""


def apply_theme() -> None:
    """在页面顶部注入 Lovable 风格 CSS"""
    st.markdown(_CSS, unsafe_allow_html=True)


def risk_badge(risk_level: int) -> str:
    """返回风险等级徽章 HTML"""
    labels = {0: "0 安全", 1: "1 轻度", 2: "2 中度", 3: "3 高风险"}
    return (
        f'<span class="risk-badge risk-{risk_level}">{labels.get(risk_level, str(risk_level))}</span>'
    )


def card(html_content: str, extra_class: str = "") -> str:
    """生成卡片 HTML"""
    return f'<div class="anxin-card {extra_class}">{html_content}</div>'


# 7 步 Pipeline 节点元数据（用于时间轴流程图）
PIPELINE_NODES = [
    {"step": "0", "name": "记忆检索", "emoji": "🧠", "type": "python"},
    {"step": "1", "name": "关键词检测", "emoji": "🔍", "type": "python"},
    {"step": "2", "name": "风险分类", "emoji": "⚖️", "type": "llm"},
    {"step": "3", "name": "策略决策", "emoji": "🎯", "type": "python"},
    {"step": "4", "name": "Prompt 构建", "emoji": "📝", "type": "python"},
    {"step": "5", "name": "LLM 生成", "emoji": "✨", "type": "llm"},
    {"step": "6", "name": "批判审计", "emoji": "🛡️", "type": "llm"},
]


def pipeline_flow_html(active_steps: list[str] | None = None,
                       crisis_path: bool = False,
                       intercepted: bool = False) -> str:
    """生成横向时间轴流程图 HTML

    Args:
        active_steps: 实际执行过的 step 编号列表（高亮）
        crisis_path: 是否走了危机模板分支（step 4-5）
        intercepted: 是否触发输出拦截（step 6b）
    """
    active_steps = active_steps or []
    nodes_html = []
    for node in PIPELINE_NODES:
        type_class = node["type"]
        active_class = " active" if node["step"] in active_steps else ""
        nodes_html.append(
            f'<div class="pipeline-node {type_class}{active_class}">'
            f'<span class="node-emoji">{node["emoji"]}</span>'
            f'<span class="node-step">Step {node["step"]}</span>'
            f'<div class="node-name">{node["name"]}</div>'
            f'</div>'
        )
        nodes_html.append('<span class="pipeline-arrow">→</span>')

    # 危机分支或 6b 拦截分支
    if crisis_path:
        nodes_html.append(
            '<div class="pipeline-node crisis active">'
            '<span class="node-emoji">⚠️</span>'
            '<span class="node-step">Step 4-5</span>'
            '<div class="node-name">危机模板</div>'
            '</div>'
        )
    elif intercepted:
        nodes_html.append(
            '<div class="pipeline-node intercept active">'
            '<span class="node-emoji">🔴</span>'
            '<span class="node-step">Step 6b</span>'
            '<div class="node-name">输出拦截</div>'
            '</div>'
        )
    else:
        # 没有走特殊分支，最后一个箭头去掉
        nodes_html.pop()

    return f'<div class="pipeline-flow">{"".join(nodes_html)}</div>'


def progress_bar(percent: float, color: str = None) -> str:
    """生成进度条 HTML（用于测试覆盖率/合规完成度）"""
    if color is None:
        color = COLORS["charcoal"]
    return (
        f'<div class="anxin-progress">'
        f'<span style="width:{percent:.0f}%; background-color:{color};"></span>'
        f'</div>'
    )
