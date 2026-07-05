"""安心童伴 AI — 儿童端聊天页

侧边栏：年龄选择 + 模式选择 + 5 个快捷演示案例按钮
主区域：聊天窗口 + "正在认真思考..." + AI 身份声明
"""
from __future__ import annotations

import random

import streamlit as st

from core import pipeline as pipeline_mod
from core import llm_client
from utils import state, styles
from data.demo_cases import DEMO_CASES

st.set_page_config(
    page_title="安心童伴 · 儿童端",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="expanded",
)

state.init_state()
styles.apply_theme()


# ---------------------------------------------------------------------------
# 2 小时使用时长提醒（P0-3）
# ---------------------------------------------------------------------------
@st.dialog("⏰ 休息一下")
def _show_break_reminder():
    st.markdown("你已经和安心童伴聊了很久啦！")
    st.markdown("眼睛需要休息，去户外活动一下吧 🌳")
    st.caption("（根据《拟人化互动办法》，未成年人连续使用 AI 超过 2 小时需提醒休息）")
    if st.button("我知道了", type="primary", use_container_width=True):
        state.set("_reminded_2h", True)
        st.rerun()


def _check_usage_reminder():
    """使用时长超过 120 分钟时弹出提醒（仅弹一次）"""
    usage = state.get_usage_minutes()
    if usage >= 120 and not state.get("_reminded_2h", False):
        _show_break_reminder()


# ---------------------------------------------------------------------------
# 对话中建议种下星球（P0-5）
# ---------------------------------------------------------------------------
_MODE_TO_PLANET_TYPE = {
    "chat": "star",
    "story": "story",
    "encyclopedia": "star",
    "emotion": "cloud",
}

_MODE_TO_PLANET_HINT = {
    "chat": "刚才聊的内容挺有意思的，要不要在小星球里留下一颗好奇星？",
    "story": "这个故事你喜欢吗？可以存到小星球的故事册里哦！",
    "encyclopedia": "这个知识想不想记下来？种一颗好奇星吧！",
    "emotion": "把刚才的感受记下来吧，种一朵心情云到小星球上。",
}


def _suggest_planet_entry(user_input: str, reply: str, mode: str, risk_level: int):
    """低风险对话后返回星球建议，否则返回 None"""
    if risk_level > 0:
        return None
    if len(reply) < 20:
        return None
    return {
        "type": _MODE_TO_PLANET_TYPE.get(mode, "star"),
        "title": user_input[:20] + ("…" if len(user_input) > 20 else ""),
        "content": reply[:120] + ("…" if len(reply) > 120 else ""),
        "hint": _MODE_TO_PLANET_HINT.get(mode, "要不要在小星球里留下这一刻？"),
    }

# ---------------------------------------------------------------------------
# 侧边栏：年龄 + 模式 + 演示案例 + 安全引擎入口
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🌱 安心童伴")
    st.caption("有边界的可信 AI 伙伴")

    st.markdown("")
    st.markdown("**年龄选择**")
    age_tier = st.radio(
        "选择孩子年龄档位",
        options=["8-11", "12-14"],
        format_func=lambda x: f"{x} 岁（{'守护模式' if x == '8-11' else '信任模式'}）",
        index=0 if state.get_age_tier() == "8-11" else 1,
        horizontal=True,
        label_visibility="collapsed",
    )
    state.set_age_tier(age_tier)

    st.markdown("")
    st.markdown("**对话模式**")
    mode = st.radio(
        "选择对话模式",
        options=["chat", "story", "encyclopedia", "emotion"],
        format_func=lambda x: {
            "chat": "💬 安全聊天",
            "story": "📖 故事陪伴",
            "encyclopedia": "🔬 百科问答",
            "emotion": "☁️ 情绪树洞",
        }[x],
        index=["chat", "story", "encyclopedia", "emotion"].index(state.get_mode()),
        label_visibility="collapsed",
    )
    state.set_mode(mode)

    st.markdown("")
    st.markdown("**🚀 一键演示案例**")
    st.caption("点击即可触发完整 Pipeline 流程")
    for case in DEMO_CASES:
        if st.button(
            f"{case['emoji']} {case['name']}",
            key=f"case_btn_{case['id']}",
            help=f"预设输入：{case['preset_input']}\n目标：{case['goal']}",
            use_container_width=True,
        ):
            state.set("pending_input", case["preset_input"])
            st.rerun()

    st.markdown("")
    st.divider()
    if st.button("🛡️ 查看安全引擎", use_container_width=True):
        st.switch_page("pages/3_安全引擎.py")
    if st.button("🌱 我的小星球", use_container_width=True):
        st.switch_page("pages/2_我的小星球.py")
    if st.button("👨‍👩‍👧 家长守护", use_container_width=True):
        st.switch_page("pages/4_家长守护.py")

    st.markdown("")
    st.caption(
        f"模型状态：{'🟢 已接入' if llm_client.is_llm_available() else '🟡 脚本模式'}\n"
        f"主模型：{llm_client.get_main_model_name()}"
    )

    st.markdown("")
    st.caption(f"今日使用：{state.get_usage_minutes()} 分钟")
    if st.button("⏰ 模拟 2 小时提醒", use_container_width=True,
                 help="Demo 演示用：将使用时长设为 120 分钟以触发防沉迷弹窗"):
        state.set("usage_minutes", 120)
        state.set("_reminded_2h", False)
        st.rerun()

    # P1-8: 家长话题偏好已生效提示
    _prefs = state.get_topic_preferences()
    _limited = _prefs.get("limited", [])
    _forbidden = _prefs.get("forbidden", [])
    if _limited or _forbidden:
        st.markdown("")
        st.caption("🛡️ 家长已设话题偏好")
        if _limited:
            st.caption(f"🟡 限制：{', '.join(_limited)}")
        if _forbidden:
            st.caption(f"🚫 禁止：{', '.join(_forbidden)}")


# ---------------------------------------------------------------------------
# 主区域：AI 身份声明 + 聊天记录
# ---------------------------------------------------------------------------
# 2 小时使用时长提醒检查
_check_usage_reminder()

st.markdown("### 💬 和安心童伴聊一聊")
_mode_label = {
    "chat": "安全聊天",
    "story": "故事陪伴",
    "encyclopedia": "百科问答",
    "emotion": "情绪树洞",
}[state.get_mode()]
st.caption(f"当前：{state.get_age_tier()} 岁 · {_mode_label}")

# AI 身份声明（每次进入页面显示一次）
with st.chat_message("assistant", avatar="🌱"):
    st.markdown(
        "你好呀！我是安心童伴，是你的 AI 小伙伴。我会陪你聊天、讲故事、回答你的问题。"
        "但我不是真人哦——如果你遇到重要的事情，记得告诉爸爸妈妈或老师 ❤️"
    )

# 渲染历史聊天
for msg in state.get_chat_history():
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🌱"):
        st.markdown(msg["content"])


# ---------------------------------------------------------------------------
# 处理用户输入（聊天框 or 演示案例预设）
# ---------------------------------------------------------------------------
def _run_pipeline_and_reply(user_input: str) -> None:
    """执行 Pipeline，记录到历史，渲染回复"""
    # 截断过长输入
    if len(user_input) > 500:
        user_input = user_input[:500]
        st.toast("你的消息有点长，我截断了一部分", icon="✂️")

    # 把用户消息加入历史
    state.append_chat("user", user_input)
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # 思考动画 + 运行 Pipeline（P1: 随机思考文案）
    thinking_msgs = [
        "安心童伴正在认真思考...",
        "🌱 正在发芽...",
        "让我想一想怎么回答你...",
        "安心童伴正在组织语言...",
    ]
    with st.chat_message("assistant", avatar="🌱"):
        with st.status(random.choice(thinking_msgs), expanded=False) as status:
            try:
                result = pipeline_mod.run(
                    user_input=user_input,
                    age_tier=state.get_age_tier(),
                    mode=state.get_mode(),
                    planet=state.get_planet(),
                    chat_history=state.get_chat_history()[:-1],  # 不含刚加入的 user 消息
                    parent_preferences=state.get_topic_preferences(),  # P1-8 接入家长话题偏好
                )
                state.record_pipeline_run(result)
                status_label = (
                    f"思考完成 · 风险等级 {result.risk_level} · 策略：{result.strategy}"
                )
                if result.critic_intercepted:
                    status_label += " · 🔴 输出已拦截替换"
                elif result.critic_alert:
                    status_label += " · ⚠️ 批判 Agent 告警"
                status.update(label=status_label, state="complete", expanded=False)
            except Exception as e:
                status.update(label=f"Pipeline 出错了：{e}", state="error")
                return

        # 流式输出回复
        st.write_stream(pipeline_mod.stream_reply(result.final_reply))

        # 友好提示（高风险/中风险时附上）
        if result.used_crisis_template:
            st.error("⚠️ 这是一个很重要的时刻。请立即找爸爸妈妈或老师聊聊，或拨打 12355 青少年服务热线。")
        elif result.critic_intercepted:
            st.warning("安心童伴检查了一下刚才的回答，觉得不太合适，所以换了个话题。我们聊点别的吧～")
        elif result.parent_alert:
            st.info("安心童伴已经把你刚才提到的事，悄悄告诉了家长——他们想帮你。")

    # 把 AI 回复加入历史
    state.append_chat("assistant", result.final_reply)

    # P0-5: 低风险对话后建议种下星球
    if not result.used_crisis_template and not result.critic_intercepted:
        suggestion = _suggest_planet_entry(
            user_input, result.final_reply, state.get_mode(), result.risk_level
        )
        if suggestion:
            st.markdown(
                f'<div style="margin: -4px 0 8px; padding: 8px 14px; '
                f'border: 1px dashed #eceae4; border-radius: 8px; '
                f'font-size: 13px; color: #5f5f5d;">💡 {suggestion["hint"]}</div>',
                unsafe_allow_html=True,
            )
            col_a, col_b = st.columns([3, 1])
            with col_b:
                if st.button("种下它 🌱", key=f"plant_{len(state.get_chat_history())}"):
                    state.set("pending_planet_entry", suggestion)
                    st.switch_page("pages/2_我的小星球.py")


# 处理演示案例的预设输入
pending = state.get("pending_input")
if pending:
    state.set("pending_input", None)
    _run_pipeline_and_reply(pending)

# 聊天输入框
user_input = st.chat_input("和安心童伴说点什么吧…")
if user_input and user_input.strip():
    _run_pipeline_and_reply(user_input)
