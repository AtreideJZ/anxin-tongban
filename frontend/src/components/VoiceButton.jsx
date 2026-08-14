/* VoiceButton — 语音输入按钮（方案 4.7）
 * 浏览器不支持 SpeechRecognition 时返回 null（降级隐藏）
 * 识别结果通过 onResult 填入输入框
 */
import { useVoice } from "../hooks/useVoice";
import "./VoiceButton.css";

export default function VoiceButton({ onResult, disabled = false }) {
  const { supported, listening, toggleListen } = useVoice({ onResult });

  if (!supported) return null; // 不支持的浏览器直接隐藏按钮

  return (
    <button
      type="button"
      className={`voice-btn ${listening ? "voice-btn--listening" : ""}`}
      onClick={toggleListen}
      disabled={disabled}
      title={listening ? "正在听…再点一下停止" : "点我说话"}
      aria-label={listening ? "停止语音输入" : "开始语音输入"}
    >
      {listening ? "🎙️" : "🎤"}
    </button>
  );
}
