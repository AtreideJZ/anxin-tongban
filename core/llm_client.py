"""LLM 客户端封装 — DeepSeek 单供应商，双模型分工

主回复（Step 5）：deepseek-v4-pro（流式，高质量生成）
轻量任务（Step 2 分类 / Step 6 审计 / 情节摘要）：deepseek-chat（非流式，快而省）

无 API Key 时自动回退到脚本化回复，保证 Demo 在无 Key 时也能跑通。

环境变量（FastAPI 后端由 config.py 加载项目根 .env）：
    DEEPSEEK_API_KEY = "sk-..."
    ANXIN_MAIN_MODEL = "deepseek-v4-pro"   # 可选，主回复模型
    ANXIN_SMALL_MODEL = "deepseek-chat"     # 可选，轻量任务模型
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterator, Optional, AsyncIterator

try:
    from openai import OpenAI  # type: ignore
    _OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore
    _OPENAI_AVAILABLE = False


# ---------------------------------------------------------------------------
# 模型配置
# ---------------------------------------------------------------------------
PROVIDER = "deepseek"

# 默认模型名
DEFAULT_MAIN_MODEL = "deepseek-v4-pro"   # 主回复：最高质量
DEFAULT_SMALL_MODEL = "deepseek-chat"    # 轻量任务：分类/审计/摘要，快而省

# OpenAI 兼容 base_url
BASE_URL = "https://api.deepseek.com/v1"


@dataclass
class ModelConfig:
    name: str           # 模型名
    base_url: str       # OpenAI 兼容 base_url
    api_key_env: str    # 读取 API Key 的环境变量名


def _get_main_config() -> Optional[ModelConfig]:
    """主回复 LLM 配置"""
    if os.environ.get("DEEPSEEK_API_KEY"):
        return ModelConfig(
            name=os.environ.get("ANXIN_MAIN_MODEL", DEFAULT_MAIN_MODEL),
            base_url=BASE_URL,
            api_key_env="DEEPSEEK_API_KEY",
        )
    return None


def _get_small_config() -> Optional[ModelConfig]:
    """轻量 LLM 配置（与主回复同 Key，不同模型名）"""
    if os.environ.get("DEEPSEEK_API_KEY"):
        return ModelConfig(
            name=os.environ.get("ANXIN_SMALL_MODEL", DEFAULT_SMALL_MODEL),
            base_url=BASE_URL,
            api_key_env="DEEPSEEK_API_KEY",
        )
    return None


def is_llm_available() -> bool:
    """是否配置了可用的 LLM API Key"""
    return os.environ.get("DEEPSEEK_API_KEY", "") != ""


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
    """主回复 LLM 流式调用（Step 5）

    Yields:
        逐 token 字符串
    Raises:
        RuntimeError: 当 LLM 不可用时
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
    """轻量 LLM 非流式调用（Step 2 分类 / Step 6 审计 / 情节摘要）

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


# ---------------------------------------------------------------------------
# 异步 LLM 调用（用于 async Pipeline）
# ---------------------------------------------------------------------------
def _make_async_client(cfg: ModelConfig):
    """创建 AsyncOpenAI 客户端"""
    if not _OPENAI_AVAILABLE:
        return None
    api_key = os.environ.get(cfg.api_key_env, "")
    if not api_key:
        return None
    try:
        from openai import AsyncOpenAI  # type: ignore
    except ImportError:
        return None
    return AsyncOpenAI(api_key=api_key, base_url=cfg.base_url)


async def chat_stream_async(messages: list[dict]) -> "AsyncIterator[str]":
    """异步流式调用主回复 LLM"""
    cfg = _get_main_config()
    if cfg is None:
        raise RuntimeError("LLM_UNAVAILABLE")
    client = _make_async_client(cfg)
    if client is None:
        raise RuntimeError("LLM_UNAVAILABLE")

    response = await client.chat.completions.create(
        model=cfg.name,
        messages=messages,
        stream=True,
        temperature=0.7,
    )
    async for chunk in response:
        try:
            token = chunk.choices[0].delta.content
        except (AttributeError, IndexError):
            token = None
        if token:
            yield token


async def chat_complete_async(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 400,
) -> str:
    """异步非流式调用轻量 LLM"""
    cfg = _get_small_config() or _get_main_config()
    if cfg is None:
        raise RuntimeError("LLM_UNAVAILABLE")
    client = _make_async_client(cfg)
    if client is None:
        raise RuntimeError("LLM_UNAVAILABLE")

    response = await client.chat.completions.create(
        model=cfg.name,
        messages=messages,
        stream=False,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()
