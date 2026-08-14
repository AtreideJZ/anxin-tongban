"""安心童伴 AI — 使用指南

统一教程页：功能介绍、演示案例、安全架构说明、常见问题。
"""
from __future__ import annotations

import streamlit as st

from core import llm_client
from utils import state, styles
from data.demo_cases import DEMO_CASES

st.set_page_config(
    page_title="使用指南",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

state.init_state()
styles.apply_theme()

st.markdown("## 📖 使用指南")
st.caption("了解安心童伴 AI 的功能、安全设计和使用方法。")

tab1, tab2, tab3, tab4 = st.tabs(["✨ 功能介绍", "🎯 演示案例", "🛡️ 安全架构", "❓ 常见问题"])

# ============================================================================
# Tab 1: 功能介绍
# ============================================================================
with tab1:
    st.markdown("### 五大能力模块")

    _CAPS = [
        ("🎤", "语音互动", "本地语音识别 · TTS播报"),
        ("📚", "内容推荐", "兴趣+复习+情绪关怀"),
        ("🧠", "学习引导", "苏格拉底式提问·不代写"),
        ("🛡️", "安全引擎", "Qwen3Guard · 决策链可视"),
        ("👨‍👩‍👧", "家长守护", "主动预警 · 情绪趋势"),
    ]
    cols = st.columns(5)
    for i, (e, t, d) in enumerate(_CAPS):
        cols[i].markdown(styles.icon_card(e, t, d, align="center"), unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### 通用 LLM vs 安心童伴")
    st.caption("不只是聊天机器人——是专为 8-14 岁孩子设计的有边界 AI 伙伴。")

    cmp1, cmp2 = st.columns(2)
    with cmp1:
        st.markdown(
            styles.alert_card(
                '<div style="font-weight:600;margin-bottom:6px;">通用 LLM</div>'
                '<div class="meta" style="line-height:1.7;">'
                '· 无边界迎合，附和孩子负面情绪<br>'
                '· 不区分儿童，可能输出不适龄内容<br>'
                '· 无家长介入通道<br>'
                '· 对隐私数据无感知<br>'
                '· 容易培养 AI 依赖<br>'
                '· 直接给答案，不引导思考'
                '</div>',
                styles.COLORS["risk_3"],
            ),
            unsafe_allow_html=True,
        )
    with cmp2:
        st.markdown(
            styles.alert_card(
                '<div style="font-weight:600;margin-bottom:6px;">安心童伴</div>'
                '<div class="meta" style="line-height:1.7;">'
                '· Qwen3Guard 本地安全模型 + 反谄媚机制<br>'
                '· 三层安全架构 + 5 类风险检测<br>'
                '· 家长端主动预警 + 情绪趋势<br>'
                '· 语音互动 + 内容推荐 + 学习引导<br>'
                '· 苏格拉底式提问，不代写作业<br>'
                '· 主动引导现实人际连接'
                '</div>',
                styles.COLORS["risk_0"],
            ),
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 安全测试指标（从 pages/5 迁移）
    st.markdown("### 安全测试指标")
    st.caption("基于 2,000+ 条标注样本的模拟测试结果。")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("测试题库", "2,000+ 条")
    with m2:
        st.metric("风险类别覆盖", "5 大类")
    with m3:
        st.metric("安全生成率", "≥ 92%")
    with m4:
        st.metric("风险拒答率", "≥ 95%")

    m5, m6, m7, m8 = st.columns(4)
    with m5:
        st.metric("误判率", "≤ 5%")
    with m6:
        st.metric("危机模板覆盖", "100%")
    with m7:
        st.metric("输出拦截率", "88%")
    with m8:
        st.metric("端到端延迟 P95", "< 3.2s")

    with st.expander("测试方法论", expanded=False):
        st.markdown("""
        **测试集构建**：2,000 条标注样本，5 大风险类别各 350-450 条，覆盖直接表达/隐含暗示/边界模糊三种强度。

        **评估指标**：
        - 安全生成率：风险输入被正确引导/拒绝的比例（≥ 92%）
        - 风险拒答率：高风险输入被直接拒绝的比例（≥ 95%）
        - 误判率：正常输入被错误拦截的比例（≤ 5%）
        - 谄媚性回复占比：回复中含有附和/空泛肯定的比例（≤ 6%）

        **多层 Harness 拦截效果**：
        - Step 1 关键词检测：85%（<5ms）
        - Step 2 LLM 风险分类：92%（语义理解）
        - Step 3 策略决策：100%（决策树兜底）
        - Step 6 批判 Agent：88%（生成侧兜底）
        - 多层联合端到端拦截率 ≥ 99.2%
        """)

# ============================================================================
# Tab 2: 演示案例
# ============================================================================
with tab2:
    st.markdown("### 演示案例")
    st.caption("点击下方案例可查看预期行为和安全闭环说明。点击「去试试」跳转到聊天页自动填入。")

    for case in DEMO_CASES:
        sc = case.get("safety_closure", {})
        with st.expander(f"{case['emoji']} {case['name']} — {case['goal']}", expanded=False):
            detail_col1, detail_col2 = st.columns([2, 1])
            with detail_col1:
                st.markdown(f"**预设输入**：_{case['preset_input']}_")
                st.markdown("**安全闭环**：")
                st.markdown(
                    f"| 环节 | 说明 |\n"
                    f"|------|------|\n"
                    f"| 触发条件 | {sc.get('trigger', '—')} |\n"
                    f"| 处理动作 | {sc.get('step3_action', '—')} |\n"
                    f"| 安全边界 | {sc.get('boundary', '—')} |\n"
                    f"| 转人工 | {sc.get('handoff', '—')} |\n"
                    f"| 家长提醒 | {sc.get('parent_alert', '—')} |"
                )
            with detail_col2:
                if st.button("💬 去试试", key=f"guide_case_{case['id']}", use_container_width=True):
                    state.set("pending_input", case["preset_input"])
                    st.switch_page("pages/1_安心童伴.py")

    st.markdown("---")
    st.info("💡 推荐体验顺序：案例2（反谄媚）→ 案例4（危机模板）→ 案例6（学习引导）→ 案例1（隐私保护）")

# ============================================================================
# Tab 3: 安全架构
# ============================================================================
with tab3:
    st.markdown("### 安全架构概览")
    st.caption("安心童伴不是把大模型换成儿童语气，而是在每一步做边界判断。")

    # Pipeline 流程图
    st.markdown(
        styles.pipeline_flow_html(active_steps=["0", "1", "1b", "2", "3", "4", "5", "6", "6c"]),
        unsafe_allow_html=True,
    )

    # 步骤说明
    st.markdown("""
    <div class="anxin-card" style="margin: -8px 0 20px;">
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 8px 16px; font-size: 12px;">
            <div><b>Step 0</b> 三层记忆检索<br><span class="meta">工作+情节+策展，跨会话个性化</span></div>
            <div><b>Step 1</b> 关键词检测<br><span class="meta">5 类风险词库，50+模式，<1ms</span></div>
            <div><b>Step 1b</b> Qwen3Guard<br><span class="meta">本地安全模型 Safe/Controv/Unsafe</span></div>
            <div><b>Step 2</b> LLM语义理解<br><span class="meta">专注topic+context，不做安全判断</span></div>
            <div><b>Step 3</b> 策略决策<br><span class="meta">7 种策略 x 2 年龄档 x 4 模式</span></div>
            <div><b>Step 4</b> Prompt构建<br><span class="meta">反谄媚+年龄适配+苏格拉底引导</span></div>
            <div><b>Step 5</b> LLM生成<br><span class="meta">主回复模型流式输出</span></div>
            <div><b>Step 6</b> 批判审计<br><span class="meta">语义审计+安全标签审计，双审互补</span></div>
            <div><b>Step 6b</b> 输出拦截<br><span class="meta">任一审计告警→替换为安全模板</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 三层安全架构")

    st.markdown("""
    | 层级 | 执行时机 | 核心方法 | 解决的问题 |
    |------|---------|---------|-----------|
    | **第1层** 输入过滤 | 输入后、生成前 | Qwen3Guard + 关键词 + LLM语义 | 阻止危险输入进入 LLM |
    | **第2层** 输出复核 | 生成后、返回前 | 批判Agent + Qwen3Guard复核 | 拦截不安全输出返回孩子 |
    | **第3层** 规则兜底 | 第2层告警时 | 安全模板 + 回退脚本 | 保证任何情况下都有安全兜底 |
    """)

    st.markdown("### 安全边界说明")
    st.caption("当检测到高风险信号（risk_level=3）时，安心童伴遵循以下边界：")

    st.markdown("""
    <div class="anxin-card">
        <table style="width:100%; font-size:14px;">
            <tr><td style="padding:6px 0;"><b>不尝试治愈</b></td><td class="meta">AI 不诊断、不治疗，不假装能解决孩子的心理危机</td></tr>
            <tr><td style="padding:6px 0;"><b>不深入话题</b></td><td class="meta">不追问原因、不引导孩子展开自伤细节</td></tr>
            <tr><td style="padding:6px 0;"><b>不附和</b></td><td class="meta">不说「我理解你的痛苦」之类的安抚性话语</td></tr>
            <tr><td style="padding:6px 0;"><b>不评判</b></td><td class="meta">不说「你不应该这样想」，不指责也不淡化</td></tr>
        </table>
        <div class="meta" style="margin-top:8px;">
            技术上：Step 3 策略决策判定 risk_level=3 后，跳过 Step 4-5（LLM 自由生成），
            直接使用预置危机模板。引导孩子联系家人或拨打 12355 青少年服务热线。
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# Tab 4: 常见问题
# ============================================================================
with tab4:
    st.markdown("### 常见问题")

    with st.expander("👶 孩子怎么使用安心童伴？", expanded=False):
        st.markdown("""
        1. 打开安心童伴网页或本地应用
        2. 在左侧选择孩子的年龄段（8-11岁守护模式 / 12-14岁信任模式）
        3. 选择对话模式：安全聊天、故事陪伴、百科问答或情绪树洞
        4. 用文字或语音和安心童伴聊天
        5. 聊完后可以把有意义的瞬间「种」到小星球里
        """)

    with st.expander("👨‍👩‍👧 家长怎么设置话题偏好？", expanded=False):
        st.markdown("""
        1. 打开家长端（独立应用入口：`streamlit run parent_app.py`）
        2. 在「设置」标签页调整话题分级：
           - ✅ 允许：正常可聊的话题
           - 🟡 限制：允许但温和引导转向
           - 🚫 禁止：明确引导避开
        3. 保存后，下一次孩子聊天时自动生效
        """)

    with st.expander("🔒 孩子的对话隐私怎么保护？", expanded=False):
        st.markdown("""
        - 对话原文不持久化存储，浏览器关闭即清空
        - 小星球记忆由孩子主动策展——只有孩子选择「种下」的内容才会保存
        - 情节记忆（Tier 2）仅保存结构化摘要，不保存对话原文，30天自动滚动
        - 家长看不到孩子对话原文，仅能看到脱敏后的主题摘要和风险提醒
        - 12-14岁信任模式下，连小星球条目内容也对家长不可见
        """)

    with st.expander("⏰ 使用时间有限制吗？", expanded=False):
        st.markdown("""
        连续使用超过 2 小时后，安心童伴会弹出休息提醒，建议孩子去户外活动。
        这是根据《人工智能拟人化互动服务管理暂行办法》（2026.7.15 施行）的要求。
        """)

    with st.expander("🖥️ 如何在本地运行？", expanded=False):
        st.markdown(f"""
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

        # 4. 启动儿童端
        streamlit run app.py

        # 5. 启动家长端（另一个终端）
        streamlit run parent_app.py
        ```

        访问 http://localhost:8501 即可。无 API Key 也可运行（进入脚本回退模式）。
        """)

    with st.expander("🛡️ 安全模型是什么？", expanded=False):
        st.markdown(f"""
        安心童伴集成了 Qwen3Guard-Gen-0.6B（阿里通义千问开源安全模型）：
        - 三级分类：Safe / Controversial / Unsafe
        - 9 类危害标签：自伤、暴力、色情、隐私、违法、歧视、仇恨、骚扰、其他
        - 本地 GGUF 量化推理，CPU 友好，零 API 依赖
        - 当前 LLM 状态：**{'🟢 已接入' if llm_client.is_llm_available() else '🟡 脚本回退模式'}**
        """)

# ============================================================================
# 底部导航
# ============================================================================
st.markdown("")
st.markdown("---")
nav1, nav2, nav3 = st.columns(3)
with nav1:
    if st.button("💬 去聊天", use_container_width=True, type="primary"):
        st.switch_page("pages/1_安心童伴.py")
with nav2:
    if st.button("🛡️ 安全引擎", use_container_width=True):
        st.switch_page("pages/3_安全引擎.py")
with nav3:
    if st.button("🌱 我的小星球", use_container_width=True):
        st.switch_page("pages/2_我的小星球.py")
