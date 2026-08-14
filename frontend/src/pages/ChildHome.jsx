/* ============================================================
 * ChildHome — 儿童端主页（/home，登录/启动后的第一站）
 *
 * 两张入口大卡：💬 去聊天 / 🪐 我的小星球。
 * 时段问候（utils/time）+ 与星球页一致的 data-time 昼夜氛围；
 * 顶栏常驻 AiIdentityBadge（合规：AI 身份标识），页脚再声明一次。
 * 家长角色误入时 redirect /parent。
 * ============================================================ */

import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { apiFetch, getStoredUser } from "../utils/api";
import { useDailyChallenge } from "../hooks/useDailyChallenge";
import { currentTimeBand, TIME_GREETING } from "../utils/time";
import AiIdentityBadge from "../components/AiIdentityBadge";
import "./ChildHome.css";

const ENTRANCES = [
  {
    to: "/chat",
    emoji: "💬",
    title: "去聊天",
    desc: "开心的、奇怪的、想问的，都可以说给我听",
    color: "var(--sky)",
  },
  {
    to: "/planet",
    emoji: "🪐",
    title: "我的小星球",
    desc: "看看你种下的星星、云朵和嫩芽",
    color: "var(--sprout)",
  },
];

/* ---- 速览小卡：星球天气 + 今日挑战（展示为主、点击跳转，失败静默降级） ---- */
function GlanceCards() {
  const challenge = useDailyChallenge();
  const [glance, setGlance] = useState(null); // {emoji, text, count}

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiFetch("/api/planet/weather"),
      apiFetch("/api/planet/entries"),
    ])
      .then(([w, e]) => {
        if (!cancelled && w?.emoji) {
          setGlance({
            emoji: w.emoji,
            text: w.text,
            count: (e.entries || []).length,
          });
        }
      })
      .catch(() => {
        /* 速览拉不到就不显示这张卡 */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!glance && !challenge) return null;
  return (
    <div className="home-glance">
      {glance && (
        <Link to="/planet" className="home-glance-card">
          <span aria-hidden="true">{glance.emoji}</span>
          <span>
            小星球今天{glance.text} · 已有 {glance.count} 个宝贝
          </span>
        </Link>
      )}
      {challenge && (
        <Link to="/chat" className="home-glance-card">
          <span aria-hidden="true">🌞</span>
          <span>今天的小挑战：{challenge.text}</span>
        </Link>
      )}
    </div>
  );
}

export default function ChildHome() {
  const user = getStoredUser();
  const reduced = useReducedMotion();

  // 家长角色没有儿童主页，直接回家长端
  if (user?.role === "parent") return <Navigate to="/parent" replace />;

  const band = currentTimeBand();
  const enter = (i) =>
    reduced
      ? {}
      : {
          initial: { opacity: 0, y: 16 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.5, ease: [0.23, 1, 0.32, 1], delay: 0.08 + i * 0.08 },
        };

  return (
    <div className="home-page track-child" data-time={band}>
      {/* 顶栏：品牌 + AI 身份徽章（合规常驻） */}
      <header className="home-header">
        <div className="home-brand">
          <span aria-hidden="true">🪐</span>
          <span className="home-brand-name">安心童伴</span>
        </div>
        <AiIdentityBadge ageTier={user?.age_tier} />
      </header>

      <main className="home-main">
        <motion.div className="home-greeting" {...enter(0)}>
          <h1 className="home-greeting-title">
            {TIME_GREETING[band]}，{user?.username || "小朋友"}！
          </h1>
          <p className="home-greeting-sub">今天想去哪里呀？</p>
        </motion.div>

        <motion.div {...enter(1)}>
          <GlanceCards />
        </motion.div>

        <nav className="home-entrances" aria-label="去哪里">
          {ENTRANCES.map((e, i) => (
            <motion.div key={e.to} {...enter(i + 2)}>
              <Link
                to={e.to}
                className="home-card"
                style={{ "--card-color": e.color }}
              >
                <span className="home-card__badge" aria-hidden="true">
                  {e.emoji}
                </span>
                <span className="home-card__text">
                  <strong>{e.title}</strong>
                  <span>{e.desc}</span>
                </span>
              </Link>
            </motion.div>
          ))}
        </nav>

        {/* 安全承诺条（纯静态，孩子能懂的语言传达安全主线） */}
        <motion.p className="home-promise" {...enter(4)}>
          <span aria-hidden="true">🛡️</span>
          你说的每句话，我都会先仔细检查再回答
        </motion.p>
      </main>

      <footer className="home-footer">
        安心童伴是 AI 程序，不是真人 · 所有对话都会经过安全检查
      </footer>
    </div>
  );
}
