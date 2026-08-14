/* ChatBubble — 聊天气泡
 * 用户气泡：--tint 微染，右侧
 * AI 气泡：奶油底 + 暖边框，左侧；下方挂"已安全检查"小徽章
 * 危机模板回复：温和样式（新芽绿暖边框），不做惊恐化 UI
 * 注意：不给孩子显示风险等级/决策链——那是家长端的事
 */
import { motion } from "framer-motion";
import RecommendationCard from "./RecommendationCard";
import DailyChallengeCard from "./DailyChallengeCard";
import "./ChatBubble.css";

export default function ChatBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <motion.div
      className={`bubble-row ${isUser ? "bubble-row--user" : "bubble-row--ai"}`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 380, damping: 30 }}
    >
      <div className="bubble-col">
        <div
          className={[
            "bubble",
            isUser ? "bubble--user" : "bubble--ai",
            message.crisis ? "bubble--crisis" : "",
          ]
            .join(" ")
            .trim()}
        >
          {message.content}
          {/* token 流式输出中的光标感小尾巴 */}
          {message.streamingTail && <span className="bubble-caret" />}
        </div>

        {/* 安全徽章：AI 气泡专属，审计通过后显示，绝不含风险等级 */}
        {!isUser && message.safetyChecked && (
          <div className="bubble-safety">
            <span aria-hidden="true">🛡️</span> 已安全检查
          </div>
        )}

        {/* done 事件后的增强卡片 */}
        {!isUser && message.recommendations?.length > 0 && (
          <RecommendationCard items={message.recommendations} />
        )}
        {!isUser && message.challenge?.text && (
          <DailyChallengeCard challenge={message.challenge} />
        )}
      </div>
    </motion.div>
  );
}
