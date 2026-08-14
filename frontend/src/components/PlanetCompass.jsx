/* ============================================================
 * PlanetCompass — 星球罗盘（v2.4 §3.2）
 *
 * 合并 v2.3 的「记忆轨道 + 类型筛选 chips + 树联动」为一个导航：
 * - 4 枚类型卫星（⭐好奇星/☁️心情云/🌱探索芽/📖故事册），常显；
 *   有内容的类型显示数量，空类型虚线描边。
 * - 点击卫星 = 筛选条目区 + 生命树对应元素点亮；再点一次取消筛选。
 * - 空类型点击直接打开对应类型的「种下」表单（空状态即入口）。
 *
 * 交互纪律：
 * - 选中态 = 类型色 15% 填充（transform/opacity 过渡，不用 filter 动画）
 * - 每枚 ≥64×64px，移动端 4 枚横排不换行（满足 44px 触摸目标）
 * - 图标 + 文字同显，颜色不作唯一信息来源
 * ============================================================ */

import { TYPE_META } from "./PlanetCard";
import "./PlanetCompass.css";

/* 四类展示顺序与类型色（与生命树/卡片同一 token 粉彩） */
const COMPASS_GROUPS = [
  { type: "star", color: "var(--star)" },
  { type: "cloud", color: "var(--cloud)" },
  { type: "sprout", color: "var(--sprout)" },
  { type: "story", color: "var(--sunset)" },
];

export default function PlanetCompass({ counts = {}, activeType, onSelect, onPlant }) {
  return (
    <nav className="planet-compass" aria-label="星球罗盘">
      {COMPASS_GROUPS.map((g) => {
        const meta = TYPE_META[g.type];
        const count = counts[g.type] || 0;
        const isOn = activeType === g.type;
        const isEmpty = count === 0;
        return (
          <button
            key={g.type}
            type="button"
            className={`compass-satellite ${isOn ? "is-on" : ""} ${isEmpty ? "is-empty" : ""}`}
            style={{ "--satellite-color": g.color }}
            aria-pressed={isOn}
            onClick={() => {
              if (isEmpty) {
                onPlant?.(g.type); // 空类型 = 种下入口
              } else {
                onSelect?.(isOn ? null : g.type);
              }
            }}
          >
            <span className="compass-satellite__icon" aria-hidden="true">
              {meta.icon}
            </span>
            <span className="compass-satellite__label">{meta.label}</span>
            <span className="compass-satellite__count" aria-hidden="true">
              {isEmpty ? "＋" : count}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
