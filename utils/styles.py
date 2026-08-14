"""Lovable 风格主题样式（依据 docs/DESIGN-lovable.md）

将 Lovable 的奶油底色 / 暖色边框 / 圆角 / 内阴影等视觉特征，
通过注入 CSS 映射到 Streamlit 的元素上。

分三层：
1. COLORS 色板与基础常量
2. _CSS 全局样式（隐藏原生 chrome、排印体系、原生组件精修、自定义组件类）
3. HTML 辅助函数（pill / icon_card / alert_card / page_header 等，供各页面复用）
"""
from __future__ import annotations

import streamlit as st


# 核心色板（与 .streamlit/config.toml 一致）
COLORS = {
    "cream":         "#f7f4ed",  # 页面背景
    "cream_surface": "#f7f4ed",  # 卡片背景
    "charcoal":      "#1c1c1c",  # 主文字
    "off_white":     "#fcfbf8",  # 深色按钮文字 / 浮层表面
    "muted_gray":    "#5f5f5d",  # 次要文字
    "border":        "#eceae4",  # 暖色边框
    "border_strong": "rgba(28,28,28,0.4)",
    "tint":          "rgba(28,28,28,0.04)",  # 微染底色（hover / 用户气泡）
    "focus_shadow":  "rgba(0,0,0,0.1) 0px 4px 12px",
    "blue":          "#3b82f6",  # LLM 节点 / 信息强调
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

_FONT_STACK = (
    'ui-sans-serif, system-ui, -apple-system, "Segoe UI", "PingFang SC", '
    '"Hiragino Sans GB", "Microsoft YaHei", sans-serif'
)


_CSS = f"""
<style>
/* ===== 隐藏 Streamlit 原生 chrome（去模板感） ===== */
#MainMenu, footer, [data-testid="stFooter"] {{ visibility: hidden !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stToolbar"], [data-testid="stAppDeployButton"] {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent !important; }}

/* ===== 全局 ===== */
.stApp, [data-testid="stAppViewContainer"] {{
    background-color: {COLORS['cream']};
    color: {COLORS['charcoal']};
    font-family: {_FONT_STACK};
}}
.stApp button, .stApp input, .stApp textarea, .stApp select {{
    font-family: inherit;
}}

::selection {{ background: rgba(28,28,28,0.12); }}

/* 细滚动条 */
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
    background: rgba(28,28,28,0.15);
    border-radius: 9999px;
    border: 2px solid transparent;
    background-clip: content-box;
}}
::-webkit-scrollbar-thumb:hover {{
    background: rgba(28,28,28,0.3);
    border: 2px solid transparent;
    background-clip: content-box;
}}

/* 主容器留白 */
[data-testid="stMainBlockContainer"] {{
    padding-top: 2.5rem;
    padding-bottom: 4rem;
}}

/* ===== 排印体系 ===== */
h1, h2, h3, h4 {{
    color: {COLORS['charcoal']};
    font-weight: 600 !important;
    line-height: 1.15;
}}
h1 {{ letter-spacing: -1.2px; }}
h2 {{ letter-spacing: -0.9px; }}
h3 {{ letter-spacing: -0.6px; }}

p, li, span {{
    color: {COLORS['charcoal']};
}}
.stMarkdown p, .stMarkdown li {{
    line-height: 1.55;
}}

/* caption 统一为次级灰 */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {{
    color: {COLORS['muted_gray']} !important;
    font-size: 13px;
}}

/* 分隔线 */
hr {{
    border-color: {COLORS['border']};
    margin: 2rem 0;
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

/* 侧边栏 radio → 分段控件 / 选项 pill（隐藏圆形单选点） */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {{
    background-color: {COLORS['tint']};
    border-radius: 12px;
    padding: 4px;
    gap: 2px;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label {{
    border-radius: 9999px;
    padding: 6px 12px;
    margin: 0;
    transition: all 0.15s ease;
    cursor: pointer;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {{
    background-color: rgba(28,28,28,0.06);
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {{
    background-color: {COLORS['charcoal']};
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) p,
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) span,
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) div {{
    color: {COLORS['off_white']} !important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-of-type {{
    display: none;
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
    background-color: {COLORS['tint']};
    border-color: {COLORS['border_strong']};
    color: {COLORS['charcoal']};
}}
.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible {{
    box-shadow: {COLORS['focus_shadow']};
    outline: none;
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
    background-color: {COLORS['off_white']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    color: {COLORS['charcoal']};
}}
.stTextInput > div > input:focus,
.stTextArea > div > textarea:focus {{
    border-color: {COLORS['border_strong']};
    box-shadow: 0 0 0 2px {COLORS['blue_ring']};
}}

/* 下拉选择 */
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
    background-color: {COLORS['off_white']};
    border-color: {COLORS['border']};
    border-radius: 6px;
}}

/* stChatInput 容器 */
div[data-testid="stChatInput"] {{
    background-color: {COLORS['off_white']};
    border-color: {COLORS['border']} !important;
    border-radius: 12px !important;
}}
div[data-testid="stChatInput"]:focus-within {{
    border-color: {COLORS['border_strong']} !important;
    box-shadow: {COLORS['focus_shadow']};
}}

/* ===== Tabs ===== */
[data-testid="stTabs"] [role="tablist"] {{
    gap: 4px;
    border-bottom: 1px solid {COLORS['border']};
}}
[data-testid="stTabs"] button[role="tab"] {{
    color: {COLORS['muted_gray']};
    font-weight: 400;
    padding: 8px 14px;
    transition: all 0.15s ease;
}}
[data-testid="stTabs"] button[role="tab"]:hover {{
    color: {COLORS['charcoal']};
    background-color: {COLORS['tint']};
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    color: {COLORS['charcoal']};
    font-weight: 600;
}}
[data-testid="stTabs"] button[role="tab"] p,
[data-testid="stTabs"] button[role="tab"] span {{
    color: inherit !important;
}}

/* ===== Expander / Status / Dialog ===== */
[data-testid="stExpander"] {{
    border: 1px solid {COLORS['border']} !important;
    border-radius: 12px !important;
    background-color: {COLORS['off_white']};
    overflow: hidden;
    transition: border-color 0.15s ease;
}}
[data-testid="stExpander"]:hover {{
    border-color: {COLORS['border_strong']} !important;
}}
[data-testid="stExpander"] summary {{
    padding: 4px 8px;
}}
[data-testid="stStatusWidget"] {{
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    background-color: {COLORS['off_white']};
}}
[data-testid="stDialog"] > div {{
    border-radius: 16px;
    background-color: {COLORS['cream']};
}}

/* ===== Metric 卡片化 ===== */
[data-testid="stMetric"] {{
    background-color: {COLORS['off_white']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 14px 18px;
}}
[data-testid="stMetricLabel"] p {{
    color: {COLORS['muted_gray']} !important;
    font-size: 13px;
}}
[data-testid="stMetricValue"] {{
    color: {COLORS['charcoal']};
    font-weight: 600 !important;
    letter-spacing: -0.6px;
}}

/* ===== 警告/提示框 ===== */
.stAlert > div {{
    border-radius: 8px;
    border: 1px solid {COLORS['border']};
}}

/* ===== 聊天消息气泡：助手白底边框 / 用户浅染无边框 =====
   说明：emoji 头像无 role testid，页面在用户消息内注入 .chat-user-marker 标记，
   通过 :has() 区分用户气泡。 */
[data-testid="stChatMessage"] {{
    background-color: {COLORS['off_white']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 12px 16px;
}}
[data-testid="stChatMessage"]:has(.chat-user-marker) {{
    background-color: {COLORS['tint']};
    border-color: transparent;
}}

/* ===== 自定义组件类 ===== */

/* 卡片 */
.anxin-card {{
    background-color: {COLORS['cream']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
}}
/* 可交互卡片：hover 边框变深（遵循设计文档——不用浮起阴影） */
.anxin-card.hoverable {{
    transition: border-color 0.15s ease;
}}
.anxin-card.hoverable:hover {{
    border-color: {COLORS['border_strong']};
}}

/* 图标卡（emoji + 标题 + 描述） */
.icon-card-emoji {{
    font-size: 32px;
    line-height: 1;
}}
.icon-card-title {{
    font-weight: 600;
    font-size: 16px;
    margin: 10px 0 4px;
    color: {COLORS['charcoal']};
    letter-spacing: -0.2px;
}}
.icon-card-desc {{
    font-size: 13px;
    line-height: 1.5;
}}

/* 通用 pill 徽章 */
.anxin-pill {{
    display: inline-block;
    padding: 4px 12px;
    margin: 2px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 600;
}}

/* 页头 */
.page-header {{
    margin: 4px 0 12px;
}}
.page-header h2 {{
    margin: 0;
}}
.page-header .meta {{
    margin: 4px 0 0;
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

/* 小星球卡片 */
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

/* 星球生态全景条 */
.planet-ecosystem {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 12px 0 20px;
    padding: 16px 18px;
    background-color: {COLORS['cream']};
    border: 1px solid {COLORS['border']};
    border-radius: 14px;
}}
.planet-weather {{
    width: 100%;
    text-align: center;
    padding: 8px 0 4px;
    font-size: 14px;
}}
.planet-weather .weather-emoji {{
    font-size: 32px;
    line-height: 1;
    display: block;
    margin-bottom: 4px;
}}
.planet-weather .weather-text {{
    font-weight: 600;
    font-size: 15px;
    color: {COLORS['charcoal']};
}}
.planet-weather .weather-desc {{
    font-size: 12px;
    color: {COLORS['muted_gray']};
    margin-top: 2px;
}}
.ecosystem-item {{
    flex: 1 1 0;
    min-width: 120px;
    text-align: center;
    padding: 10px 8px;
    background-color: {COLORS['off_white']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
}}
.ecosystem-item .eco-icon {{
    font-size: 24px;
    line-height: 1;
    display: block;
    margin-bottom: 4px;
}}
.ecosystem-item .eco-label {{
    font-size: 11px;
    color: {COLORS['muted_gray']};
    margin-bottom: 2px;
}}
.ecosystem-item .eco-desc {{
    font-size: 13px;
    font-weight: 500;
    color: {COLORS['charcoal']};
    line-height: 1.4;
}}

/* 时间胶囊卡片 */
.capsule-card {{
    background-color: {COLORS['cream']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 14px 16px;
    transition: all 0.3s ease;
}}
.capsule-card.sealed {{
    background-color: rgba(28,28,28,0.02);
    border-style: dashed;
    opacity: 0.75;
}}
.capsule-card.sealed .capsule-preview {{
    filter: blur(4px);
    user-select: none;
    pointer-events: none;
}}
.capsule-card.revealed {{
    border-color: #c4a86c;
    background-color: rgba(196, 168, 108, 0.06);
    animation: capsuleCrack 0.6s ease-out;
}}
@keyframes capsuleCrack {{
    0% {{ transform: scale(0.95); opacity: 0.7; }}
    50% {{ transform: scale(1.03); }}
    100% {{ transform: scale(1); opacity: 1; }}
}}
.capsule-countdown {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 600;
    color: {COLORS['muted_gray']};
    background-color: rgba(28,28,28,0.06);
}}

/* 每日小挑战卡片 */
.daily-challenge-card {{
    background-color: rgba(196, 168, 108, 0.08);
    border: 1px solid rgba(196, 168, 108, 0.35);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 16px;
}}
.daily-challenge-card .challenge-icon {{
    font-size: 22px;
    line-height: 1;
    margin-right: 8px;
}}
.daily-challenge-card .challenge-text {{
    font-size: 14px;
    color: {COLORS['charcoal']};
    line-height: 1.5;
}}
.daily-challenge-card .challenge-hint {{
    font-size: 12px;
    color: {COLORS['muted_gray']};
    margin-top: 4px;
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
    border-left-color: {COLORS['blue']};
}}
.pipeline-step.python {{
    border-left-color: {COLORS['risk_0']};
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
    border-color: {COLORS['blue']};
    background-color: rgba(59, 130, 246, 0.06);
}}
.pipeline-node.llm .node-step {{
    color: {COLORS['blue']};
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
</style>
"""


def apply_theme() -> None:
    """在页面顶部注入 Lovable 风格 CSS"""
    st.markdown(_CSS, unsafe_allow_html=True)


def risk_color(risk_level: int) -> str:
    """返回风险等级对应的颜色值"""
    return COLORS.get(f"risk_{risk_level}", COLORS["muted_gray"])


def risk_badge(risk_level: int) -> str:
    """返回风险等级徽章 HTML"""
    labels = {0: "0 安全", 1: "1 轻度", 2: "2 中度", 3: "3 高风险"}
    return (
        f'<span class="risk-badge risk-{risk_level}">{labels.get(risk_level, str(risk_level))}</span>'
    )


def pill(text: str, fg: str, bg: str) -> str:
    """通用 pill 徽章 HTML"""
    return f'<span class="anxin-pill" style="color:{fg}; background-color:{bg};">{text}</span>'


def card(html_content: str, extra_class: str = "") -> str:
    """生成卡片 HTML"""
    return f'<div class="anxin-card {extra_class}">{html_content}</div>'


def icon_card(emoji: str, title: str, desc: str, padding: str = "16px", align: str = "left") -> str:
    """图标卡 HTML（emoji + 标题 + 描述），align 可设 "left" / "center\""""
    return (
        f'<div class="anxin-card" style="padding:{padding}; text-align:{align};">'
        f'<div class="icon-card-emoji">{emoji}</div>'
        f'<div class="icon-card-title">{title}</div>'
        f'<div class="meta icon-card-desc">{desc}</div>'
        f'</div>'
    )


def _tint(hex_color: str, alpha: float) -> str:
    """十六进制颜色转 rgba 淡染底色"""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def alert_card(html_content: str, color: str, tinted: bool = False) -> str:
    """左侧色条强调卡 HTML（告警、对比、提示复用）"""
    bg = f"background-color:{_tint(color, 0.08)};" if tinted else ""
    return (
        f'<div class="anxin-card" style="border-left:4px solid {color}; {bg}">'
        f'{html_content}</div>'
    )


def page_header(emoji: str, title: str, caption: str = "") -> str:
    """统一页头 HTML（emoji 标题 + 可选 meta 描述）"""
    caption_html = f'<p class="meta" style="margin:4px 0 0;">{caption}</p>' if caption else ""
    return (
        f'<div class="page-header">'
        f'<h2 style="margin:0;">{emoji} {title}</h2>{caption_html}'
        f'</div>'
    )


# 7 步 Pipeline 节点元数据（用于时间轴流程图）
PIPELINE_NODES = [
    {"step": "0", "name": "记忆检索", "emoji": "🧠", "type": "python"},
    {"step": "1", "name": "关键词检测", "emoji": "🔍", "type": "python"},
    {"step": "1b", "name": "Qwen3Guard", "emoji": "🛡️", "type": "python"},
    {"step": "2", "name": "语义理解", "emoji": "⚖️", "type": "llm"},
    {"step": "3", "name": "策略决策", "emoji": "🎯", "type": "python"},
    {"step": "4", "name": "Prompt构建", "emoji": "📝", "type": "python"},
    {"step": "5", "name": "LLM生成", "emoji": "✨", "type": "llm"},
    {"step": "6", "name": "批判审计", "emoji": "🔎", "type": "llm"},
    {"step": "6c", "name": "Qwen3Guard复核", "emoji": "🛡️", "type": "python"},
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
