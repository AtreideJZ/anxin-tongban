"""session_state 统一管理

封装对各页面共享状态的读写，避免散落的字符串 key 出错。
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import streamlit as st


# ---------------------------------------------------------------------------
# 默认值
# ---------------------------------------------------------------------------
DEFAULT_AGE_TIER = "8-11"
DEFAULT_MODE = "chat"

_PLANET_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "planet.json")
_STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "session_state.json")

# 部署环境检测：Streamlit Cloud 是多用户共享容器，
# 基于文件的持久化会把 A 用户的聊天暴露给 B 用户，因此禁用。
# 本地开发时保留文件持久化，方便调试。
def _is_deployed() -> bool:
    """检测当前是否在 Streamlit Cloud 部署环境

    判据（任一满足即视为部署环境）：
    1. STREAMLIT_SHARING_MODE 环境变量（Streamlit Cloud 官方标识）
    2. STREAMLIT_SERVER_HEADLESS=true（Streamlit Cloud 启动方式）
    3. HOME 目录以 /home/appuser 开头（Streamlit Cloud 容器约定）
    4. 存在 /app/<repo-name> 路径（Streamlit Cloud 工作目录）
    """
    if os.environ.get("STREAMLIT_SHARING_MODE", ""):
        return True
    if os.environ.get("STREAMLIT_SERVER_HEADLESS", "").lower() == "true":
        return True
    home = os.path.expanduser("~")
    if home.startswith("/home/appuser"):
        return True
    if os.path.isdir("/app"):
        return True
    return False


_PERSISTENCE_ENABLED = not _is_deployed()


def _cleanup_deployed_state_file() -> None:
    """部署环境启动时清理残留的 session_state.json

    防止旧版本代码写入的文件被新版本意外读到。
    """
    if not _PERSISTENCE_ENABLED:
        try:
            if os.path.exists(_STATE_FILE):
                os.remove(_STATE_FILE)
        except Exception:
            pass


_cleanup_deployed_state_file()


def _load_default_planet() -> dict:
    try:
        with open(_PLANET_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"stars": [], "clouds": [], "sprouts": [], "stories": []}


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------
def init_state() -> None:
    """初始化所有 session_state 字段（幂等）"""
    if "age_tier" not in st.session_state:
        st.session_state.age_tier = DEFAULT_AGE_TIER
    if "mode" not in st.session_state:
        st.session_state.mode = DEFAULT_MODE
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # [{role: "user"|"assistant", content}]
    if "planet" not in st.session_state:
        st.session_state.planet = _load_default_planet()
    if "pipeline_runs" not in st.session_state:
        # 全部历史 Pipeline 运行结果（最近在前）
        st.session_state.pipeline_runs = []
    if "latest_pipeline" not in st.session_state:
        st.session_state.latest_pipeline = None
    if "parent_alerts" not in st.session_state:
        # 家长端风险提醒列表 [{time, topic, risk_level, summary, suggestion}]
        st.session_state.parent_alerts = []
    if "parent_summary" not in st.session_state:
        st.session_state.parent_summary = None
    if "conversation_topics" not in st.session_state:
        # 当日对话主题统计 [{topic, mode, risk_level}]
        st.session_state.conversation_topics = []
    if "session_start_time" not in st.session_state:
        import time
        st.session_state.session_start_time = time.time()
    if "usage_minutes" not in st.session_state:
        st.session_state.usage_minutes = 18  # 模拟初始值
    if "parent_consent_given" not in st.session_state:
        st.session_state.parent_consent_given = False
    if "topic_preferences" not in st.session_state:
        st.session_state.topic_preferences = {
            "allowed": ["故事", "百科", "学习", "情绪", "安全教育"],
            "limited": ["游戏", "消费"],
            "forbidden": ["暴力", "色情", "自伤", "危险操作"],
        }

    # 从磁盘恢复持久化状态（仅首次初始化时加载一次）
    # 部署环境下禁用文件持久化，避免不同用户的数据互相污染
    if not st.session_state.get("_state_loaded", False):
        if _PERSISTENCE_ENABLED:
            load_state()
        st.session_state._state_loaded = True


# ---------------------------------------------------------------------------
# 数据持久化（JSON 文件）
# ---------------------------------------------------------------------------
def save_state() -> None:
    """将关键 session_state 保存到 JSON 文件，刷新后可恢复

    部署环境下禁用（多用户共享容器，文件持久化无意义）。
    """
    if not _PERSISTENCE_ENABLED:
        return
    data = {
        "chat_history": st.session_state.get("chat_history", []),
        "planet": st.session_state.get("planet", {}),
        "parent_alerts": st.session_state.get("parent_alerts", []),
        "conversation_topics": st.session_state.get("conversation_topics", []),
        "usage_minutes": st.session_state.get("usage_minutes", 0),
        "age_tier": st.session_state.get("age_tier", DEFAULT_AGE_TIER),
        "mode": st.session_state.get("mode", DEFAULT_MODE),
        "parent_consent_given": st.session_state.get("parent_consent_given", False),
        "topic_preferences": st.session_state.get("topic_preferences", {}),
    }
    try:
        os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 持久化失败不应影响主流程


def load_state() -> None:
    """从 JSON 文件恢复状态到 session_state"""
    if not os.path.exists(_STATE_FILE):
        return
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in data.items():
            st.session_state[key] = value
    except Exception:
        pass


def clear_saved_state() -> None:
    """清除持久化文件（重置 Demo 时用）"""
    try:
        if os.path.exists(_STATE_FILE):
            os.remove(_STATE_FILE)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 读写
# ---------------------------------------------------------------------------
def get_age_tier() -> str:
    return st.session_state.get("age_tier", DEFAULT_AGE_TIER)


def set_age_tier(v: str) -> None:
    st.session_state.age_tier = v


def get_mode() -> str:
    return st.session_state.get("mode", DEFAULT_MODE)


def set_mode(v: str) -> None:
    st.session_state.mode = v


def get_chat_history() -> list[dict]:
    return st.session_state.get("chat_history", [])


def append_chat(role: str, content: str) -> None:
    st.session_state.chat_history.append({"role": role, "content": content})


def clear_chat() -> None:
    st.session_state.chat_history = []


def get_planet() -> dict:
    return st.session_state.get("planet", {})


def set_planet(p: dict) -> None:
    st.session_state.planet = p
    save_state()


def get_latest_pipeline():
    return st.session_state.get("latest_pipeline")


def get_all_pipeline_runs() -> list:
    return st.session_state.get("pipeline_runs", [])


def record_pipeline_run(result) -> None:
    """记录一次 Pipeline 运行，更新 latest / history / 家长提醒 / 主题统计"""
    st.session_state.latest_pipeline = result
    runs = st.session_state.get("pipeline_runs", [])
    runs.insert(0, result)
    # 只保留最近 20 次
    st.session_state.pipeline_runs = runs[:20]

    # 家长风险提醒
    if result.parent_alert:
        from datetime import datetime
        st.session_state.parent_alerts.insert(0, {
            "time": datetime.now().strftime("%H:%M"),
            "topic": result.topic,
            "risk_level": result.risk_level,
            "summary": _summarize_alert(result),
            "suggestion": _suggest_for_parent(result),
        })

    # 主题统计
    st.session_state.conversation_topics.append({
        "topic": result.topic,
        "risk_level": result.risk_level,
        "strategy": result.strategy,
    })

    # 使用时长累加（粗略模拟：每次 +1 分钟）
    st.session_state.usage_minutes = st.session_state.get("usage_minutes", 0) + 1

    save_state()


def _summarize_alert(result) -> str:
    """根据 topic 生成家长提醒摘要（不展示原文）"""
    summaries = {
        "privacy_leak": "孩子在与陌生网友对话中提到要分享家庭地址，已由安心童伴温和引导不要告知，建议您以轻松方式跟孩子聊聊网络安全。",
        "school_bullying": "孩子提到有同学推搡并要求不要告诉老师，已由安心童伴鼓励 TA 找可信任的成年人，建议您关心孩子在学校的人际关系。",
        "self_harm": "检测到孩子可能存在高风险情绪表达，已使用预置危机模板引导孩子联系家人或拨打 12355，请立即关注。",
        "ai_dependency": "孩子表现出对 AI 的明显依赖，已由安心童伴引导现实人际连接，建议您增加与孩子的现实陪伴。",
        "inappropriate_content": "孩子输入涉及不适龄内容，已由安心童伴拦截并引导，建议关注孩子的内容接触来源。",
    }
    return summaries.get(result.topic, "检测到一次风险事件，已由安心童伴处理，建议关注。")


def _suggest_for_parent(result) -> str:
    suggestions = {
        "privacy_leak": "以轻松的方式跟孩子聊聊：网上有哪些信息不能随便告诉别人？",
        "school_bullying": "用关心的语气问：最近在学校和同学相处怎么样？有没有什么让你不舒服的事？",
        "self_harm": "🚨 立即与孩子沟通。如需专业心理援助，请拨打 12355 青少年服务热线或联系学校心理老师。安心童伴已在儿童端引导孩子联系家人或拨打 12355。",
        "ai_dependency": "增加陪伴时间，与孩子一起做一些现实中的活动。",
        "inappropriate_content": "了解孩子最近接触的内容来源，做适当引导。",
    }
    return suggestions.get(result.topic, "找机会与孩子聊聊这件事。")


def get_parent_alerts() -> list:
    return st.session_state.get("parent_alerts", [])


def get_conversation_topics() -> list:
    return st.session_state.get("conversation_topics", [])


def get_usage_minutes() -> int:
    return st.session_state.get("usage_minutes", 0)


def is_parent_consent_given() -> bool:
    return st.session_state.get("parent_consent_given", False)


def set_parent_consent(v: bool) -> None:
    st.session_state.parent_consent_given = v
    save_state()


def get_topic_preferences() -> dict:
    """获取家长话题偏好设置

    返回 {"allowed": [...], "limited": [...], "forbidden": [...]}
    """
    default = {
        "allowed": ["故事", "百科", "学习", "情绪", "安全教育"],
        "limited": ["游戏", "消费"],
        "forbidden": ["暴力", "色情", "自伤", "危险操作"],
    }
    prefs = st.session_state.get("topic_preferences")
    if not prefs or not isinstance(prefs, dict):
        return default
    # 补齐缺失的 key（向后兼容）
    for k, v in default.items():
        if k not in prefs:
            prefs[k] = v
    return prefs


def set_topic_preferences(prefs: dict) -> None:
    st.session_state.topic_preferences = prefs
    save_state()


def get(key: str, default: Any = None) -> Any:
    return st.session_state.get(key, default)


def set(key: str, value: Any) -> None:
    st.session_state[key] = value
