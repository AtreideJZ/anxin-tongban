"""语音互动模块 (Voice Interaction)

语音输入：st.audio_input → faster-whisper 本地 STT → 文本送入 Pipeline
语音输出：LLM 文本回复 → 可选 TTS 语音播报

技术选型：
- STT (Demo): faster-whisper small 模型，本地推理，<2s 延迟，零 API 依赖
- STT (正式版): 讯飞语音听写 SDK（儿童声学优化）
- TTS: Web Speech API（浏览器内置，零成本）

隐私设计：语音数据本地处理，不离开设备。
"""
from __future__ import annotations

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# faster-whisper 集成（可选依赖）
# ---------------------------------------------------------------------------
_whisper_model = None
_whisper_available: Optional[bool] = None  # None = 未检测, True/False = 已知


def is_whisper_available() -> bool:
    """检测 faster-whisper 是否可用"""
    global _whisper_available
    if _whisper_available is not None:
        return _whisper_available
    try:
        import faster_whisper  # noqa: F401
        _whisper_available = True
    except ImportError:
        _whisper_available = False
    return _whisper_available


def _get_model():
    """延迟加载 whisper 模型（首次调用时加载）"""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    if not is_whisper_available():
        return None
    try:
        from faster_whisper import WhisperModel
        # small 模型：~400MB，CPU 推理 <2s，中文优化
        _whisper_model = WhisperModel(
            "small",
            device="cpu",
            compute_type="int8",  # 量化加速
        )
        logger.info("faster-whisper small model loaded successfully")
    except Exception as e:
        logger.warning(f"Failed to load faster-whisper model: {e}")
        _whisper_available = False
        return None
    return _whisper_model


def transcribe(audio_bytes: bytes, language: str = "zh") -> Optional[str]:
    """将音频字节流转写为文本

    Args:
        audio_bytes: WAV 格式的音频数据
        language: 语言代码，默认 "zh"

    Returns:
        转写文本，若失败则返回 None
    """
    model = _get_model()
    if model is None:
        return None

    try:
        audio_io = io.BytesIO(audio_bytes)
        segments, _ = model.transcribe(
            audio_io,
            language=language,
            beam_size=5,
            vad_filter=True,  # 过滤静音段
        )
        text_parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        if not text_parts:
            return None
        return "".join(text_parts)
    except Exception as e:
        logger.warning(f"Whisper transcription failed: {e}")
        return None


# ---------------------------------------------------------------------------
# TTS 输出（Web Speech API — 客户端 JS）
# ---------------------------------------------------------------------------
def get_tts_html(text: str) -> str:
    """生成 TTS 播报的 HTML/JS 代码

    在 Streamlit 中通过 st.markdown(..., unsafe_allow_html=True) 注入。
    使用浏览器内置 Web Speech API，零成本，跨平台。

    Args:
        text: 要播报的文本（自动截断至 500 字）

    Returns:
        HTML + JS 代码片段
    """
    # 清理文本中的特殊字符，防止 JS 注入
    safe_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
    # 截断过长文本
    if len(safe_text) > 500:
        safe_text = safe_text[:500] + "……"

    return f"""
    <div id="tts-container" style="margin: 4px 0 8px;">
        <button onclick="speakText()" style="
            padding: 4px 12px;
            border: 1px solid #7BB76E;
            border-radius: 9999px;
            background: transparent;
            color: #7BB76E;
            font-size: 12px;
            cursor: pointer;
            font-family: inherit;
        " title="使用浏览器语音播报">🔊 听一听</button>
    </div>
    <script>
    function speakText() {{
        if (window.speechSynthesis.speaking) {{
            window.speechSynthesis.cancel();
            return;
        }}
        const utterance = new SpeechSynthesisUtterance('{safe_text}');
        utterance.lang = 'zh-CN';
        utterance.rate = 0.9;  // 稍慢，适合儿童
        utterance.pitch = 1.1; // 稍高，更友好
        window.speechSynthesis.speak(utterance);
    }}
    </script>
    """


# ---------------------------------------------------------------------------
# 语音输入状态
# ---------------------------------------------------------------------------
def get_voice_input_status_text() -> str:
    """返回语音输入的当前状态文本（供 UI 提示）"""
    if is_whisper_available():
        return "🎤 语音输入就绪（faster-whisper 本地识别）"
    else:
        return "📝 文字输入（安装 faster-whisper 可启用语音：pip install faster-whisper）"
