/* AiIdentityBadge — AI 身份标识（合规 4.8，常驻聊天页顶栏）
   分龄表述（v2.2）：低龄档温和简短；11 岁及以上明确"没有真实情感"，
   避免青少年产生情感投射（虚拟亲密关系红线） */
import "./AiIdentityBadge.css";

const BADGE_TEXTS = {
  "5-7": "我是 AI 伙伴，不是真人",
  "8-10": "我是 AI 伙伴，不是真人",
  "11-13": "我是 AI，不是真人，也没有真实情感",
  "14": "我是 AI，不是真人，也没有真实情感",
};

export default function AiIdentityBadge({ ageTier }) {
  const text = BADGE_TEXTS[ageTier] || BADGE_TEXTS["8-10"];
  return (
    <span className="ai-identity-badge" title="安心童伴是 AI 程序，不是真人">
      <span aria-hidden="true">🤖</span>
      {text}
    </span>
  );
}
