/* ============================================================
 * useChat.js — 对话 hook：手工解析 SSE 伪流式（方案 4.5）
 *
 * 为什么不用 EventSource：EventSource 只支持 GET，/api/chat/send 是 POST，
 * 所以用 fetch + ReadableStream 自己按 SSE 协议解析（\n\n 分块，event:/data: 行）。
 *
 * 关键时序：服务端先跑完整 Pipeline（真实 LLM 约 5-15s）再回放事件，
 * 所以"发送 → 首个事件"之间必须有等待期 UI（waitingPhase）。
 *
 * 阶段机：idle → waiting（等首事件）→ processing（step 事件回放中）
 *        → streaming（token 打字机）→ idle（done）
 * ============================================================ */

import { useCallback, useRef, useState } from "react";
import { apiFetch, getToken } from "../utils/api";

let nextId = 1;
const genId = () => nextId++;

/** 解析一个 SSE 事件块，返回 {event, data} 或 null */
function parseEventBlock(block) {
  let event = "message";
  const dataLines = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return null;
  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return null;
  }
}

export function useChat({ onDone } = {}) {
  const [messages, setMessages] = useState([]);
  const [waitingPhase, setWaitingPhase] = useState("idle");
  const [historyLoaded, setHistoryLoaded] = useState(false);
  // 正在流式输出的那条 AI 消息 id（token 事件追加目标）
  const streamingIdRef = useRef(null);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  const streaming = waitingPhase !== "idle";

  /** 挂载时加载历史消息，返回 {usage_minutes} 供计时用 */
  const loadHistory = useCallback(async () => {
    const data = await apiFetch("/api/chat/history");
    const history = (data.messages || []).map((m) => ({
      id: genId(),
      role: m.role,
      content: m.content,
      ts: m.ts,
      safetyChecked: m.role === "assistant", // 历史 AI 回复均已过审计
    }));
    setMessages(history);
    setHistoryLoaded(true);
    return data;
  }, []);

  const sendMessage = useCallback(async (text) => {
    const content = text.trim();
    if (!content) return;

    // 1. 用户气泡立刻上屏
    const userMsg = { id: genId(), role: "user", content, ts: Date.now() };
    const aiId = genId();
    const aiMsg = {
      id: aiId,
      role: "assistant",
      content: "",
      ts: Date.now(),
      safetyChecked: false,
    };
    streamingIdRef.current = aiId;
    setMessages((prev) => [...prev, userMsg, aiMsg]);
    setWaitingPhase("waiting");

    const patchAi = (patch) =>
      setMessages((prev) =>
        prev.map((m) => (m.id === aiId ? { ...m, ...patch } : m))
      );

    try {
      const res = await fetch("/api/chat/send", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ message: content }),
      });
      if (!res.ok || !res.body) {
        throw new Error("网络出了点小问题，请再发一次试试");
      }

      // 2. 手工解析 SSE 流
      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let fullReply = ""; // 累计完整回复（TTS 播报等回调用）

      const handleEvent = ({ event, data }) => {
        if (event === "step") {
          // step 到达 → 悄悄推进提示阶段（不展示技术步骤名）
          setWaitingPhase((p) => (p === "waiting" ? "processing" : p));
        } else if (event === "token") {
          fullReply += data.text;
          setWaitingPhase("streaming");
          setMessages((prev) =>
            prev.map((m) =>
              m.id === aiId ? { ...m, content: m.content + data.text } : m
            )
          );
        } else if (event === "done") {
          patchAi({
            safetyChecked: true, // 审计已通过，可显示"已安全检查"徽章
            crisis: !!data.used_crisis_template, // 危机模板 → 温和样式
            recommendations: data.recommendations || [],
            challenge: data.challenge || null,
          });
          onDoneRef.current?.(data, fullReply);
        }
      };

      // 按 \n\n 分块；缓冲区末尾可能是不完整的半个事件，留给下一轮
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";
        for (const block of blocks) {
          const parsed = parseEventBlock(block);
          if (parsed) handleEvent(parsed);
        }
      }
      // 冲刷尾部残留
      const tail = parseEventBlock(buffer);
      if (tail) handleEvent(tail);
    } catch (err) {
      // 网络/解析失败：把 AI 气泡换成温和的错误文案，不惊吓孩子
      patchAi({
        content: "哎呀，信号好像迷路了……请再发一次试试好吗？",
        safetyChecked: false,
        failed: true,
      });
      if (import.meta.env.DEV) console.error("[useChat] send failed:", err);
    } finally {
      streamingIdRef.current = null;
      setWaitingPhase("idle");
    }
  }, []);

  return {
    messages,
    waitingPhase,
    streaming,
    historyLoaded,
    loadHistory,
    sendMessage,
  };
}
