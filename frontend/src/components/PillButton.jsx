/* PillButton — pill 主按钮/描边次按钮封装（形状纪律：主按钮只有 pill） */
import "./PillButton.css";

export default function PillButton({
  variant = "primary", // primary → .btn-pill；ghost → .btn-ghost
  type = "button",
  disabled = false,
  onClick,
  children,
  className = "",
}) {
  const base = variant === "ghost" ? "btn-ghost" : "btn-pill";
  return (
    <button
      type={type}
      className={`${base} ${className}`.trim()}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
