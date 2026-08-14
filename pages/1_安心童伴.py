"""安心童伴 AI — 儿童端聊天页

侧边栏：年龄选择 + 模式选择 + 语音状态
主区域：聊天窗口 + 语音/文字输入 + 推荐卡片
"""
from __future__ import annotations

import streamlit as st

from core import pipeline as pipeline_mod
from core import llm_client, voice, recommendation_engine as rec_engine, episodic_memory as em, daily_challenges
from utils import state, styles

st.set_page_config(
    page_title="安心童伴 · 儿童端",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="expanded",
)

state.init_state()
styles.apply_theme()

C = styles.COLORS

# 用户气泡标记（emoji 头像无 role testid，用 :has() 区分用户/助手气泡样式）
_USER_MARKER = '<span class="chat-user-marker" hidden></span>'

_MODE_META = {
    "chat": ("💬", "安全聊天"),
    "story": ("📖", "故事陪伴"),
    "encyclopedia": ("🔬", "百科问答"),
    "emotion": ("☁️", "情绪树洞"),
}


# ---------------------------------------------------------------------------
# 2 小时使用时长提醒
# ---------------------------------------------------------------------------
@st.dialog("⏰ 休息一下")
def _show_break_reminder():
    st.markdown("你已经和安心童伴聊了很久啦！")
    st.markdown("眼睛需要休息，去户外活动一下吧 🌳")
    if st.button("我知道了", type="primary", use_container_width=True):
        state.set("_reminded_2h", True)
        st.rerun()


def _check_usage_reminder():
    usage = state.get_usage_minutes()
    if usage >= 120 and not state.get("_reminded_2h", False):
        _show_break_reminder()


# ---------------------------------------------------------------------------
# 对话中建议种下星球
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
# 侧边栏：年龄 + 模式 + 语音状态 + 导航
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🌱 安心童伴")

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

    st.markdown("**对话模式**")
    mode = st.radio(
        "选择对话模式",
        options=["chat", "story", "encyclopedia", "emotion"],
        format_func=lambda x: f"{_MODE_META[x][0]} {_MODE_META[x][1]}",
        index=["chat", "story", "encyclopedia", "emotion"].index(state.get_mode()),
        label_visibility="collapsed",
    )
    state.set_mode(mode)

    st.markdown("")
    st.caption(voice.get_voice_input_status_text())

    st.markdown("")
    st.divider()
    if st.button("🌱 我的小星球", use_container_width=True):
        st.switch_page("pages/2_我的小星球.py")
    if st.button("📖 使用指南", use_container_width=True):
        st.switch_page("pages/0_使用指南.py")

    st.markdown("")
    st.caption(f"今日使用：{state.get_usage_minutes()} 分钟")

    # 家长话题偏好提示
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
# 主区域：聊天
# ---------------------------------------------------------------------------
_check_usage_reminder()

_mode_emoji, _mode_label = _MODE_META[state.get_mode()]
_status_pills = (
    styles.pill(
        f"🌱 {state.get_age_tier()} 岁 · {'守护模式' if state.get_age_tier() == '8-11' else '信任模式'}",
        C["charcoal"], "rgba(28,28,28,0.06)",
    )
    + styles.pill(f"{_mode_emoji} {_mode_label}", C["charcoal"], "rgba(28,28,28,0.06)")
)
st.markdown(styles.page_header("💬", "和安心童伴聊一聊"), unsafe_allow_html=True)
st.markdown(f'<div style="margin:-2px 0 14px;">{_status_pills}</div>', unsafe_allow_html=True)

# 首次进入时显示 AI 身份声明（欢迎卡）
if not state.get("_greeting_shown", False):
    st.markdown(
        """
        <div class="anxin-card" style="background-color: rgba(123,183,110,0.08);
                    border-color: rgba(123,183,110,0.35); padding: 18px 20px;">
            <div style="display:flex; gap:14px; align-items:flex-start;">
                <div style="font-size:30px; line-height:1.2;">🌱</div>
                <div>
                    <div style="font-weight:600; margin-bottom:4px;">你好呀！我是安心童伴</div>
                    <div style="font-size:14px; line-height:1.6; color: rgba(28,28,28,0.82);">
                        是你的 AI 小伙伴，会陪你聊天、讲故事、回答你的问题。<br>
                        但我不是真人哦——如果你遇到重要的事情，记得告诉爸爸妈妈或老师 ❤️
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    state.set("_greeting_shown", True)

# 每日小挑战（P1-1）：星球不为空且有聊天历史时显示
_planet = state.get_planet()
_has_entries = _planet and any(
    _planet.get(k) for k in ["stars", "clouds", "sprouts", "stories"]
)
if _has_entries and state.get_chat_history():
    challenge = daily_challenges.get_today_challenge()
    st.markdown(
        f"""
        <div class="daily-challenge-card">
            <div style="display:flex; align-items:flex-start; gap:10px;">
                <span class="challenge-icon">🌟</span>
                <div>
                    <div class="challenge-text">{challenge['text']}</div>
                    <div class="challenge-hint">完成了？去小星球种一棵探索芽吧！</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 渲染历史聊天
for msg in state.get_chat_history():
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🌱"):
        if msg["role"] == "user":
            st.markdown(_USER_MARKER, unsafe_allow_html=True)
        st.markdown(msg["content"])


# ---------------------------------------------------------------------------
# 处理用户输入
# ---------------------------------------------------------------------------
def _run_pipeline_and_reply(user_input: str) -> None:
    if len(user_input) > 500:
        user_input = user_input[:500]
        st.toast("你的消息有点长，我截断了一部分", icon="✂️")

    state.append_chat("user", user_input)
    with st.chat_message("user", avatar="👤"):
        st.markdown(_USER_MARKER, unsafe_allow_html=True)
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🌱"):
        with st.status("安心童伴正在思考…", expanded=False) as status:
            try:
                result = pipeline_mod.run(
                    user_input=user_input,
                    age_tier=state.get_age_tier(),
                    mode=state.get_mode(),
                    planet=state.get_planet(),
                    chat_history=state.get_chat_history()[:-1],
                    parent_preferences=state.get_topic_preferences(),
                )
                state.record_pipeline_run(result)
                status.update(label="思考完成", state="complete", expanded=False)
            except Exception as e:
                status.update(label=f"出错了：{e}", state="error")
                return

        st.write_stream(pipeline_mod.stream_reply(result.final_reply))

        if result.used_crisis_template:
            st.error("⚠️ 这是一个很重要的时刻。请立即找爸爸妈妈或老师聊聊，或拨打 12355 青少年服务热线。")
        elif result.critic_intercepted:
            st.warning("安心童伴检查了一下刚才的回答，觉得不太合适，所以换了个话题。我们聊点别的吧～")
        elif result.parent_alert:
            st.info("安心童伴已经把你刚才提到的事，悄悄告诉了家长——他们想帮你。")

    state.append_chat("assistant", result.final_reply)

    # TTS 语音播报
    st.markdown(voice.get_tts_html(result.final_reply), unsafe_allow_html=True)

    # 低风险对话后建议种下星球
    if not result.used_crisis_template and not result.critic_intercepted:
        suggestion = _suggest_planet_entry(
            user_input, result.final_reply, state.get_mode(), result.risk_level
        )
        if suggestion:
            st.markdown(
                styles.alert_card(
                    f'<span style="font-size:13px;">💡 {suggestion["hint"]}</span>',
                    C["risk_0"], tinted=True,
                ),
                unsafe_allow_html=True,
            )
            col_a, col_b = st.columns([3, 1])
            with col_b:
                if st.button("种下它 🌱", key=f"plant_{len(state.get_chat_history())}"):
                    state.set("pending_planet_entry", suggestion)
                    st.switch_page("pages/2_我的小星球.py")

    # 内容推荐卡片
    if not result.used_crisis_template and not result.critic_intercepted:
        _emotion_trend = em.get_emotion_trend(days=7)
        rec_result = rec_engine.recommend_after_reply(
            planet=state.get_planet(),
            age_tier=state.get_age_tier(),
            mode=state.get_mode(),
            latest_topic=result.topic,
            emotion_trend=_emotion_trend,
        )
        if rec_result and rec_result.items:
            st.markdown("---")
            st.markdown("#### 💡 还想了解……？")
            st.caption(rec_result.source_detail)
            rec_cols = st.columns(len(rec_result.items))
            for i, item in enumerate(rec_result.items):
                with rec_cols[i]:
                    type_emoji = {"encyclopedia": "🔬", "story": "📖", "chat": "💬"}
                    st.markdown(
                        styles.icon_card(
                            type_emoji.get(item.type, "💡"), item.title, item.hint,
                            padding="12px 14px",
                        ),
                        unsafe_allow_html=True,
                    )
                    if st.button(f"聊聊这个 →", key=f"rec_{i}_{len(state.get_chat_history())}"):
                        state.set("pending_input", item.title)
                        st.rerun()


# 处理教程页跳转来的预设输入
pending = state.get("pending_input")
if pending:
    state.set("pending_input", None)
    _run_pipeline_and_reply(pending)

# 语音输入
voice_col1, voice_col2 = st.columns([1, 3])
with voice_col1:
    audio_value = st.audio_input("🎤 语音输入", label_visibility="visible")
with voice_col2:
    st.caption("点击麦克风录音，说完后再次点击停止。")

if audio_value is not None:
    with st.spinner("正在识别语音……"):
        transcribed = voice.transcribe(audio_value.getvalue())
    if transcribed:
        st.success(f"识别结果：{transcribed}")
        _run_pipeline_and_reply(transcribed)
    else:
        if voice.is_whisper_available():
            st.warning("语音识别失败，请在下方用文字输入")
        else:
            st.info("语音识别未安装，请在下方用文字输入。安装：pip install faster-whisper")

# 文字输入
user_input = st.chat_input("和安心童伴说点什么吧…")
if user_input and user_input.strip():
    _run_pipeline_and_reply(user_input)
