"""LLM 客户端封装

支持 OpenAI 兼容协议（DeepSeek 官方 / 硅基流动 SiliconFlow 等）。
当未配置 API Key 时，自动回退到脚本化回复，保证 Demo 在无 Key 时也能跑通。

环境变量（按优先级自动探测）：
- 主回复 LLM：DEEPSEEK_API_KEY（DeepSeek v4-pro）或 SILICONFLOW_API_KEY（MiniMax-M2.5）
- 轻量 LLM（风险分类/审计）：SILICONFLOW_API_KEY（MiniMax-M2.5）或 DEEPSEEK_API_KEY（v4-flash）

可在 .streamlit/secrets.toml 或环境变量中配置：
    DEEPSEEK_API_KEY = "sk-..."
    SILICONFLOW_API_KEY = "sk-..."
    ANXIN_MAIN_MODEL = "deepseek-v4-pro"             # 可选
    ANXIN_SMALL_MODEL = "Pro/MiniMaxAI/MiniMax-M2.5" # 可选
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterator, Optional

try:
    from openai import OpenAI  # type: ignore
    _OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore
    _OPENAI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Secrets 同步：把 st.secrets / .streamlit/secrets.toml 的值同步到 os.environ
# 这样代码用 os.environ.get() 就能读到 secrets.toml 里的配置，
# 同时兼容 Streamlit Cloud（Cloud 也会注入 os.environ）和本地环境变量。
# ---------------------------------------------------------------------------
_SECRET_KEYS = (
    "DEEPSEEK_API_KEY",
    "SILICONFLOW_API_KEY",
    "ANXIN_MAIN_MODEL",
    "ANXIN_SMALL_MODEL",
)


def _sync_secrets_to_environ() -> None:
    """把 st.secrets 里的配置同步到 os.environ（覆盖已有的环境变量）

    Demo 项目约定：secrets.toml 是项目级配置，优先于系统环境变量。
    这样开发机上的旧环境变量不会干扰项目配置。
    """
    try:
        import streamlit as st  # type: ignore
        secrets = st.secrets
    except Exception:
        return
    for key in _SECRET_KEYS:
        try:
            val = secrets[key]
        except (KeyError, AttributeError):
            continue
        if val:
            os.environ[key] = str(val)


_sync_secrets_to_environ()


# ---------------------------------------------------------------------------
# 模型配置
# ---------------------------------------------------------------------------
MAIN_PROVIDER_DEEPSEEK = "deepseek"
MAIN_PROVIDER_SILICONFLOW = "siliconflow"

# 默认模型名
DEFAULT_MAIN_MODEL_DEEPSEEK = "deepseek-v4-pro"
DEFAULT_MAIN_MODEL_SILICONFLOW = "Pro/MiniMaxAI/MiniMax-M2.5"
DEFAULT_SMALL_MODEL_SILICONFLOW = "Pro/MiniMaxAI/MiniMax-M2.5"
DEFAULT_SMALL_MODEL_DEEPSEEK = "deepseek-v4-flash"

# OpenAI 兼容 base_url
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"


@dataclass
class ModelConfig:
    name: str           # 模型名
    base_url: str       # OpenAI 兼容 base_url
    api_key_env: str    # 读取 API Key 的环境变量名
    provider: str       # 标识


def _get_main_config() -> Optional[ModelConfig]:
    """探测主回复 LLM 配置（优先 DeepSeek，质量更好）"""
    # 优先 DeepSeek 官方
    if os.environ.get("DEEPSEEK_API_KEY"):
        return ModelConfig(
            name=os.environ.get("ANXIN_MAIN_MODEL", DEFAULT_MAIN_MODEL_DEEPSEEK),
            base_url=DEEPSEEK_BASE_URL,
            api_key_env="DEEPSEEK_API_KEY",
            provider=MAIN_PROVIDER_DEEPSEEK,
        )
    # 其次硅基流动 SiliconFlow（MiniMax-M2.5）
    if os.environ.get("SILICONFLOW_API_KEY"):
        return ModelConfig(
            name=os.environ.get("ANXIN_MAIN_MODEL", DEFAULT_MAIN_MODEL_SILICONFLOW),
            base_url=SILICONFLOW_BASE_URL,
            api_key_env="SILICONFLOW_API_KEY",
            provider=MAIN_PROVIDER_SILICONFLOW,
        )
    return None


def _get_small_config() -> Optional[ModelConfig]:
    """探测轻量 LLM 配置（优先硅基流动，更快更省）"""
    # 优先硅基流动 SiliconFlow（MiniMax-M2.5）
    if os.environ.get("SILICONFLOW_API_KEY"):
        return ModelConfig(
            name=os.environ.get("ANXIN_SMALL_MODEL", DEFAULT_SMALL_MODEL_SILICONFLOW),
            base_url=SILICONFLOW_BASE_URL,
            api_key_env="SILICONFLOW_API_KEY",
            provider=MAIN_PROVIDER_SILICONFLOW,
        )
    # 其次 DeepSeek 官方（v4-flash 轻量版）
    if os.environ.get("DEEPSEEK_API_KEY"):
        return ModelConfig(
            name=os.environ.get("ANXIN_SMALL_MODEL", DEFAULT_SMALL_MODEL_DEEPSEEK),
            base_url=DEEPSEEK_BASE_URL,
            api_key_env="DEEPSEEK_API_KEY",
            provider=MAIN_PROVIDER_DEEPSEEK,
        )
    return None


def is_llm_available() -> bool:
    """是否配置了可用的 LLM API Key"""
    return _get_main_config() is not None


def _make_client(cfg: ModelConfig):
    if not _OPENAI_AVAILABLE:
        return None
    api_key = os.environ.get(cfg.api_key_env, "")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=cfg.base_url)


# ---------------------------------------------------------------------------
# 主回复 LLM 调用
# ---------------------------------------------------------------------------
def chat_stream(messages: list[dict]) -> Iterator[str]:
    """主回复 LLM 流式调用

    Yields:
        逐 token 字符串
    Raises:
        RuntimeError: 当 LLM 不可用且未提供 fallback 时
    """
    cfg = _get_main_config()
    if cfg is None:
        raise RuntimeError("LLM_UNAVAILABLE")
    client = _make_client(cfg)
    if client is None:
        raise RuntimeError("LLM_UNAVAILABLE")

    response = client.chat.completions.create(
        model=cfg.name,
        messages=messages,
        stream=True,
        temperature=0.7,
    )
    for chunk in response:
        try:
            token = chunk.choices[0].delta.content
        except (AttributeError, IndexError):
            token = None
        if token:
            yield token


def chat_complete(messages: list[dict], temperature: float = 0.3, max_tokens: int = 400) -> str:
    """轻量 LLM 非流式调用，用于风险分类/审计等

    Returns:
        完整回复字符串
    """
    cfg = _get_small_config() or _get_main_config()
    if cfg is None:
        raise RuntimeError("LLM_UNAVAILABLE")
    client = _make_client(cfg)
    if client is None:
        raise RuntimeError("LLM_UNAVAILABLE")

    response = client.chat.completions.create(
        model=cfg.name,
        messages=messages,
        stream=False,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


def get_main_model_name() -> str:
    cfg = _get_main_config()
    return cfg.name if cfg else "本地脚本模式（无 API Key）"


def get_small_model_name() -> str:
    cfg = _get_small_config() or _get_main_config()
    return cfg.name if cfg else "本地脚本模式（无 API Key）"
