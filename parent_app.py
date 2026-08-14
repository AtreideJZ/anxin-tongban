"""安心童伴 AI — 家长端（独立入口）

启动方式：streamlit run parent_app.py
与儿童端（app.py）共享 core/ 模块，独立部署。
"""
from __future__ import annotations

import os
from collections import Counter

import streamlit as st

from core import memory_manager as mm
from core import proactive_engine as pro
from core import episodic_memory as em
from utils import state, styles

st.set_page_config(
    page_title="安心童伴 · 家长端",
    page_icon="👨‍👩‍👧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

state.init_state()
styles.apply_theme()


# ---------------------------------------------------------------------------
# PIN 门控
# ---------------------------------------------------------------------------
def _get_parent_pin() -> str:
    """从 secrets 或环境变量读取家长 PIN，默认 0000"""
    try:
        return st.secrets.get("PARENT_PIN", os.environ.get("PARENT_PIN", "0000"))
    except Exception:
        return os.environ.get("PARENT_PIN", "0000")


def _verify_pin(input_pin: str) -> bool:
    """常数时间比对 PIN"""
    stored = _get_parent_pin()
    if len(input_pin) != len(stored):
        return False
    result = 0
    for a, b in zip(input_pin, stored):
        result |= ord(a) ^ ord(b)
    return result == 0


if not state.get("_parent_authenticated", False):
    st.markdown("## 👨‍👩‍👧 家长端")

    st.markdown(
        """
        <div class="anxin-card" style="margin: 16px 0;">
            <p>家长守护面板包含孩子的使用统计、情绪趋势和风险提醒。
            请输入家长密码以继续。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pin_input = st.text_input(
        "家长密码",
        type="password",
        placeholder="输入 4 位数字密码",
        max_chars=4,
        label_visibility="collapsed",
    )

    col_pin1, col_pin2 = st.columns([1, 3])
    with col_pin1:
        if st.button("验证", type="primary", use_container_width=True):
            if _verify_pin(pin_input):
                state.set("_parent_authenticated", True)
                st.rerun()
            else:
                st.error("密码错误")

    st.caption(f"默认密码：0000（可在 .streamlit/secrets.toml 中设置 PARENT_PIN 修改）")

    st.markdown("---")
    if st.button("💬 回到儿童端", use_container_width=True):
        st.switch_page("pages/1_安心童伴.py")
    st.stop()


# ---------------------------------------------------------------------------
# 退出按钮（侧边栏）
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 👨‍👩‍👧 家长端")
    if st.button("🚪 退出登录", use_container_width=True):
        state.set("_parent_authenticated", False)
        st.rerun()
    st.caption(f"孩子年龄档：{state.get_age_tier()} 岁")
    st.divider()
    if st.button("💬 儿童端", use_container_width=True):
        st.switch_page("pages/1_安心童伴.py")
    if st.button("📖 使用指南", use_container_width=True):
        st.switch_page("pages/0_使用指南.py")

# ---------------------------------------------------------------------------
# 家长同意流程（首次使用）
# ---------------------------------------------------------------------------
if not state.is_parent_consent_given():
    st.markdown("## 👨‍👩‍👧 监护人同意")

    st.markdown(
        """
        <div class="anxin-card" style="margin: 16px 0;">
            <p>欢迎来到家长守护面板。根据《人工智能拟人化互动服务管理暂行办法》（2026.7.15 施行），
            未成年人使用 AI 服务需取得监护人同意。</p>
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
    st.stop()


# ---------------------------------------------------------------------------
# 数据准备
# ---------------------------------------------------------------------------
topics = state.get_conversation_topics()
usage_min = state.get_usage_minutes()
alerts = state.get_parent_alerts()
planet = state.get_planet()

topic_label_map = {
    "safe": "日常聊天", "privacy_leak": "隐私安全", "school_bullying": "校园欺凌",
    "emotional_low": "情绪低落", "self_harm": "高风险情绪",
    "ai_dependency": "AI 依赖", "inappropriate_content": "不适龄内容",
}

topic_counter = Counter(t["topic"] for t in topics)
risk_stats = Counter()
topic_stats = Counter()
mode_stats = Counter()
for t in topics:
    risk_stats[t["risk_level"]] += 1
    topic_stats[t["topic"]] += 1
    mode_stats[t.get("strategy", "normal_child_friendly_response")] += 1

# ---------------------------------------------------------------------------
# 主面板（4 个标签页）
# ---------------------------------------------------------------------------
st.markdown("## 👨‍👩‍👧 家长守护仪表盘")
st.caption("这里只显示脱敏摘要和风险提醒，不会展示孩子的对话原文。")

tab1, tab2, tab3, tab4 = st.tabs(["📊 仪表盘", "🚨 风险与预警", "📈 情绪与学习", "⚙️ 设置"])

# ===== Tab 1: 仪表盘 =====
with tab1:
    # 话题摘要
    st.markdown("### 📝 话题摘要")
    topic_summary_parts = [f"{topic_label_map.get(t, t)} {c} 次" for t, c in topic_counter.most_common()]
    if topic_summary_parts:
        summary_text = "孩子今天主要聊了：" + "、".join(topic_summary_parts) + "。"
    else:
        summary_text = "孩子今天还没有使用安心童伴。"

    st.markdown(
        f"""
        <div class="anxin-card">
            <div style="font-size: 15px; line-height: 1.6;">{summary_text}</div>
            <div class="meta" style="margin-top: 8px;">本面板不展示孩子的对话原文，仅展示脱敏后的主题摘要。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 使用统计
    st.markdown("### ⏱️ 使用统计")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("今日使用时长", f"{usage_min} 分钟")
    with col2:
        st.metric("今日对话轮数", len(topics))
    with col3:
        high_risk_count = sum(1 for t in topics if t["risk_level"] >= 2)
        st.metric("中/高风险对话", high_risk_count)

    # 图表
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("**📈 风险等级分布**")
        if risk_stats:
            import pandas as pd
            risk_df = pd.DataFrame([
                {"风险等级": f"等级 {lvl}", "次数": cnt}
                for lvl, cnt in sorted(risk_stats.items())
            ])
            st.bar_chart(risk_df.set_index("风险等级")["次数"], use_container_width=True, height=200)
        else:
            st.caption("暂无对话数据")

    with chart_col2:
        st.markdown("**📊 主题分布**")
        if topic_stats:
            import pandas as pd
            topic_df = pd.DataFrame([
                {"主题": topic_label_map.get(t, t), "次数": c}
                for t, c in topic_stats.most_common()
            ])
            st.bar_chart(topic_df.set_index("主题")["次数"], use_container_width=True, height=200)
        else:
            st.caption("暂无对话数据")

    # 策略分布
    chart_col3, chart_col4 = st.columns(2)
    with chart_col3:
        st.markdown("**📅 7 日风险趋势**")
        # 从 pipeline runs 中提取近 7 天的风险数据
        import pandas as pd
        from datetime import datetime as dt, timedelta
        seven_days_ago = dt.now() - timedelta(days=7)
        daily_risks: dict[str, dict[int, int]] = {}
        for run in state.get_all_pipeline_runs():
            try:
                ts = run.decision_record.get("timestamp", "")
                if ts:
                    run_date = ts[:10]  # "2026-07-29"
                    run_date_dt = dt.strptime(run_date, "%Y-%m-%d")
                    if run_date_dt >= seven_days_ago:
                        if run_date not in daily_risks:
                            daily_risks[run_date] = {0: 0, 1: 0, 2: 0, 3: 0}
                        rl = run.risk_level
                        if 0 <= rl <= 3:
                            daily_risks[run_date][rl] += 1
            except (ValueError, KeyError):
                continue
        if daily_risks:
            dates_sorted = sorted(daily_risks.keys())
            trend_data = []
            for d in dates_sorted:
                counts = daily_risks[d]
                trend_data.append({
                    "日期": d[-5:],  # "07-29"
                    "安全(0级)": counts[0],
                    "轻度(1级)": counts[1],
                    "中度(2级)": counts[2],
                    "高风险(3级)": counts[3],
                })
            trend_df = pd.DataFrame(trend_data)
            st.bar_chart(
                trend_df.set_index("日期"),
                use_container_width=True,
                height=200,
                color=["#7BB76E", "#E8C75A", "#E8954C", "#D9534F"],
            )
        else:
            st.caption("暂无近 7 天对话数据")

    with chart_col4:
        st.markdown("**🏷️ 主题变化**")
        # 从情节记忆中提取主题变化
        recent_eps = em.retrieve_recent(days=7, limit=20)
        if recent_eps:
            ep_topic_counter = Counter()
            for ep in recent_eps:
                for t in ep.topics:
                    ep_topic_counter[t] += 1
            if ep_topic_counter:
                ep_topic_df = pd.DataFrame([
                    {"探索主题": topic, "提及次数": count}
                    for topic, count in ep_topic_counter.most_common(8)
                ])
                st.bar_chart(
                    ep_topic_df.set_index("探索主题")["提及次数"],
                    use_container_width=True,
                    height=200,
                )
            else:
                st.caption("暂无主题数据，多聊几轮后有变化趋势")
        else:
            st.caption("暂无情节记忆数据。多聊几轮后这里会出现主题变化。")

    st.markdown("---")

    # 策略分布
    if mode_stats:
        strategy_label_map = {
            "normal_child_friendly_response": "常规友好回应",
            "warm_redirect_with_empathy": "温和转移",
            "refuse_with_reason": "礼貌拒答",
            "encourage_real_world_action": "鼓励现实行动",
            "crisis_template": "危机模板",
            "guardrail_block": "输入拦截",
            "parent_alert_strategy": "家长提醒",
            "socratic_learning_guide": "苏格拉底学习引导",
        }
        st.markdown("**🎯 策略分布**")
        strategy_html_parts = []
        for k, v in mode_stats.most_common():
            label = strategy_label_map.get(k, k)
            pct = (v / sum(mode_stats.values())) * 100
            color = styles.COLORS["charcoal"]
            if "crisis" in k or "block" in k:
                color = styles.risk_color(3)
            elif "redirect" in k or "refuse" in k:
                color = styles.risk_color(2)
            elif "encourage" in k:
                color = styles.risk_color(0)
            strategy_html_parts.append(
                f'<div style="margin-bottom:6px;">'
                f'<div style="display:flex;justify-content:space-between;font-size:13px;">'
                f'<span>{label}</span><span class="meta">{v} 次 · {pct:.0f}%</span></div>'
                f'{styles.progress_bar(pct, color)}'
                f'</div>'
            )
        st.markdown(
            f'<div class="anxin-card">{"".join(strategy_html_parts)}</div>',
            unsafe_allow_html=True,
        )

# ===== Tab 2: 风险与预警 =====
with tab2:
    st.markdown("### 🚨 风险事件")

    if not alerts:
        st.success("目前没有风险事件。孩子今天一切正常。")
    else:
        for a in alerts:
            color = styles.risk_color(a["risk_level"])
            is_critical = (a["risk_level"] == 3 and a["topic"] == "self_harm")
            urgent_badge = (
                styles.pill("🚨 立即关注", styles.COLORS["off_white"], styles.risk_color(3))
                if is_critical else ""
            )
            card_html = (
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;">'
                f'<div>{styles.risk_badge(a["risk_level"])} · {topic_label_map.get(a["topic"], a["topic"])}{urgent_badge}</div>'
                f'<div class="meta">{a["time"]}</div>'
                f'</div>'
                f'<div style="margin:6px 0;font-size:14px;line-height:1.5;">{a["summary"]}</div>'
                f'<div class="meta">💡 建议：{a["suggestion"]}</div>'
            )
            st.markdown(
                styles.alert_card(card_html, color, tinted=is_critical),
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("### 🔔 主动预警")

    proactive_alerts = pro.run_all_checks(
        planet=planet,
        conversation_topics=topics,
        latest_pipeline=state.get_latest_pipeline(),
        last_active_time=state.get("session_start_time"),
        usage_minutes=usage_min,
    )

    if not proactive_alerts:
        st.success("✅ 目前没有需要关注的主动预警。")
    else:
        severity_emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}
        severity_color = {
            "critical": styles.risk_color(3),
            "warning": styles.risk_color(2),
            "info": styles.COLORS["blue"],
        }
        for alert in proactive_alerts:
            emoji_icon = severity_emoji.get(alert.severity, "ℹ️")
            color = severity_color.get(alert.severity, styles.COLORS["muted_gray"])
            is_critical = alert.severity == "critical"
            card_html = (
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;">'
                f'<div style="font-weight:600;">{emoji_icon} {alert.title}</div>'
                f'<div class="meta">{alert.triggered_at[:16]}</div>'
                f'</div>'
                f'<div style="margin:6px 0;font-size:14px;line-height:1.5;">{alert.summary}</div>'
                f'<div class="meta">💡 {alert.suggestion}</div>'
            )
            st.markdown(
                styles.alert_card(card_html, color, tinted=is_critical),
                unsafe_allow_html=True,
            )

# ===== Tab 3: 情绪与学习 =====
with tab3:
    st.markdown("### 📈 情绪与学习趋势")

    emo_col1, emo_col2 = st.columns(2)

    with emo_col1:
        st.markdown("**😊 7 日情绪趋势**")
        emotion_data = em.get_emotion_trend(days=7)
        total_emo = sum(emotion_data.values())
        if total_emo > 0:
            import pandas as pd
            emo_labels = {
                "positive": "😊 积极", "neutral": "😐 平稳",
                "slightly_negative": "😔 略有低落", "negative": "😢 需要关注",
            }
            emo_df = pd.DataFrame([
                {"情绪": emo_labels.get(k, k), "次数": v}
                for k, v in emotion_data.items() if v > 0
            ])
            st.bar_chart(emo_df.set_index("情绪")["次数"], use_container_width=True, height=200)
        else:
            st.caption("暂无足够对话数据。多聊几轮后这里会出现情绪变化图。")

    with emo_col2:
        st.markdown("**📚 学习兴趣分布**")
        tag_counter = Counter()
        for key in ["stars"]:
            for entry in (planet.get(key, []) or []):
                if isinstance(entry, dict):
                    for tag in (entry.get("tags", []) or []):
                        tag_counter[tag] += 1
        if tag_counter:
            import pandas as pd
            tag_df = pd.DataFrame([
                {"兴趣标签": tag, "次数": count}
                for tag, count in tag_counter.most_common(8)
            ])
            st.bar_chart(tag_df.set_index("兴趣标签")["次数"], use_container_width=True, height=200)
        else:
            st.caption("孩子还没有在小星球里种下标签。种多了这里会出现兴趣分布。")

    ep_count = em.count_episodes()
    if ep_count > 0:
        st.markdown(f"**🧠 情节记忆**：已积累 {ep_count} 条对话摘要（30 天滚动）")
        st.caption("情节记忆不保存对话原文，仅保留结构化摘要，用于跨会话个性化引导。")

# ===== Tab 4: 设置 =====
with tab4:
    st.markdown("### ⚙️ 话题偏好设置")
    st.caption("对话题分级。设置后在儿童端下一次对话时生效。")

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
        )
        new_forbidden = st.multiselect(
            "🚫 禁止话题（强烈引导转向）",
            options=_all_topics,
            default=_prefs.get("forbidden", []),
        )
        overlap = set(new_limited) & set(new_forbidden)
        if overlap:
            st.warning(f"以下话题同时出现在「限制」和「禁止」中，已自动从「限制」移除：{', '.join(overlap)}")
            new_limited = [t for t in new_limited if t not in new_forbidden]
        new_allowed = [t for t in _all_topics if t not in new_limited and t not in new_forbidden]

        if st.button("保存偏好", type="primary", use_container_width=True):
            state.set_topic_preferences({
                "allowed": new_allowed,
                "limited": new_limited,
                "forbidden": new_forbidden,
            })
            st.success("已保存。儿童端下一次对话起生效。")
            st.rerun()

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

    st.markdown("---")
    st.markdown("### 🌱 小星球概览")

    if state.get_age_tier() == "8-11":
        counts = mm.count_entries(planet)
        if counts["total"] == 0:
            st.info("孩子还没有在小星球里种下任何东西。")
        else:
            cs1, cs2, cs3, cs4, cs5, cs6 = st.columns(6)
            with cs1:
                st.metric("⭐ 好奇星", counts["star"])
            with cs2:
                st.metric("☁️ 心情云", counts["cloud"])
            with cs3:
                st.metric("🌱 探索芽", counts["sprout"])
            with cs4:
                st.metric("📖 故事册", counts["story"])
            with cs5:
                st.metric("✉️ 时间胶囊", counts["capsule"])
            with cs6:
                st.metric("总计", counts["total"])
            st.caption("8-11 岁守护模式：家长可见星球条目数量，不显示具体内容。")
    else:
        st.info("孩子处于 12-14 岁信任模式。根据隐私边界设计，小星球的具体信息对家长完全不可见。")

    st.markdown("---")
    st.markdown("### 📋 合规状态")

    compliance_items = [
        ("禁止诱导不安全行为", "✅ 已覆盖", 100, styles.risk_color(0)),
        ("禁止虚拟亲密关系", "✅ 已覆盖", 100, styles.risk_color(0)),
        ("监护人同意", "✅ 已覆盖", 100, styles.risk_color(0)),
        ("未成年人模式", "✅ 已覆盖", 100, styles.risk_color(0)),
        ("年龄识别", "✅ 已覆盖", 70, styles.risk_color(1)),
        ("AI 身份标识", "✅ 已覆盖", 100, styles.risk_color(0)),
        ("2 小时使用提醒", "✅ 已覆盖", 100, styles.risk_color(0)),
        ("算法备案", "⚠️ 评估中", 50, styles.risk_color(1)),
    ]

    for req, status_text, pct, color in compliance_items:
        st.markdown(
            f'<div class="anxin-card" style="padding:10px 16px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<div><b>{req}</b></div>'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span style="color:{color};font-weight:600;">{status_text}</span>'
            f'<span style="display:inline-block;width:60px;">{styles.progress_bar(pct, color)}</span>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

    st.caption("安心童伴已覆盖《拟人化互动办法》全部核心条款。")

# ---------------------------------------------------------------------------
# 页脚
# ---------------------------------------------------------------------------
st.markdown("")
st.markdown("---")
st.markdown(
    '<div class="meta" style="text-align:center;">安心童伴 AI · 家长守护面板 · 数据仅在本地存储</div>',
    unsafe_allow_html=True,
)
