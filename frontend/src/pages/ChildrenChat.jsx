/* ChildrenChat — 儿童端统一聊天页（本阶段核心）
 *
 * 组成：
 * - 顶栏：产品名 + AiIdentityBadge（合规 4.8）+ 使用时长 + 星球入口 + 退出
 * - 消息流：ChatBubble（用户右/AI 左 + "已安全检查"徽章）
 * - 等待期 UI：发送 → 首个 SSE 事件可能 5-15s，显示 SafetyShield 呼吸动画
 * - 输入区：大圆角多行输入（Enter 发送 / Shift+Enter 换行）+ 发送 pill
 *   + VoiceButton（语音识别）+ TTS 播报开关
 * - useUsageTimer：本次时长显示 + 累计 120 分钟温暖提醒（可关闭，不强制锁）
 */
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "../hooks/useAuth";
import { useChat } from "../hooks/useChat";
import { useUsageTimer } from "../hooks/useUsageTimer";
import { speak, stopSpeaking } from "../hooks/useVoice";
import { apiFetch } from "../utils/api";
import ChatBubble from "../components/ChatBubble";
import SafetyShield from "../components/SafetyShield";
import VoiceButton from "../components/VoiceButton";
import AiIdentityBadge from "../components/AiIdentityBadge";
import PillButton from "../components/PillButton";
import "./ChildrenChat.css";

export default function ChildrenChat() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const [initialMinutes, setInitialMinutes] = useState(0);
  const [ttsOn, setTtsOn] = useState(false);
  const [topicCard, setTopicCard] = useState(null); // 亲子话题卡（v2.2 B）
  const [topicLoading, setTopicLoading] = useState(false);
  const ttsOnRef = useRef(false);
  const scrollRef = useRef(null);

  // done 后按开关自动播报完整回复（方案 4.7）
  const { messages, waitingPhase, streaming, historyLoaded, loadHistory, sendMessage } =
    useChat({
      onDone: (_data, fullReply) => {
        if (ttsOnRef.current && fullReply) speak(fullReply);
      },
    });

  const { sessionMinutes, showReminder, dismissReminder } =
    useUsageTimer(initialMinutes);

  // 挂载时加载历史消息 + 累计使用时长
  useEffect(() => {
    loadHistory()
      .then((data) => setInitialMinutes(data.usage_minutes || 0))
      .catch(() => {});
  }, [loadHistory]);

  // 平滑滚动到底部（新消息 / 阶段变化时）
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, waitingPhase]);

  ttsOnRef.current = ttsOn;

  const handleSend = () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    sendMessage(text);
  };

  const handleKeyDown = (e) => {
    // Enter 发送，Shift+Enter 换行
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleLogout = () => {
    stopSpeaking();
    logout();
    navigate("/", { replace: true });
  };

  const toggleTts = () => {
    setTtsOn((on) => {
      if (on) stopSpeaking(); // 关闭时停掉当前播报
      return !on;
    });
  };

  // 亲子话题卡（v2.2 B）：独立端点，不走 chat/send，不计入使用时长
  const fetchTopic = async () => {
    if (topicLoading) return;
    setTopicLoading(true);
    try {
      const data = await apiFetch("/api/cocreation/topic", { method: "POST" });
      setTopicCard(data);
    } catch {
      setTopicCard({
        topic: "去问问爸爸妈妈「今天过得怎么样」吧，也讲讲你自己的今天！",
      });
    } finally {
      setTopicLoading(false);
    }
  };

  // 正在流式输出的 AI 气泡 id（打字机小尾巴）
  const lastMsg = messages[messages.length - 1];
  const streamingId =
    waitingPhase === "streaming" && lastMsg?.role === "assistant"
      ? lastMsg.id
      : null;

  return (
    <div className="chat-page track-child">
      {/* ---- 顶栏 ---- */}
      <header className="chat-header">
        <div className="chat-brand">
          <span aria-hidden="true">🪐</span>
          <span className="chat-brand-name">安心童伴</span>
        </div>
        <AiIdentityBadge ageTier={user?.age_tier} />
        <div className="chat-header-right">
          <span className="chat-usage" title="本次连续聊天时长">
            ⏱️ 本次 <span className="num">{sessionMinutes}</span> 分钟
          </span>
          <Link to="/home" className="chat-planet-link">
            🏠 主页
          </Link>
          <Link to="/planet" className="chat-planet-link">
            🌍 我的小星球
          </Link>
          <button className="chat-logout" onClick={handleLogout}>
            退出
          </button>
        </div>
      </header>

      {/* ---- 消息流 ---- */}
      <main className="chat-scroll" ref={scrollRef}>
        <div className="chat-flow">
          {historyLoaded && messages.length === 0 && (
            <div className="chat-empty">
              <div className="chat-empty-emoji" aria-hidden="true">
                👋
              </div>
              <p>
                你好呀{user?.username ? `，${user.username}` : ""}！
                <br />
                想聊点什么？开心的、奇怪的、想问的，都可以告诉我～
              </p>
            </div>
          )}

          {messages.map((m) => (
            <ChatBubble
              key={m.id}
              message={{ ...m, streamingTail: m.id === streamingId }}
            />
          ))}

          {/* 等待期：呼吸盾牌 + 轮换提示（首事件可能 5-15s 后才到） */}
          {(waitingPhase === "waiting" || waitingPhase === "processing") && (
            <SafetyShield phase={waitingPhase} />
          )}
        </div>
      </main>

      {/* ---- 输入区 ---- */}
      <footer className="chat-input-bar">
        {/* 亲子话题卡（v2.2 B）：孩子拿着话题去和爸爸妈妈当面聊 */}
        <AnimatePresence>
          {topicCard && (
            <motion.div
              className="topic-card"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ type: "spring", stiffness: 300, damping: 26 }}
            >
              <div className="topic-card-title">💬 拿去和爸爸妈妈聊聊吧</div>
              <p className="topic-card-text">{topicCard.topic}</p>
              <div className="topic-card-actions">
                <button
                  type="button"
                  className="topic-card-btn"
                  onClick={fetchTopic}
                  disabled={topicLoading}
                >
                  {topicLoading ? "想一下…" : "🔄 换一个"}
                </button>
                <button
                  type="button"
                  className="topic-card-btn"
                  onClick={() => setTopicCard(null)}
                >
                  收起
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="说点什么吧…（Enter 发送，Shift+Enter 换行）"
          rows={2}
          disabled={streaming}
        />
        <div className="chat-input-actions">
          <button
            type="button"
            className="topic-toggle"
            onClick={fetchTopic}
            disabled={topicLoading}
            title="想和爸爸妈妈聊点什么？"
            aria-label="生成一个亲子话题"
          >
            💬
          </button>
          <VoiceButton
            onResult={(text) => setInput((prev) => (prev ? prev + " " + text : text))}
            disabled={streaming}
          />
          <button
            type="button"
            className={`tts-toggle ${ttsOn ? "tts-toggle--on" : ""}`}
            onClick={toggleTts}
            title={ttsOn ? "关闭朗读" : "让安心童伴读给我听"}
            aria-label={ttsOn ? "关闭语音播报" : "开启语音播报"}
          >
            {ttsOn ? "🔊" : "🔇"}
          </button>
          <PillButton
            onClick={handleSend}
            disabled={!input.trim() || streaming}
            className="chat-send"
          >
            发送
          </PillButton>
        </div>
      </footer>

      {/* ---- 2 小时温暖提醒（合规 4.8，可关闭，不强制锁） ---- */}
      <AnimatePresence>
        {showReminder && (
          <motion.div
            className="reminder-mask"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="reminder-dialog card"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ type: "spring", stiffness: 320, damping: 26 }}
              role="dialog"
              aria-modal="true"
            >
              <div className="reminder-emoji" aria-hidden="true">
                🌳
              </div>
              <h2 className="reminder-title">已经聊了 2 小时啦</h2>
              <p className="reminder-text">
                起来活动一下眼睛和身体吧～喝口水、看看窗外，
                <br />
                安心童伴会一直在这里等你回来。
              </p>
              <PillButton onClick={dismissReminder}>知道啦</PillButton>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
