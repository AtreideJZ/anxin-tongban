/* SafetyShield — 等待期"呼吸盾牌"动画（动效语言：等待=呼吸盾牌）
 * Framer Motion spring 缩放呼吸感 + 轮换的儿童友好提示文案
 * 不展示任何 Pipeline 技术步骤名，只按阶段悄悄换提示
 */
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import "./SafetyShield.css";

// 各阶段的儿童友好提示（waiting=等首事件 processing=step 回放中）
const HINTS = {
  waiting: ["安心童伴正在认真想…", "小脑袋转呀转…", "马上就好哦…"],
  processing: ["正在做安全检查哦…", "小盾牌正在站岗…", "检查通过就来啦…"],
};

export default function SafetyShield({ phase = "waiting" }) {
  const hints = HINTS[phase] || HINTS.waiting;
  const [idx, setIdx] = useState(0);

  // 每 2.4s 轮换一条提示；换阶段时从头开始
  useEffect(() => {
    setIdx(0);
    const timer = setInterval(
      () => setIdx((i) => (i + 1) % hints.length),
      2400
    );
    return () => clearInterval(timer);
  }, [phase, hints.length]);

  return (
    <div className="safety-shield" role="status" aria-live="polite">
      <motion.div
        className="safety-shield-icon"
        animate={{ scale: [1, 1.12, 1] }}
        transition={{
          duration: 1.6,
          repeat: Infinity,
          ease: "easeInOut",
          type: "spring",
          stiffness: 120,
          damping: 14,
        }}
      >
        🛡️
      </motion.div>
      <motion.div
        key={`${phase}-${idx}`}
        className="safety-shield-hint"
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 26 }}
      >
        {hints[idx]}
      </motion.div>
    </div>
  );
}
