/* DailyChallengeCard — 每日挑战卡片（done 事件或今日挑战接口数据） */
import "./DailyChallengeCard.css";

const TYPE_LABEL = {
  kindness: "暖心挑战",
  courage: "勇气挑战",
  curiosity: "好奇挑战",
  creativity: "创意挑战",
};

export default function DailyChallengeCard({ challenge }) {
  if (!challenge?.text) return null;
  return (
    <div className="challenge-card">
      <div className="challenge-head">
        <span aria-hidden="true">🌱</span>
        <span className="challenge-title">今日小挑战</span>
        {challenge.type && (
          <span className="challenge-type">
            {TYPE_LABEL[challenge.type] || "小小挑战"}
          </span>
        )}
      </div>
      <p className="challenge-text">{challenge.text}</p>
    </div>
  );
}
