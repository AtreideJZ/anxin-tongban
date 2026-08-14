/* ============================================================
 * MyPlanet — 我的小星球（儿童轨，情感设计核心页 · v2.4 版）
 *
 * 动线（v2.4 §三，生命树是唯一视觉主角）：
 *   顶栏 → 轻 Hero（时段问候 + 今日小挑战胶囊条）→ 生命树（含天气氛围）
 *   → 星球罗盘（类型筛选 + 树联动 + 空类型入口，三合一）
 *   → 条目区（「本周」时间条 / 「种类」分组双视图）
 *   → 共创故事卫星卡 → 时间胶囊花园（横向架，位置下调）
 *
 * 分龄：5-7 锁定本周视图 + 简版种下表单（大图标 + 一个输入框）；
 *      8+ 可切换视图 + 完整表单（modal 化，backdrop blur）。
 *
 * 反馈：种下成功 → 按钮变「种下了 ✨」+ 树心粒子（GrowthTree 内部）
 *      + 新卡片平滑滚入视野；sprout 校验温和提示条沿用旧逻辑。
 *
 * 儿童端纪律：不展示风险等级 / 决策链 / 技术步骤名。
 * ============================================================ */

import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { usePlanet } from "../hooks/usePlanet";
import { useCapsules } from "../hooks/useCapsules";
import { getStoredUser } from "../utils/api";
import { useDailyChallenge } from "../hooks/useDailyChallenge";
import { timeBandOf, TIME_GREETING } from "../utils/time";
import GrowthTree from "../components/GrowthTree";
import PlanetCompass from "../components/PlanetCompass";
import TimeCapsule from "../components/TimeCapsule";
import PlanetCard, {
  MOOD_COLORS,
  MOOD_LABELS,
  TYPE_META,
} from "../components/PlanetCard";
import PillButton from "../components/PillButton";
import AiIdentityBadge from "../components/AiIdentityBadge";
import "./MyPlanet.css";

/* 四类分组的展示顺序与点缀色（token 粉彩） */
const GROUPS = [
  { type: "star", dot: "var(--star)" },
  { type: "cloud", dot: "var(--cloud)" },
  { type: "sprout", dot: "var(--sprout)" },
  { type: "story", dot: "var(--sunset)" },
];

const MOOD_KEYS = ["pink", "blue", "gray", "yellow"];

/* 各类型内容框的引导文案（沿用旧版的温暖语气） */
const CONTENT_HINT = {
  star: { label: "记下你的发现或问题", placeholder: "我发现… / 我想知道…" },
  cloud: { label: "当时是什么感受？", placeholder: "今天有点难过，因为…" },
  sprout: {
    label: "你在真实世界里经历了什么？",
    placeholder: "例如：我告诉了老师同学推我的事… 或者 在公园发现了一只没见过的虫子…",
  },
  story: { label: "故事预览（开头一段）", placeholder: "从前有一只小恐龙…" },
};

/* ---- 时段问候语与昼夜氛围 band 见 utils/time（儿童端共用） ---- */

/* 统一入场动效（v2.4 §四）：opacity 0 + translateY(16px)，stagger 50ms */
const sectionEnter = (i = 0) => ({
  initial: { opacity: 0, y: 16 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.5, ease: [0.23, 1, 0.32, 1], delay: i * 0.05 },
});

/* ---- 轻 Hero：一句话问候 + 今日小挑战胶囊条（挑战闭环：点击回聊天页） ---- */
function PlanetHero({ username }) {
  const challenge = useDailyChallenge();
  const band = timeBandOf(new Date().getHours());
  return (
    <header className="planet-hero">
      <h1 className="planet-hero__greeting">
        {TIME_GREETING[band]}，{username}的小星球
      </h1>
      {challenge && (
        <Link to="/chat" className="daily-challenge-pill">
          <span aria-hidden="true">🌞</span> 今天的小挑战：{challenge.text}
        </Link>
      )}
    </header>
  );
}

/* ---- 种下新东西表单（8+ 完整字段；5-7 简版：大图标 + 一个输入框） ---- */
function EntryForm({ simple = false, initialType = "star", onSubmit, onCancel }) {
  const [type, setType] = useState(initialType);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [mood, setMood] = useState("pink");
  const [tags, setTags] = useState("");
  const [busy, setBusy] = useState(false);
  const [planted, setPlanted] = useState(false); // 「种下了 ✨」短暂反馈
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("给这一刻起个名字吧～");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onSubmit({
        type,
        title: title.trim(),
        content: simple ? "" : content.trim(),
        mood: !simple && type === "cloud" ? mood : undefined,
        tags: !simple && tags.trim() ? tags.trim().split(/\s+/) : [],
      });
      // 成功反馈：按钮变「种下了 ✨」，停一小下再关，让孩子看到确认
      setPlanted(true);
      setTimeout(onCancel, 900);
    } catch (err) {
      setError(err.message || "没种上，再试一次吧");
      setBusy(false);
    }
  };

  const hint = CONTENT_HINT[type];

  return (
    <form className={`entry-form ${simple ? "entry-form--simple" : ""}`} onSubmit={handleSubmit}>
      {/* 选类型：简版用大图标（≥72px 触摸目标），完整版用 pill */}
      <div className="entry-form-field">
        <span>想种下什么？</span>
        <div className={`entry-type-picker ${simple ? "entry-type-picker--big" : ""}`}>
          {GROUPS.map((g) => (
            <button
              key={g.type}
              type="button"
              className={`entry-type-option ${type === g.type ? "entry-type-option--on" : ""}`}
              onClick={() => setType(g.type)}
              aria-pressed={type === g.type}
            >
              <span className="entry-type-icon" aria-hidden="true">
                {TYPE_META[g.type].icon}
              </span>
              {TYPE_META[g.type].label}
            </button>
          ))}
        </div>
      </div>

      <label className="entry-form-field">
        <span>给它起个名字</span>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="给这一刻起个名字…"
          maxLength={128}
        />
      </label>

      {!simple && type === "cloud" && (
        <div className="entry-form-field">
          <span>这朵云是什么颜色的？</span>
          <div className="mood-picker">
            {MOOD_KEYS.map((m) => (
              <button
                key={m}
                type="button"
                className={`mood-option ${mood === m ? "mood-option--on" : ""}`}
                onClick={() => setMood(m)}
                aria-pressed={mood === m}
              >
                <span className="mood-dot" style={{ "--mood": MOOD_COLORS[m] }} />
                {MOOD_LABELS[m]}
              </button>
            ))}
          </div>
        </div>
      )}

      {!simple && (
        <label className="entry-form-field">
          <span>{hint.label}</span>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={hint.placeholder}
            rows={3}
          />
        </label>
      )}

      {!simple && (
        <label className="entry-form-field">
          <span>标签（用空格分开，可以不填）</span>
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="科学 好奇"
          />
        </label>
      )}

      {error && <p className="entry-form-error">{error}</p>}

      <div className="entry-form-actions">
        <PillButton type="submit" disabled={busy}>
          {planted ? "种下了 ✨" : busy ? "种下中…" : "种下来 🌱"}
        </PillButton>
        <PillButton variant="ghost" onClick={onCancel}>
          先不种了
        </PillButton>
      </div>
    </form>
  );
}

/* ---- 表单弹层：8+ 居中 modal；5-7 全屏底部面板；遮罩半透奶油 + blur ---- */
function EntryFormModal({ simple, presetType, onSubmit, onClose }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <motion.div
      className="entry-modal-backdrop"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      onClick={onClose}
    >
      <motion.div
        className={`entry-modal ${simple ? "entry-modal--sheet" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label="种下新东西"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 24 }}
        transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
        onClick={(e) => e.stopPropagation()}
      >
        <EntryForm
          simple={simple}
          initialType={presetType}
          onSubmit={onSubmit}
          onCancel={onClose}
        />
      </motion.div>
    </motion.div>
  );
}

/* ---- sprout 校验温和提示条（后端已保存，只提醒不训斥） ---- */
function SproutNotice({ notice, onRetype, onDismiss }) {
  const suggested = notice.validation?.suggested_type;
  const suggestedMeta = suggested && TYPE_META[suggested];
  // 后端文案带 ** 强调标记，给孩子看前去掉
  const message = (notice.validation?.message || "").replace(/\*\*/g, "");
  return (
    <motion.div
      className="sprout-notice card"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 26 }}
      role="status"
    >
      <p className="sprout-notice-text">{message}</p>
      <p className="sprout-notice-hint">这条已经帮你留在探索芽里啦，没有丢。</p>
      <div className="sprout-notice-actions">
        {suggestedMeta && (
          <PillButton variant="ghost" onClick={onRetype}>
            改成{suggestedMeta.icon} {suggestedMeta.label}
          </PillButton>
        )}
        <PillButton variant="ghost" onClick={onDismiss}>
          知道啦
        </PillButton>
      </div>
    </motion.div>
  );
}

/* ---- 本周视图：近 7 天横向时间条，更早的收进折叠区 ---- */
function localDayKey(d) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function dayLabel(date, offset) {
  if (offset === 0) return "今天";
  if (offset === 1) return "昨天";
  return `${date.getMonth() + 1}月${date.getDate()}日`;
}

function WeekView({ entries, activeType, onDelete }) {
  const [showEarlier, setShowEarlier] = useState(false);

  const { days, earlier } = useMemo(() => {
    const today = new Date();
    const buckets = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() - i);
      return { key: localDayKey(d), date: d, offset: i, items: [] };
    });
    const index = new Map(buckets.map((b, i) => [b.key, i]));
    const older = [];
    for (const e of entries) {
      const key = (e.created_at || "").slice(0, 10) || e.date;
      const i = index.get(key);
      if (i === undefined) older.push(e);
      else buckets[i].items.push(e);
    }
    return { days: buckets, earlier: older };
  }, [entries]);

  const match = (e) => !activeType || e.type === activeType;
  const visibleDays = days
    .map((d) => ({ ...d, items: d.items.filter(match) }))
    .filter((d) => d.items.length > 0 || !activeType);
  const visibleEarlier = earlier.filter(match);

  return (
    <div className="week-view">
      {visibleDays.length === 0 ? (
        <p className="entries-empty card">这一周这一类还没有宝贝，种一颗试试吧～</p>
      ) : (
        <div className="week-strip">
          {visibleDays.map((d) => (
          <div key={d.key} className="week-day">
            <p className="week-day-label">
              {dayLabel(d.date, d.offset)}
              <span className="week-day-count">
                {d.items.length > 0 ? `${d.items.length} 件小事` : ""}
              </span>
            </p>
            <ul className="week-day-list">
              {d.items.map((entry) => (
                <PlanetCard key={entry.id} entry={entry} onDelete={onDelete} />
              ))}
            </ul>
            {d.items.length === 0 && <span className="week-day-dot" aria-hidden="true" />}
          </div>
          ))}
        </div>
      )}

      {visibleEarlier.length > 0 && (
        <div className="week-earlier">
          <PillButton variant="ghost" onClick={() => setShowEarlier((v) => !v)}>
            {showEarlier ? "收起更早的" : `更早的（${visibleEarlier.length}）`}
          </PillButton>
          {showEarlier && (
            <ul className="entry-grid">
              {visibleEarlier.map((entry) => (
                <PlanetCard key={entry.id} entry={entry} onDelete={onDelete} />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

/* ---- 种类视图：四类分组（联动罗盘筛选），每组最多 6 张 + 展开更多 ---- */
const GROUP_LIMIT = 6;

function EntryGroup({ group, entries, onDelete }) {
  const [expanded, setExpanded] = useState(false);
  const meta = TYPE_META[group.type];
  const shown = expanded ? entries : entries.slice(0, GROUP_LIMIT);
  return (
    <div className="entry-group">
      <h3 className="entry-group-title">
        <span className="section-dot" style={{ "--dot": group.dot }} aria-hidden="true" />
        {meta.icon} {meta.label}
      </h3>
      <ul className="entry-grid">
        {shown.map((entry) => (
          <PlanetCard key={entry.id} entry={entry} onDelete={onDelete} />
        ))}
      </ul>
      {entries.length > GROUP_LIMIT && (
        <PillButton variant="ghost" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "收起来" : `展开更多（还有 ${entries.length - GROUP_LIMIT} 张）`}
        </PillButton>
      )}
    </div>
  );
}

function TypeView({ entries, activeType, onDelete }) {
  const groups = GROUPS.map((g) => ({
    ...g,
    list: entries.filter((e) => e.type === g.type),
  })).filter((g) => g.list.length > 0 && (!activeType || g.type === activeType));

  if (groups.length === 0) {
    return <p className="entries-empty card">这一类还没有宝贝，点上面的「＋ 种下新东西」试试吧～</p>;
  }
  return (
    <>
      {groups.map((g) => (
        <EntryGroup key={g.type} group={g} entries={g.list} onDelete={onDelete} />
      ))}
    </>
  );
}

/* ---- 共创故事卫星卡（替代 ghost 链接，v2.3 §5.5） ---- */
function CoCreationSatellite() {
  return (
    <Link to="/cocreation" className="cocreation-satellite">
      <span className="cocreation-satellite__badge" aria-hidden="true">
        🚀
      </span>
      <span className="cocreation-satellite__text">
        <strong>共创故事</strong>
        <span>和爸爸妈妈一起写故事</span>
      </span>
    </Link>
  );
}

export default function MyPlanet() {
  const { entries, weather, loading, error, createEntry, deleteEntry } = usePlanet();
  const { capsules, loaded: capsulesLoaded, createCapsule, deleteCapsule } =
    useCapsules();
  const reduced = useReducedMotion();
  /* reduced-motion：入场动效整体降级为直接呈现 */
  const enter = (i) => (reduced ? {} : sectionEnter(i));

  const user = getStoredUser();
  const ageTier = user?.age_tier || "8-10";
  const simpleMode = ageTier === "5-7"; // 5-7 守护模式最低龄档：认知减负

  const [activeType, setActiveType] = useState(null); // 罗盘筛选
  const [view, setView] = useState("week"); // week | type（5-7 锁定 week）
  const [form, setForm] = useState({ open: false, presetType: "star" });
  const [notice, setNotice] = useState(null); // sprout 校验提示 {entry, validation}
  const [newEntryId, setNewEntryId] = useState(null); // 种成功后滚入视野用

  const counts = useMemo(() => {
    const c = { star: 0, cloud: 0, sprout: 0, story: 0 };
    for (const e of entries) {
      if (c[e.type] !== undefined) c[e.type] += 1;
    }
    return c;
  }, [entries]);

  /** 表单提交；sprout 校验不过时弹出温和提示条 */
  const handleCreate = async (payload) => {
    const data = await createEntry(payload);
    if (payload.type === "sprout" && data.validation && data.validation.valid === false) {
      setNotice({ entry: data.entry, validation: data.validation });
    }
    if (data.entry) {
      // 新卡片要能被看到：筛选挡着就先取消筛选
      if (activeType && data.entry.type !== activeType) setActiveType(null);
      setNewEntryId(data.entry.id);
    }
    return data;
  };

  /* 种下成功 → 新卡片平滑滚入视野（reduced-motion 时直接定位） */
  useEffect(() => {
    if (!newEntryId) return;
    const el = document.querySelector(`[data-entry-id="${newEntryId}"]`);
    if (el) {
      el.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "center" });
    }
    setNewEntryId(null);
  }, [newEntryId, entries, reduced]);

  /** 按建议类型重种：新建建议类型条目 → 删掉原探索芽 */
  const handleRetype = async () => {
    if (!notice) return;
    const { entry, validation } = notice;
    setNotice(null);
    try {
      await createEntry({
        type: validation.suggested_type,
        title: entry.title,
        content: entry.content,
        tags: entry.tags || [],
      });
      await deleteEntry(entry.id);
    } catch {
      /* 改种失败时原条目仍在，下次再试 */
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteEntry(id);
    } catch {
      /* 删除失败条目会留在原地，不打扰孩子 */
    }
  };

  /** 树元素点击 = 点罗盘对应卫星（切换筛选） */
  const handleTreeSelect = (type) =>
    setActiveType((cur) => (cur === type ? null : type));

  const goldenGlow = capsules.some((c) => c.unlocked);
  const band = timeBandOf(new Date().getHours());
  const effectiveView = simpleMode ? "week" : view;

  return (
    <div className="planet-page track-child" data-time={band}>
      {/* ---- 顶栏（与聊天页一致的风格） ---- */}
      <header className="planet-header">
        <div className="planet-brand">
          <span aria-hidden="true">🪐</span>
          <span className="planet-brand-name">安心童伴</span>
        </div>
        <AiIdentityBadge />
        <div className="planet-header-right">
          <Link to="/home" className="planet-chat-link">
            🏠 主页
          </Link>
          <Link to="/chat" className="planet-chat-link">
            💬 回去聊天
          </Link>
        </div>
      </header>

      <main className="planet-main">
        {loading && <p className="planet-loading">小星球正在醒来…</p>}
        {error && !loading && (
          <p className="planet-loading" role="alert">
            {error}
          </p>
        )}

        {!loading && !error && (
          <>
            {/* 轻 Hero：纯文本问候 + 一个挑战胶囊条（不抢树的戏） */}
            <PlanetHero username={user?.username || "你"} />

            {/* 生命树（本页灵魂，唯一主角） */}
            <motion.section
              className="planet-tree-section"
              aria-label="生命树"
              {...enter(0)}
            >
              <GrowthTree
                entries={entries}
                weather={weather}
                goldenGlow={goldenGlow}
                activeType={activeType}
                onSelectType={handleTreeSelect}
              />
            </motion.section>

            {/* 星球罗盘：类型筛选 + 树联动 + 空类型种下入口 */}
            <motion.div {...enter(1)}>
              <PlanetCompass
                counts={counts}
                activeType={activeType}
                onSelect={setActiveType}
                onPlant={(t) => setForm({ open: true, presetType: t })}
              />
            </motion.div>

            {/* 条目区：本周 / 种类双视图 */}
            <motion.section
              className="entries-section"
              aria-label="星球条目"
              {...enter(2)}
            >
              <div className="entries-head">
                <div className="entries-title-row">
                  <h2 className="section-title">🌱 星球上的宝贝们</h2>
                  {!simpleMode && (
                    <div className="view-switch" role="tablist" aria-label="浏览方式">
                      <button
                        type="button"
                        role="tab"
                        aria-selected={effectiveView === "week"}
                        className={`view-switch-btn ${
                          effectiveView === "week" ? "view-switch-btn--on" : ""
                        }`}
                        onClick={() => setView("week")}
                      >
                        本周
                      </button>
                      <button
                        type="button"
                        role="tab"
                        aria-selected={effectiveView === "type"}
                        className={`view-switch-btn ${
                          effectiveView === "type" ? "view-switch-btn--on" : ""
                        }`}
                        onClick={() => setView("type")}
                      >
                        种类
                      </button>
                    </div>
                  )}
                </div>
                <p className="section-sub">
                  每一颗星、每一朵云、每一棵芽，都是你愿意留下来的瞬间。
                </p>
              </div>

              <AnimatePresence>
                {notice && (
                  <SproutNotice
                    key="sprout-notice"
                    notice={notice}
                    onRetype={handleRetype}
                    onDismiss={() => setNotice(null)}
                  />
                )}
              </AnimatePresence>

              <div className="entries-actions">
                <PillButton
                  variant="ghost"
                  onClick={() =>
                    setForm({ open: true, presetType: activeType || "star" })
                  }
                >
                  ＋ 种下新东西
                </PillButton>
              </div>

              {entries.length === 0 ? (
                <p className="entries-empty card">
                  你的小星球还是空的。点上面的卫星，种下第一颗吧～
                </p>
              ) : effectiveView === "week" ? (
                <WeekView
                  entries={entries}
                  activeType={activeType}
                  onDelete={handleDelete}
                />
              ) : (
                <TypeView
                  entries={entries}
                  activeType={activeType}
                  onDelete={handleDelete}
                />
              )}

              {/* 共创故事卫星卡 */}
              <CoCreationSatellite />

              <p className="entries-footnote">
                小星球是策展式记忆——AI 只在你主动留下的条目里检索记忆。
              </p>
            </motion.section>

            {/* 时间胶囊花园（未来的惊喜，放在现在的记忆之后） */}
            <motion.div {...enter(3)}>
              <TimeCapsule
                capsules={capsules}
                loaded={capsulesLoaded}
                onCreate={createCapsule}
                onDelete={deleteCapsule}
              />
            </motion.div>
          </>
        )}
      </main>

      {/* 种下新东西：modal / 底部面板 */}
      <AnimatePresence>
        {form.open && (
          <EntryFormModal
            simple={simpleMode}
            presetType={form.presetType}
            onSubmit={handleCreate}
            onClose={() => setForm((f) => ({ ...f, open: false }))}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
