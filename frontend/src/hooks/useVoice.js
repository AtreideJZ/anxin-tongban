/* ============================================================
 * useVoice.js — Web Speech API 封装（方案 4.7）
 * 识别：webkitSpeechRecognition（Chrome/Edge），不支持则 supported=false → 按钮隐藏
 * 合成：speechSynthesis 中文播报
 * 备注：Demo 级方案（浏览器内置），正式版升级讯飞语音 SDK
 * ============================================================ */

import { useCallback, useEffect, useRef, useState } from "react";

const SpeechRecognitionCtor =
  typeof window !== "undefined" &&
  (window.SpeechRecognition || window.webkitSpeechRecognition);

export function useVoice({ onResult } = {}) {
  const supported = !!SpeechRecognitionCtor;
  const [listening, setListening] = useState(false);
  const recogRef = useRef(null);
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  useEffect(() => {
    if (!supported) return undefined;
    const recog = new SpeechRecognitionCtor();
    recog.lang = "zh-CN";
    recog.interimResults = false;
    recog.maxAlternatives = 1;

    recog.onresult = (e) => {
      const text = e.results?.[0]?.[0]?.transcript?.trim();
      if (text) onResultRef.current?.(text);
    };
    recog.onend = () => setListening(false);
    recog.onerror = () => setListening(false);
    recogRef.current = recog;

    return () => {
      try {
        recog.abort();
      } catch {
        /* 忽略 */
      }
    };
  }, [supported]);

  const toggleListen = useCallback(() => {
    if (!recogRef.current) return;
    if (listening) {
      recogRef.current.stop();
    } else {
      try {
        recogRef.current.start();
        setListening(true);
      } catch {
        setListening(false);
      }
    }
  }, [listening]);

  return { supported, listening, toggleListen };
}

/** 朗读一段文本（AI 回复播报）；返回停止函数 */
export function speak(text) {
  if (typeof window === "undefined" || !window.speechSynthesis) return () => {};
  window.speechSynthesis.cancel(); // 先停掉上一条，避免叠读
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = "zh-CN";
  utter.rate = 0.95; // 稍慢一点，孩子听得更清楚
  window.speechSynthesis.speak(utter);
  return () => window.speechSynthesis.cancel();
}

export function stopSpeaking() {
  if (typeof window !== "undefined" && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}
