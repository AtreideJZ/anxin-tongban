"""安心童伴 AI — 我的小星球（策展空间）

依据 docs/安心童伴AI-产品需求文档(PRD).md F-023 设计：
- 卡片网格展示已有条目，按时间倒序
- "种下新东西"按钮 → 新建条目表单
- 5 类条目：⭐好奇星 / ☁️心情云 / 🌱探索芽 / 📖故事册 / ✉️时间胶囊
- 不计数、不打分、不搞排行榜
- 探索芽记录真实世界的经历和发现，纯 AI 聊天内容会温和提示
- 时间胶囊可以给未来的自己留言，到期自动解锁
"""
from __future__ import annotations

import streamlit as st

from core import memory_manager as mm
from utils import state, styles

st.set_page_config(
    page_title="我的小星球",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

state.init_state()
styles.apply_theme()

C = styles.COLORS

# ---------------------------------------------------------------------------
# 页头
# ---------------------------------------------------------------------------
st.markdown("## 🌱 我的小星球")
st.caption("由你自己决定的成长空间。每一颗星、每一朵云、每一棵芽，都是你愿意留下来的瞬间。")

# ---------------------------------------------------------------------------
# 检查时间胶囊：自动解锁到期的
# ---------------------------------------------------------------------------
newly_unlocked = mm.check_capsules(state.get_planet())
if newly_unlocked:
    state.set_planet(state.get_planet())
    for cap in newly_unlocked:
        st.balloons()
        st.toast(f"✉️ 一封时间胶囊开封了！「{cap.get('title', '')}」", icon="✉️")

# ---------------------------------------------------------------------------
# 一键采纳：从聊天页跳转来的星球建议（P0-5）
# ---------------------------------------------------------------------------
_pending_entry = state.get("pending_planet_entry")
if _pending_entry:
    state.set("pending_planet_entry", None)
    entry = {
        "type": _pending_entry.get("type", "star"),
        "title": _pending_entry.get("title", ""),
        "content": _pending_entry.get("content", ""),
        "tags": ["聊天采纳"],
        "source": "chat_suggestion",
    }
    mm.create_entry(state.get_planet(), entry)
    state.set_planet(state.get_planet())
    st.success(f"🌱 已种下：{_pending_entry.get('title', '')}")
    st.caption("从聊天中采纳的条目已加入小星球。你可以在下方找到它，或继续手动种下新的。")


# ---------------------------------------------------------------------------
# 星球生态可视化（P0-1）
# ---------------------------------------------------------------------------
ecosystem = mm.get_planet_ecosystem(state.get_planet())
weather = ecosystem["weather"]

# 天气横幅
st.markdown(
    f"""
    <div class="planet-weather">
        <span class="weather-emoji">{weather['emoji']}</span>
        <span class="weather-text">{weather['text']}</span>
        <div class="weather-desc">{weather['description']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 生态元素条
eco_items_html = ""
for el in ecosystem["elements"]:
    eco_items_html += (
        f'<div class="ecosystem-item">'
        f'<span class="eco-icon">{el["icon"]}</span>'
        f'<span class="eco-label">{el["label"]}</span>'
        f'<div class="eco-desc">{el["desc"]}</div>'
        f'</div>'
    )

st.markdown(
    f'<div class="planet-ecosystem">{eco_items_html}</div>',
    unsafe_allow_html=True,
)


# 类型说明（紧凑版，保留用于表单参考）
type_meta = mm.TYPE_META
st.markdown(
    f"""
    <div class="anxin-card" style="margin: 0 0 20px; padding: 10px 16px; font-size: 12px;">
        <span style="margin-right: 14px;">{type_meta['star']['icon']} <b>{type_meta['star']['label']}</b> 问题与发现</span>
        <span style="margin-right: 14px;">{type_meta['cloud']['icon']} <b>{type_meta['cloud']['label']}</b> 情绪时刻</span>
        <span style="margin-right: 14px;">{type_meta['sprout']['icon']} <b>{type_meta['sprout']['label']}</b> 真实世界的经历</span>
        <span style="margin-right: 14px;">{type_meta['story']['icon']} <b>{type_meta['story']['label']}</b> 共创故事</span>
        <span>{type_meta['capsule']['icon']} <b>{type_meta['capsule']['label']}</b> 给未来的自己</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# 种下新东西
# ---------------------------------------------------------------------------
with st.expander("＋ 种下新东西", expanded=False):
    with st.form("new_entry_form", clear_on_submit=True):
        col_a, col_b = st.columns([1, 2])
        with col_a:
            entry_type = st.selectbox(
                "类型",
                options=["star", "cloud", "sprout", "story", "capsule"],
                format_func=lambda x: f"{type_meta[x]['icon']} {type_meta[x]['label']}",
            )
        with col_b:
            title = st.text_input("标题", placeholder="给这一刻起个名字…")

        # 时间胶囊专属字段：解锁时间
        if entry_type == "capsule":
            unlock_preset = st.selectbox(
                "什么时候打开？",
                options=["1周后", "1个月后", "3个月后", "自定义日期"],
                index=1,
            )
            from datetime import datetime, timedelta

            if unlock_preset == "1周后":
                unlock_date = (datetime.now() + timedelta(days=7)).strftime("%m月%d日").lstrip("0")
            elif unlock_preset == "1个月后":
                unlock_date = (datetime.now() + timedelta(days=30)).strftime("%m月%d日").lstrip("0")
            elif unlock_preset == "3个月后":
                unlock_date = (datetime.now() + timedelta(days=90)).strftime("%m月%d日").lstrip("0")
            else:
                unlock_date = ""
                custom_date = st.text_input("输入解锁日期", placeholder="例如：8月15日 或 2026-08-15")
                if custom_date:
                    unlock_date = custom_date

            content_label = "想对未来的自己说什么？"
            content_placeholder = "嘿，你现在变得更勇敢了吗？还记得写这封信的时候吗…"
            mood = None
        elif entry_type == "cloud":
            mood = st.select_slider("心情色", options=["blue", "pink", "gray", "yellow"], value="pink")
        else:
            mood = None

        if entry_type == "story":
            content_label = "故事预览（开头一段）"
            content_placeholder = "从前有一只小恐龙…"
        elif entry_type == "sprout":
            content_label = "你在真实世界里经历了什么？"
            content_placeholder = "例如：我告诉了老师同学推我的事… 或者 在公园发现了一只没见过的虫子…"
        elif entry_type == "cloud":
            content_label = "当时是什么感受？"
            content_placeholder = "今天有点难过，因为…"
        elif entry_type == "capsule":
            # labels already set above
            pass
        else:
            content_label = "记下你的发现或问题"
            content_placeholder = "我发现… / 我想知道…"

        content = st.text_area(content_label, placeholder=content_placeholder, height=80)
        tags_str = st.text_input("标签（用空格分隔）", placeholder="科学 好奇")

        submitted = st.form_submit_button("种下来 🌱", use_container_width=True, type="primary")
        if submitted:
            if not title.strip():
                st.error("给这一刻起个名字吧～")
                st.stop()

            # 探索芽只记录真实世界事件，过滤纯 AI 聊天内容
            if entry_type == "sprout":
                ai_only_signals = ["和 ai 聊天", "和ai聊天", "跟 ai 聊", "跟ai聊", "ai 陪我", "ai陪我"]
                if any(s in content.lower() for s in ai_only_signals) and not any(
                    w in content for w in ["告诉", "说", "找", "主动", "和妈妈", "和爸爸", "老师", "同学"]
                ):
                    st.warning(
                        "探索芽是记录你在**真实世界**里的经历和发现哦——"
                        "比如「在公园发现了一只没见过的虫子」「第一次自己坐地铁」"
                        "「我告诉了老师同学推我的事」。\n\n"
                        "和 AI 聊天是很开心，但值得记住的回忆在真实世界里。"
                        "要不要换成一朵心情云或一颗好奇星？"
                    )
                    st.stop()

            # 时间胶囊
            if entry_type == "capsule":
                if not unlock_date:
                    st.error("请选择或输入解锁日期～")
                    st.stop()
                capsule = {
                    "title": title.strip(),
                    "content": content.strip(),
                    "unlock_at": unlock_date,
                    "tags": tags_str.split() if tags_str.strip() else [],
                }
                mm.create_capsule(state.get_planet(), capsule)
                state.set_planet(state.get_planet())
                st.success(f"✉️ 时间胶囊封好了！{unlock_date} 那天回来打开吧～")
                st.rerun()

            entry = {
                "type": entry_type,
                "title": title.strip(),
                "content": content.strip(),
                "tags": tags_str.split() if tags_str.strip() else [],
                "source": "manual",
            }
            if mood:
                entry["mood"] = mood
            if entry_type == "sprout":
                entry["verified_action"] = True

            mm.create_entry(state.get_planet(), entry)
            state.set_planet(state.get_planet())
            st.success(f"{type_meta[entry_type]['icon']} 种下啦！")
            st.rerun()


st.markdown("")

# ---------------------------------------------------------------------------
# 卡片网格
# ---------------------------------------------------------------------------
planet = state.get_planet()
all_entries = mm._flatten_planet(planet)  # 内部拍平函数（含 capsules）
# 按日期倒序（粗略：用原始字符串排序后反转）
all_entries.reverse()

if not all_entries:
    st.info("你的小星球还是空的。点上面的「＋ 种下新东西」开始记录吧～")
else:
    # 分开渲染：先渲染普通卡片，再渲染胶囊（胶囊有特殊样式）
    normal_entries = [e for e in all_entries if e.get("type") != "capsule"]
    capsule_entries = [e for e in all_entries if e.get("type") == "capsule"]

    cols_per_row = 3

    # 普通卡片网格
    for i in range(0, len(normal_entries), cols_per_row):
        row = normal_entries[i : i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, entry in zip(cols, row):
            with col:
                meta = type_meta.get(entry.get("type", "star"), type_meta["star"])
                title = entry.get("title", "（未命名）")
                date = entry.get("date", "")
                content = entry.get("content") or entry.get("preview") or ""
                tags = entry.get("tags", []) or []
                tags_html = "".join(
                    styles.pill(t, C["muted_gray"], "rgba(28,28,28,0.04)")
                    for t in tags
                )
                st.markdown(
                    f"""
                    <div class="planet-card">
                        <div style="font-size: 22px;">{meta['icon']}</div>
                        <div style="font-weight: 600; margin: 4px 0 2px; font-size: 15px;">{title}</div>
                        <div class="meta" style="font-size: 12px; margin-bottom: 6px;">{meta['label']} · {date}</div>
                        <div style="font-size: 13px; color: {C['charcoal']}; line-height: 1.5;">
                            {(content[:80] + '…') if len(content) > 80 else content}
                        </div>
                        <div style="margin-top: 8px;">{tags_html}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("删除", key=f"del_{entry.get('id', '')}_{i}", help="删除这条条目", use_container_width=True):
                    mm.delete_entry(state.get_planet(), entry.get("id", ""))
                    state.set_planet(state.get_planet())
                    st.rerun()

    # 时间胶囊区域
    if capsule_entries:
        st.markdown("---")
        st.markdown("### ✉️ 时间胶囊")
        st.caption("写给未来的自己——封存时看不见，到期自动开封。")

        for i in range(0, len(capsule_entries), cols_per_row):
            row = capsule_entries[i : i + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, entry in zip(cols, row):
                with col:
                    meta = type_meta.get("capsule", {"label": "时间胶囊", "icon": "✉️"})
                    title = entry.get("title", "（未命名）")
                    created = entry.get("created_at", "")
                    unlock_at = entry.get("unlock_at", "")
                    content = entry.get("content", "")
                    tags = entry.get("tags", []) or []
                    unlocked = entry.get("unlocked", False)

                    tags_html = "".join(
                        styles.pill(t, C["muted_gray"], "rgba(28,28,28,0.04)")
                        for t in tags
                    )

                    if unlocked:
                        # 已解锁：显示内容
                        card_class = "capsule-card revealed"
                        st.markdown(
                            f"""
                            <div class="{card_class}">
                                <div style="font-size: 22px;">📬</div>
                                <div style="font-weight: 600; margin: 4px 0 2px; font-size: 15px;">{title}</div>
                                <div class="meta" style="font-size: 12px; margin-bottom: 6px;">
                                    封存于 {created} · 已开封
                                </div>
                                <div style="font-size: 13px; color: {C['charcoal']}; line-height: 1.5;">
                                    {(content[:120] + '…') if len(content) > 120 else content}
                                </div>
                                <div style="margin-top: 8px;">{tags_html}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        # 封装状态：模糊预览 + 倒计时
                        countdown = mm.get_capsule_countdown(entry)
                        card_class = "capsule-card sealed"
                        st.markdown(
                            f"""
                            <div class="{card_class}">
                                <div style="font-size: 22px;">🔒</div>
                                <div style="font-weight: 600; margin: 4px 0 2px; font-size: 15px;">{title}</div>
                                <div class="meta" style="font-size: 12px; margin-bottom: 4px;">
                                    封存于 {created}
                                </div>
                                <span class="capsule-countdown">⏳ {countdown}</span>
                                <div class="capsule-preview" style="font-size: 12px; color: {C['muted_gray']}; line-height: 1.4; margin-top: 6px;">
                                    {content[:60] + ('…' if len(content) > 60 else '')}
                                </div>
                                <div style="margin-top: 8px;">{tags_html}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    if st.button("删除", key=f"del_cap_{entry.get('id', '')}_{i}", help="删除这个胶囊", use_container_width=True):
                        mm.delete_entry(state.get_planet(), entry.get("id", ""))
                        state.set_planet(state.get_planet())
                        st.rerun()


st.markdown("")
st.markdown("---")
st.markdown(
    '<div class="meta" style="text-align:center;">'
    '小星球是策展式记忆——AI 只在你主动留下的条目里检索记忆。'
    '</div>',
    unsafe_allow_html=True,
)

# 底部导航
st.markdown("")
nav1, nav2 = st.columns(2)
with nav1:
    if st.button("💬 回到聊天", use_container_width=True, type="primary"):
        st.switch_page("pages/1_安心童伴.py")
with nav2:
    if st.button("📖 使用指南", use_container_width=True):
        st.switch_page("pages/0_使用指南.py")
