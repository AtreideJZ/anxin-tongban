/* RecommendationCard — 推荐卡片："💡 还想了解……？" 粉彩 pill 列表 */
import "./RecommendationCard.css";

export default function RecommendationCard({ items = [] }) {
  if (!items.length) return null;
  return (
    <div className="rec-card">
      <div className="rec-title">💡 还想了解……？</div>
      <div className="rec-list">
        {items.map((item, i) => (
          <span key={i} className="rec-pill">
            {typeof item === "string" ? item : item.text || item.title}
          </span>
        ))}
      </div>
    </div>
  );
}
