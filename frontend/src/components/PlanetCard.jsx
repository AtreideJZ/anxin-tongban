/* ============================================================
 * PlanetCard — 星球条目卡（⭐好奇星/☁️心情云/🌱探索芽/📖故事册）
 * 标题 / 类型·日期 / 内容 / 心情色点（心情云）/ 标签 / 温和删除
 * ============================================================ */

import { motion } from "framer-motion";
import GentleDelete from "./GentleDelete";
import "./PlanetCard.css";

/* 类型元信息（与后端四类一致） */
export const TYPE_META = {
  star: { icon: "⭐", label: "好奇星" },
  cloud: { icon: "☁️", label: "心情云" },
  sprout: { icon: "🌱", label: "探索芽" },
  story: { icon: "📖", label: "故事册" },
};

/* 心情云四色 → token 粉彩（pink|blue|gray|yellow） */
export const MOOD_COLORS = {
  pink: "var(--cloud)",
  blue: "var(--sky)",
  gray: "var(--muted)",
  yellow: "var(--star)",
};

export const MOOD_LABELS = {
  pink: "甜甜的",
  blue: "有点低落",
  gray: "灰蒙蒙的",
  yellow: "亮晶晶的",
};

/* 类型色（卡片左侧竖条，与生命树/罗盘同一 token 粉彩） */
const TYPE_COLORS = {
  star: "var(--star)",
  cloud: "var(--cloud)",
  sprout: "var(--sprout)",
  story: "var(--sunset)",
};

export default function PlanetCard({ entry, onDelete }) {
  const meta = TYPE_META[entry.type] || TYPE_META.star;
  return (
    <motion.li
      className="planet-entry-card card"
      style={{ "--type-color": TYPE_COLORS[entry.type] || "var(--sky)" }}
      data-entry-id={entry.id}
      initial={{ scale: 0.92, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
      whileTap={{ scale: 0.98 }}
      layout
    >
      <div className="planet-entry-head">
        <span className="planet-entry-icon" aria-hidden="true">
          {meta.icon}
        </span>
        <div className="planet-entry-heading">
          <strong className="planet-entry-title">{entry.title}</strong>
          <span className="planet-entry-meta">
            {meta.label} · <time>{entry.date}</time>
          </span>
        </div>
        {entry.type === "cloud" && entry.mood && (
          <span
            className="planet-entry-mood"
            style={{ "--mood": MOOD_COLORS[entry.mood] || "var(--cloud)" }}
            title={MOOD_LABELS[entry.mood] || "心情色"}
            aria-label={`心情：${MOOD_LABELS[entry.mood] || entry.mood}`}
          />
        )}
      </div>

      {entry.content && <p className="planet-entry-content">{entry.content}</p>}

      {entry.tags?.length > 0 && (
        <div className="planet-entry-tags">
          {entry.tags.map((t) => (
            <span key={t} className="planet-entry-tag">
              {t}
            </span>
          ))}
        </div>
      )}

      <div className="planet-entry-actions">
        <GentleDelete onConfirm={() => onDelete(entry.id)} />
      </div>
    </motion.li>
  );
}
