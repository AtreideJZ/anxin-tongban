/* RiskBadge — 风险等级语义色 pill（绿/黄/橙/红，两端统一含义）
 * 家长端告警卡 / 仪表盘 / 安全引擎演示结果共用
 */
import "./RiskBadge.css";

const LEVELS = [
  { label: "安全", color: "var(--risk-0)" },
  { label: "轻度", color: "var(--risk-1)" },
  { label: "中度", color: "var(--risk-2)" },
  { label: "高危", color: "var(--risk-3)" },
];

export default function RiskBadge({ level = 0, showLevel = false }) {
  const conf = LEVELS[Math.min(Math.max(level, 0), 3)];
  return (
    <span
      className="risk-badge"
      style={{ "--risk-color": conf.color }}
      title={`风险等级 ${level}`}
    >
      <span className="risk-badge-dot" aria-hidden="true" />
      {conf.label}
      {showLevel ? ` · L${level}` : ""}
    </span>
  );
}
