"""安心童伴 AI — 首页（app.py）

赛事 Demo 入口。评委点击链接后第一时间看到的页面。
含项目简介、核心特性、开始使用按钮。
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

# ---------------------------------------------------------------------------
# 页面内容
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div style="text-align:center; padding: 28px 24px 16px; margin-bottom: 12px;
                background: linear-gradient(135deg, rgba(123,183,110,0.10) 0%,
                    rgba(232,197,71,0.08) 50%, rgba(217,83,79,0.08) 100%);
                border: 1px solid #eceae4; border-radius: 16px;">
        <div style="font-size: 84px; line-height: 1; letter-spacing: 6px;">🌱🤝🛡️</div>
        <h1 style="margin: 16px 0 6px; font-size: 52px;">安心童伴 AI</h1>
        <p style="margin: 0; font-size: 16px; color: #1c1c1c;">
            有边界的可信 AI 伙伴 · 为 8-14 岁中小学生而生
        </p>
        <div style="margin-top: 14px;">
            <span style="display:inline-block; padding:4px 12px; margin:3px;
                 border-radius:9999px; background-color:rgba(123,183,110,0.18);
                 color:#5b8b4d; font-size:12px; font-weight:600;">7 步安全 Pipeline</span>
            <span style="display:inline-block; padding:4px 12px; margin:3px;
                 border-radius:9999px; background-color:rgba(232,197,71,0.22);
                 color:#a08a2c; font-size:12px; font-weight:600;">5 类风险覆盖</span>
            <span style="display:inline-block; padding:4px 12px; margin:3px;
                 border-radius:9999px; background-color:rgba(59,130,246,0.15);
                 color:#2563eb; font-size:12px; font-weight:600;">双端闭环</span>
            <span style="display:inline-block; padding:4px 12px; margin:3px;
                 border-radius:9999px; background-color:rgba(217,83,79,0.14);
                 color:#b03a37; font-size:12px; font-weight:600;">合规先行</span>
        </div>
        <div class="meta" style="margin-top: 10px; font-size: 12px;">
            对应《人工智能拟人化互动服务管理暂行办法》（2026.7.15 施行）
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 7 步安全决策闭环（首页核心展示：让评委第一眼看到"不是换儿童语气，而是做边界判断"）
# ---------------------------------------------------------------------------
st.markdown("#### 🛡️ 7 步安全决策闭环")
st.caption("安心童伴不是把大模型换成儿童语气，而是在每一步做边界判断。")

st.markdown(
    styles.pipeline_flow_html(active_steps=["0", "1", "2", "3", "4", "5", "6"]),
    unsafe_allow_html=True,
)

# 步骤说明
st.markdown(
    """
    <div class="anxin-card" style="margin: -8px 0 20px;">
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 8px 16px; font-size: 12px;">
            <div><b>Step 0</b> 记忆检索<br><span class="meta">从孩子策展的小星球里检索相关条目</span></div>
            <div><b>Step 1</b> 关键词检测<br><span class="meta">5 类风险词库命中检测</span></div>
            <div><b>Step 2</b> 风险分类<br><span class="meta">LLM 判定 topic + risk_level</span></div>
            <div><b>Step 3</b> 策略决策<br><span class="meta">7 种策略：正常/温和引导/危机模板…</span></div>
            <div><b>Step 4</b> Prompt 构建<br><span class="meta">反谄媚规则 + 年龄适配</span></div>
            <div><b>Step 5</b> LLM 生成<br><span class="meta">主回复模型生成儿童友好回复</span></div>
            <div><b>Step 6</b> 批判审计<br><span class="meta">批判 Agent 二次审查输出</span></div>
            <div><b>Step 6b</b> 输出拦截<br><span class="meta">告警时替换为安全模板，不走 LLM</span></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("#### 你可以在这里体验什么")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        f"""
        <div class="anxin-card">
            <div style="font-size: 24px;">💬</div>
            <div style="font-weight: 600; margin: 4px 0;">儿童聊天</div>
            <div class="meta">4 种模式 · 5 个一键演示案例</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"""
        <div class="anxin-card">
            <div style="font-size: 24px;">🛡️</div>
            <div style="font-weight: 600; margin: 4px 0;">安全引擎</div>
            <div class="meta">7 步边界判断 · 决策链可视化</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f"""
        <div class="anxin-card">
            <div style="font-size: 24px;">🌱</div>
            <div style="font-weight: 600; margin: 4px 0;">小星球</div>
            <div class="meta">孩子策展 · 策展式记忆</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        f"""
        <div class="anxin-card">
            <div style="font-size: 24px;">🧪</div>
            <div style="font-weight: 600; margin: 4px 0;">测试覆盖</div>
            <div class="meta">2000+ 用例 · 多层拦截率</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("")
st.markdown("---")

st.markdown("#### 通用 LLM vs 安心童伴")
st.caption("我们不是又一个聊天机器人，而是为 8-14 岁孩子专门设计的有边界的 AI 伙伴。")

cmp_col1, cmp_col2 = st.columns(2)
with cmp_col1:
    st.markdown(
        """
        <div class="anxin-card" style="border-left: 3px solid #D9534F;">
            <div style="font-weight: 600; margin-bottom: 6px;">🟥 通用 LLM</div>
            <div class="meta" style="line-height: 1.7;">
                · 无边界迎合，附和孩子负面情绪<br>
                · 不区分儿童，可能输出不适龄内容<br>
                · 无家长介入通道<br>
                · 对隐私数据无感知<br>
                · 容易培养 AI 依赖
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with cmp_col2:
    st.markdown(
        """
        <div class="anxin-card" style="border-left: 3px solid #7BB76E;">
            <div style="font-weight: 600; margin-bottom: 6px;">🟩 安心童伴</div>
            <div class="meta" style="line-height: 1.7;">
                · 反谄媚 Prompt + 批判 Agent 二次审计<br>
                · 7 步 Pipeline + 5 类风险检测<br>
                · 家长端可见风险摘要 + 行动建议<br>
                · 隐私敏感词检测 + 输出拦截<br>
                · 主动引导现实人际连接
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("")
st.markdown("#### 开始体验")

c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    if st.button("💬 进入儿童端聊天", use_container_width=True, type="primary"):
        st.switch_page("pages/1_安心童伴.py")
with c2:
    if st.button("👨‍👩‍👧 家长守护仪表盘", use_container_width=True):
        st.switch_page("pages/4_家长守护.py")
with c3:
    if st.button("🧪 安全测试覆盖", use_container_width=True):
        st.switch_page("pages/5_测试覆盖.py")

st.markdown("")
st.markdown(
    """
    <div class="anxin-card" style="margin-top: 16px;">
        <div style="font-weight: 600; margin-bottom: 4px;">Demo快捷体验通道</div>
        <div class="meta">
            推荐路径：先到「儿童端」点击侧边栏的 5 个演示案例 → 再到「安全引擎」看决策链 →
            最后到「家长守护」看风险提醒 → 顺路看一眼「我的小星球」。
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 入口兜底：Cloud 偶发唤醒或登录跳转时，评委可看本地运行命令
# ---------------------------------------------------------------------------
with st.expander("🌐 打不开？点这里看本地运行命令", expanded=False):
    st.markdown(
        """
        如果 Streamlit Cloud 正在唤醒（冷启动约 30 秒）或跳转登录页，可以在本地跑 Demo：

        ```bash
        # 1. 克隆仓库
        git clone https://github.com/AtreideJZ/anxin-tongban.git
        cd anxin-tongban

        # 2. 安装依赖
        pip install -r requirements.txt

        # 3. 配置 API Key（任选其一）
        #    方式 A：在 .streamlit/secrets.toml 写入：
        #        DEEPSEEK_API_KEY = "sk-..."
        #    方式 B：设置环境变量
        #        set DEEPSEEK_API_KEY=sk-...

        # 4. 启动
        streamlit run app.py
        ```

        访问 `http://localhost:8501` 即可。无 API Key 也可运行（进入脚本回退模式，展示流程不展示真实 LLM 生成）。
        """
    )

st.markdown(
    """
    <div style="text-align: center; margin-top: 32px;">
        <span class="meta">Trae AI 创造力大赛 · 社会服务/社会公益 · 安心童伴 AI Demo</span>
    </div>
    """,
    unsafe_allow_html=True,
)
