"""安心童伴 AI — 我的小星球（策展空间）

依据 docs/安心童伴AI-产品需求文档(PRD).md F-023 设计：
- 卡片网格展示已有条目，按时间倒序
- "种下新东西"按钮 → 新建条目表单
- 4 类条目：⭐好奇星 / ☁️心情云 / 🌱勇敢芽 / 📖故事册
- 不计数、不打分、不搞排行榜
- 勇敢芽只记录现实行动，纯 AI 聊天内容会温和提示
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

# ---------------------------------------------------------------------------
# 页头
# ---------------------------------------------------------------------------
st.markdown("## 🌱 我的小星球")
st.caption("由你自己决定的成长空间。每一颗星、每一朵云、每一棵芽，都是你愿意留下来的瞬间。")

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

# 类型说明
type_meta = mm.TYPE_META
st.markdown(
    f"""
    <div class="anxin-card" style="margin: 12px 0 20px;">
        <span style="margin-right: 16px;">{type_meta['star']['icon']} <b>{type_meta['star']['label']}</b> 问题与发现</span>
        <span style="margin-right: 16px;">{type_meta['cloud']['icon']} <b>{type_meta['cloud']['label']}</b> 情绪时刻</span>
        <span style="margin-right: 16px;">{type_meta['sprout']['icon']} <b>{type_meta['sprout']['label']}</b> 真实世界的勇敢行动</span>
        <span>{type_meta['story']['icon']} <b>{type_meta['story']['label']}</b> 和安心童伴共创的故事</span>
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
                options=["star", "cloud", "sprout", "story"],
                format_func=lambda x: f"{type_meta[x]['icon']} {type_meta[x]['label']}",
            )
        with col_b:
            title = st.text_input("标题", placeholder="给这一刻起个名字…")

        if entry_type == "cloud":
            mood = st.select_slider("心情色", options=["blue", "pink", "gray", "yellow"], value="pink")
        else:
            mood = None

        if entry_type == "story":
            content_label = "故事预览（开头一段）"
            content_placeholder = "从前有一只小恐龙…"
        elif entry_type == "sprout":
            content_label = "你在真实世界里做了什么？"
            content_placeholder = "例如：今天我告诉了老师同学推我的事…"
        elif entry_type == "cloud":
            content_label = "当时是什么感受？"
            content_placeholder = "今天有点难过，因为…"
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
            # 勇敢芽只记录现实行动
            if entry_type == "sprout":
                ai_only_signals = ["和 ai 聊天", "和ai聊天", "跟 ai 聊", "跟ai聊", "ai 陪我", "ai陪我"]
                if any(s in content.lower() for s in ai_only_signals) and not any(
                    w in content for w in ["告诉", "说", "找", "主动", "和妈妈", "和爸爸", "老师", "同学"]
                ):
                    st.warning(
                        "勇敢芽是记录你在真实世界里的勇敢时刻哦——比如你今天告诉了老师一件事、"
                        "或者主动跟新同学说了话。要不要换成一颗好奇星或一朵心情云？"
                    )
                    st.stop()

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
all_entries = mm._flatten_planet(planet)  # 内部拍平函数
# 按日期倒序（粗略：用原始字符串排序后反转）
all_entries.reverse()

if not all_entries:
    st.info("你的小星球还是空的。点上面的「＋ 种下新东西」开始记录吧～")
else:
    # 用 columns 实现网格（每行 3 列）
    cols_per_row = 3
    for i in range(0, len(all_entries), cols_per_row):
        row = all_entries[i : i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, entry in zip(cols, row):
            with col:
                meta = type_meta.get(entry.get("type", "star"), type_meta["star"])
                title = entry.get("title", "（未命名）")
                date = entry.get("date", "")
                content = entry.get("content") or entry.get("preview") or ""
                tags = entry.get("tags", []) or []
                tags_html = "".join(
                    f'<span style="display:inline-block; padding:1px 8px; margin-right:4px; '
                    f'border-radius:9999px; background-color:rgba(28,28,28,0.04); '
                    f'font-size:11px; color:#5f5f5d;">{t}</span>'
                    for t in tags
                )
                st.markdown(
                    f"""
                    <div class="planet-card">
                        <div style="font-size: 22px;">{meta['icon']}</div>
                        <div style="font-weight: 600; margin: 4px 0 2px; font-size: 15px;">{title}</div>
                        <div class="meta" style="font-size: 12px; margin-bottom: 6px;">{meta['label']} · {date}</div>
                        <div style="font-size: 13px; color: #2c2c2c; line-height: 1.5;">
                            {(content[:80] + '…') if len(content) > 80 else content}
                        </div>
                        <div style="margin-top: 8px;">{tags_html}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                # 删除按钮（小、不显眼）
                if st.button("删除", key=f"del_{entry.get('id', '')}_{i}", help="删除这条条目"):
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
nav1, nav2, nav3, nav4 = st.columns(4)
with nav1:
    if st.button("💬 回到聊天", use_container_width=True):
        st.switch_page("pages/1_安心童伴.py")
with nav2:
    if st.button("🛡️ 安全引擎", use_container_width=True):
        st.switch_page("pages/3_安全引擎.py")
with nav3:
    if st.button("👨‍👩‍👧 家长守护", use_container_width=True):
        st.switch_page("pages/4_家长守护.py")
with nav4:
    if st.button("🧪 测试覆盖", use_container_width=True):
        st.switch_page("pages/5_测试覆盖.py")
