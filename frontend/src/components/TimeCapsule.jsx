/* ============================================================
 * TimeCapsule — 时间胶囊花园（v2.4：横向架，位置在条目区之后）
 *
 * - 横向胶囊架：桌面端可换行，移动端横向滚动；区顶一条柔和地平线
 * - 密封卡：蛋壳 SVG + 🔒 + countdown（"还有 N 天"/"明天"/"今天"），
 *   内容只给模糊预览（封存时看不见）
 * - 已解锁卡：破壳蛋壳 + 完整内容；第一次看到的解锁会放一小簇粒子 +
 *   屏幕中央 2s 非模态 toast（sessionStorage 记录已见过，不重复放）
 * - 空状态：沉睡的蛋，整卡可点击直接打开创建表单
 * - 创建表单：标题 + 内容 + 解锁时间（明天/7 天后/30 天后/自定义日期）
 * - 删除：两步温和确认（再点一次才删）
 * ============================================================ */

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import PillButton from "./PillButton";
import GentleDelete from "./GentleDelete";
import "./TimeCapsule.css";

/* sessionStorage：已看过破壳动画的胶囊 id */
const SEEN_KEY = "anxin_seen_unlocked";
function loadSeen() {
  try {
    return new Set(JSON.parse(sessionStorage.getItem(SEEN_KEY) || "[]"));
  } catch {
    return new Set();
  }
}
function markSeen(id) {
  const seen = loadSeen();
  seen.add(id);
  try {
    sessionStorage.setItem(SEEN_KEY, JSON.stringify([...seen]));
  } catch {
    /* 存储失败只是多放一次动画，无妨 */
  }
}

/* 密封蛋壳：奶油底 + 粉彩斑点 */
function EggSealed() {
  return (
    <svg viewBox="-36 -44 72 88" className="capsule-egg" aria-hidden="true">
      <ellipse cx="0" cy="0" rx="30" ry="38" fill="var(--off-white)" stroke="var(--border-strong)" strokeWidth="1.5" />
      <circle cx="-10" cy="-12" r="4" fill="var(--cloud)" />
      <circle cx="10" cy="2" r="3.2" fill="var(--sky)" />
      <circle cx="-6" cy="14" r="3.6" fill="var(--star)" />
      <circle cx="12" cy="-20" r="2.6" fill="var(--sprout)" />
    </svg>
  );
}

/* 破壳蛋壳：上下两半沿锯齿缝分开，上半壳弹开 */
function EggCracked() {
  const crack = "L-18 -7 L-9 3 L0 -7 L9 3 L18 -7 L30 0";
  return (
    <svg viewBox="-44 -56 88 104" className="capsule-egg" aria-hidden="true">
      {/* 下半壳（原地） */}
      <path
        d={`M-30 0 ${crack} A30 38 0 0 1 -30 0 Z`}
        fill="var(--off-white)" stroke="var(--border-strong)" strokeWidth="1.5"
      />
      {/* 上半壳（掀开） */}
      <motion.g
        initial={{ y: 0, rotate: 0, opacity: 1 }}
        animate={{ y: -16, x: 8, rotate: 26 }}
        transition={{ type: "spring", stiffness: 260, damping: 15 }}
        style={{ transformBox: "fill-box", transformOrigin: "50% 100%" }}
      >
        <path
          d={`M-30 0 ${crack} A30 38 0 0 0 -30 0 Z`}
          fill="var(--off-white)" stroke="var(--border-strong)" strokeWidth="1.5"
        />
        <circle cx="-8" cy="-16" r="3.4" fill="var(--cloud)" />
        <circle cx="9" cy="-26" r="2.8" fill="var(--sky)" />
      </motion.g>
    </svg>
  );
}

/* 首次解锁的粒子小簇：八点金星向外弹开，放完即收 */
function UnlockBurst() {
  return (
    <span className="capsule-burst" aria-hidden="true">
      {Array.from({ length: 8 }, (_, i) => {
        const a = (Math.PI / 4) * i;
        return (
          <motion.span
            key={i}
            className="capsule-burst-dot"
            initial={{ x: 0, y: 0, scale: 1, opacity: 1 }}
            animate={{
              x: Math.cos(a) * 42,
              y: Math.sin(a) * 42,
              scale: 0.2,
              opacity: 0,
            }}
            transition={{ duration: 0.7, ease: "easeOut", delay: i * 0.03 }}
          />
        );
      })}
    </span>
  );
}

/* 两步温和确认删除 → 共用组件 GentleDelete */

/* 单张胶囊卡 */
function CapsuleCard({ capsule, onDelete, onFirstUnlock }) {
  // 首次见到的已解锁胶囊 → 放一次破壳粒子 + 通知外层弹 toast
  const [burst, setBurst] = useState(false);
  const seenRef = useRef(false);
  useEffect(() => {
    if (capsule.unlocked && !seenRef.current && !loadSeen().has(capsule.id)) {
      seenRef.current = true;
      markSeen(capsule.id);
      setBurst(true);
      onFirstUnlock?.();
      const t = setTimeout(() => setBurst(false), 1200);
      return () => clearTimeout(t);
    }
    return undefined;
  }, [capsule.id, capsule.unlocked, onFirstUnlock]);

  const created = (capsule.created_at || "").slice(0, 10);

  return (
    <motion.li
      className={`capsule-card card ${capsule.unlocked ? "capsule-card--open" : "capsule-card--sealed"}`}
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
    >
      <div className="capsule-egg-wrap">
        {capsule.unlocked ? <EggCracked /> : <EggSealed />}
        {burst && <UnlockBurst />}
      </div>

      <div className="capsule-body">
        <div className="capsule-title-row">
          <span aria-hidden="true">{capsule.unlocked ? "📬" : "🔒"}</span>
          <strong className="capsule-title">{capsule.title}</strong>
        </div>
        <div className="capsule-meta">
          封存于 <time>{created}</time>
          {capsule.unlocked ? " · 已破壳" : ""}
        </div>

        {capsule.unlocked ? (
          <p className="capsule-content">{capsule.content}</p>
        ) : (
          <>
            <span className="capsule-countdown">⏳ {capsule.countdown || "等待破壳"}</span>
            {capsule.content && (
              <p className="capsule-content capsule-content--blurred">{capsule.content}</p>
            )}
          </>
        )}

        <div className="capsule-actions">
          <GentleDelete onConfirm={() => onDelete(capsule.id)} />
        </div>
      </div>
    </motion.li>
  );
}

/* 解锁时间快捷选项 */
const UNLOCK_PRESETS = [
  { key: "1", label: "明天" },
  { key: "7", label: "7 天后" },
  { key: "30", label: "30 天后" },
  { key: "custom", label: "自己选日子" },
];

/* 创建表单 */
function CapsuleForm({ onCreate, onCancel }) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [preset, setPreset] = useState("7");
  const [customDate, setCustomDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("给这颗胶囊起个名字吧～");
      return;
    }
    let unlockAt;
    if (preset === "custom") {
      if (!customDate) {
        setError("选一个想打开的日子吧～");
        return;
      }
      unlockAt = new Date(`${customDate}T09:00:00`);
    } else {
      unlockAt = new Date(Date.now() + Number(preset) * 86400000);
    }
    setBusy(true);
    setError(null);
    try {
      await onCreate({
        title: title.trim(),
        content: content.trim(),
        unlock_at: unlockAt.toISOString(),
      });
      onCancel(); // 成功后收起表单
    } catch (err) {
      setError(err.message || "没封上，再试一次吧");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="capsule-form card" onSubmit={handleSubmit}>
      <label className="capsule-form-field">
        <span>胶囊名字</span>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="给未来的自己的一封信…"
          maxLength={128}
        />
      </label>
      <label className="capsule-form-field">
        <span>想对未来的自己说什么？</span>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="嘿，你现在变得更勇敢了吗？还记得写这封信的时候吗…"
          rows={3}
        />
      </label>
      <div className="capsule-form-field">
        <span>什么时候破壳？</span>
        <div className="capsule-presets">
          {UNLOCK_PRESETS.map((p) => (
            <button
              key={p.key}
              type="button"
              className={`capsule-preset ${preset === p.key ? "capsule-preset--on" : ""}`}
              onClick={() => setPreset(p.key)}
            >
              {p.label}
            </button>
          ))}
        </div>
        {preset === "custom" && (
          <input
            type="date"
            value={customDate}
            onChange={(e) => setCustomDate(e.target.value)}
            min={new Date().toISOString().slice(0, 10)}
          />
        )}
      </div>

      {error && <p className="capsule-form-error">{error}</p>}

      <div className="capsule-form-actions">
        <PillButton type="submit" disabled={busy}>
          {busy ? "封存中…" : "封好它 ✉️"}
        </PillButton>
        <PillButton variant="ghost" onClick={onCancel}>
          先不封了
        </PillButton>
      </div>
    </form>
  );
}

/* 沉睡的蛋（空状态）：整卡可点击，点击直接打开创建表单 */
function SleepingEgg({ onClick }) {
  return (
    <button type="button" className="capsule-sleep" onClick={onClick}>
      <span className="capsule-sleep-egg" aria-hidden="true">
        <EggSealed />
        <span className="capsule-sleep-zzz">💤</span>
      </span>
      <span className="capsule-sleep-text">
        花园里还睡着一颗蛋。点它一下，给未来的自己写封信吧～
      </span>
    </button>
  );
}

export default function TimeCapsule({ capsules = [], loaded, onCreate, onDelete }) {
  const [formOpen, setFormOpen] = useState(false);
  const [toast, setToast] = useState(false);
  const toastTimer = useRef(null);

  /** 首次破壳 → 屏幕中央非模态 toast，2s 自动消失 */
  const handleFirstUnlock = useCallback(() => {
    setToast(true);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(false), 2000);
  }, []);
  useEffect(() => () => clearTimeout(toastTimer.current), []);

  return (
    <section className="capsule-section" aria-label="时间胶囊">
      <div className="capsule-head">
        <h2 className="section-title">
          <span className="section-dot section-dot--capsule" aria-hidden="true" />
          ✉️ 时间胶囊
        </h2>
        <p className="section-sub">写给未来的自己——封存时看不见，到期自动破壳。</p>
      </div>

      {loaded && capsules.length === 0 && !formOpen && (
        <SleepingEgg onClick={() => setFormOpen(true)} />
      )}

      {capsules.length > 0 && (
        <ul className="capsule-grid">
          {capsules.map((c) => (
            <CapsuleCard
              key={c.id}
              capsule={c}
              onDelete={onDelete}
              onFirstUnlock={handleFirstUnlock}
            />
          ))}
        </ul>
      )}

      {formOpen ? (
        <CapsuleForm onCreate={onCreate} onCancel={() => setFormOpen(false)} />
      ) : (
        capsules.length > 0 && (
          <PillButton variant="ghost" onClick={() => setFormOpen(true)}>
            ＋ 封一颗新胶囊
          </PillButton>
        )
      )}

      <AnimatePresence>
        {toast && (
          <motion.p
            className="capsule-toast"
            role="status"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            胶囊破壳啦 🎉
          </motion.p>
        )}
      </AnimatePresence>
    </section>
  );
}
