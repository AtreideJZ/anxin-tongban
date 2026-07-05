"""LLM 客户端封装

支持 OpenAI 兼容协议（DeepSeek / 通义 DashScope / 智谱 GLM 等）。
当未配置 API Key 时，自动回退到脚本化回复，保证 Demo 在无 Key 时也能跑通。

环境变量（按优先级自动探测）：
- 主回复 LLM：DEEPSEEK_API_KEY（DeepSeek）或 DASHSCOPE_API_KEY（通义千问）
- 轻量 LLM（风险分类/审计）：DASHSCOPE_API_KEY（通义千问）或 DEEPSEEK_API_KEY

可在 .streamlit/secrets.toml 或环境变量中配置：
    DEEPSEEK_API_KEY = "sk-..."
    DASHSCOPE_API_KEY = "sk-..."
    ANXIN_MAIN_MODEL = "deepseek-chat"        # 可选
    ANXIN_SMALL_MODEL = "qwen-turbo"          # 可选
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
# 模型配置
# ---------------------------------------------------------------------------
MAIN_PROVIDER_DEEPSEEK = "deepseek"
MAIN_PROVIDER_DASHSCOPE = "dashscope"


@dataclass
class ModelConfig:
    name: str           # 模型名
    base_url: str       # OpenAI 兼容 base_url
    api_key_env: str    # 读取 API Key 的环境变量名
    provider: str       # 标识


def _get_main_config() -> Optional[ModelConfig]:
    """探测主回复 LLM 配置"""
    # 优先 DeepSeek
    if os.environ.get("DEEPSEEK_API_KEY"):
        return ModelConfig(
            name=os.environ.get("ANXIN_MAIN_MODEL", "deepseek-chat"),
            base_url="https://api.deepseek.com/v1",
            api_key_env="DEEPSEEK_API_KEY",
            provider=MAIN_PROVIDER_DEEPSEEK,
        )
    # 其次通义 DashScope
    if os.environ.get("DASHSCOPE_API_KEY"):
        return ModelConfig(
            name=os.environ.get("ANXIN_MAIN_MODEL", "qwen-plus"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key_env="DASHSCOPE_API_KEY",
            provider=MAIN_PROVIDER_DASHSCOPE,
        )
    return None


def _get_small_config() -> Optional[ModelConfig]:
    """探测轻量 LLM 配置（风险分类/审计）"""
    if os.environ.get("DASHSCOPE_API_KEY"):
        return ModelConfig(
            name=os.environ.get("ANXIN_SMALL_MODEL", "qwen-turbo"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key_env="DASHSCOPE_API_KEY",
            provider=MAIN_PROVIDER_DASHSCOPE,
        )
    if os.environ.get("DEEPSEEK_API_KEY"):
        return ModelConfig(
            name=os.environ.get("ANXIN_SMALL_MODEL", "deepseek-chat"),
            base_url="https://api.deepseek.com/v1",
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
