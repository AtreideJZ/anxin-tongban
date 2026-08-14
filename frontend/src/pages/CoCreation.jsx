/* ============================================================
 * CoCreation — 共创故事（儿童轨，v2.2 拓展方向 C，本期核心交付）
 *
 * 流程（docs/v2.2-拓展方向.md 5.1）：
 *   开始（AI 生成开头，留白）→ 孩子/家长同设备轮流接一段
 *   → AI 轻量引导（只提问不代写）→ ✨ 完成润色（只改语法/错别字）
 *   → 成品标注共同作者 → 自动种小星球 → 孩子主动分享给家长
 *
 * 儿童端 UI 纪律：不显示风险等级 / 决策链 / 技术步骤名。
 * 孩子的每段输入在后端走完整 Pipeline 审计；被拒绝的内容不入故事，
 * 本页只把安心童伴的安全回应以气泡展示。
 * ============================================================ */

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { apiFetch, getStoredUser } from "../utils/api";
import PillButton from "../components/PillButton";
import AiIdentityBadge from "../components/AiIdentityBadge";
import "./CoCreation.css";

/* 气泡署名：ai=安心童伴，child=孩子名，parent=爸爸/妈妈 */
function speakerOf(turn, childName) {
  if (turn.role === "ai") return "安心童伴";
  if (turn.role === "parent") return "爸爸/妈妈";
  return childName;
}

export default function CoCreation() {
  const user = getStoredUser();
  const childName = user?.username || "你";

  const [story, setStory] = useState(null); // 进行中的故事（服务端 turns 为准）
  const [rejects, setRejects] = useState([]); // 被拒绝时安心童伴的回应气泡（本地展示，不入故事）
  const [title, setTitle] = useState("");
  const [role, setRole] = useState("child"); // 同设备轮流：我是孩子 / 我是家长
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [suggestFinalize, setSuggestFinalize] = useState(false);
  const [finalData, setFinalData] = useState(null); // 成品（finalize 响应）
  const [shared, setShared] = useState(false);

  /* 把服务端 turns 与被拒绝的回应按发生位置交织成展示流 */
  const bubbles = useMemo(() => {
    if (!story) return [];
    const items = [];
    (story.turns || []).forEach((t, i) => {
      items.push({ ...t, key: `t${i}` });
      rejects
        .filter((r) => r.after === i + 1)
        .forEach((r, j) =>
          items.push({ role: "ai", kind: "reject", content: r.content, key: `r${i}-${j}` })
        );
    });
    return items;
  }, [story, rejects]);

  /** 发起故事：AI 生成开头（30-50 字，留白） */
  const handleStart = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const data = await apiFetch("/api/cocreation/story/start", {
        method: "POST",
        body: title.trim() ? { title: title.trim() } : {},
      });
      setStory(data.story);
      setRejects([]);
      setFinalData(null);
      setShared(false);
      setSuggestFinalize(false);
    } catch (err) {
      setError(err.message || "没有开始成功，再试一次吧");
    } finally {
      setBusy(false);
    }
  };

  /** 接一段：accepted=false 时把安全回应以安心童伴气泡展示（原文不入故事） */
  const handleTurn = async () => {
    const content = input.trim();
    if (!content || busy || !story) return;
    setBusy(true);
    setError(null);
    try {
      const data = await apiFetch("/api/cocreation/story/turn", {
        method: "POST",
        body: { story_id: story.id, role, content },
      });
      if (data.accepted) {
        setStory(data.story);
        setSuggestFinalize(Boolean(data.suggest_finalize));
      } else if (data.ai_response) {
        // 这一段没有写进故事；安心童伴的回应直接展示给孩子
        setRejects((prev) => [
          ...prev,
          { after: (data.story?.turns || []).length, content: data.ai_response },
        ]);
      }
      setInput("");
    } catch (err) {
      setError(err.message || "这一段没接上，再试一次吧");
    } finally {
      setBusy(false);
    }
  };

  /** ✨ 完成润色：只改语法/错别字，成品自动种小星球 */
  const handleFinalize = async () => {
    if (busy || !story) return;
    setBusy(true);
    setError(null);
    try {
      const data = await apiFetch("/api/cocreation/story/finalize", {
        method: "POST",
        body: { story_id: story.id },
      });
      setFinalData(data);
      setStory(data.story);
    } catch (err) {
      setError(err.message || "润色没成功，再试一次吧");
    } finally {
      setBusy(false);
    }
  };

  /** 给爸爸妈妈看：孩子主动分享，成品默认私密 */
  const handleShare = async () => {
    if (busy || !story) return;
    setBusy(true);
    try {
      await apiFetch(`/api/cocreation/story/${story.id}/share`, { method: "POST" });
      setShared(true);
    } catch (err) {
      setError(err.message || "分享没成功，再试一次吧");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="co-page track-child">
      {/* ---- 顶栏（与星球页同风格） ---- */}
      <header className="co-header">
        <div className="co-brand">
          <span aria-hidden="true">🪐</span>
          <span className="co-brand-name">安心童伴</span>
        </div>
        <AiIdentityBadge />
        <div className="co-header-right">
          <Link to="/planet" className="co-nav-link">
            🪐 我的小星球
          </Link>
          <Link to="/chat" className="co-nav-link">
            💬 回去聊天
          </Link>
        </div>
      </header>

      <main className="co-main">
        <div className="co-head">
          <h1 className="co-title">📖 共创故事</h1>
          <p className="co-sub">
            和爸爸妈妈一起，一人一段写故事。安心童伴只帮忙引导和改错别字，故事是你们自己写的。
          </p>
        </div>

        {/* ---- 开始 ---- */}
        {!story && (
          <div className="card co-start">
            <label className="co-field">
              <span>给故事起个名字（可以不填，我们帮你起）</span>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="比如：会飞的小鲸鱼"
                maxLength={64}
              />
            </label>
            <PillButton onClick={handleStart} disabled={busy}>
              {busy ? "安心童伴在想开头…" : "✨ 开始共创故事"}
            </PillButton>
          </div>
        )}

        {/* ---- 故事气泡流 ---- */}
        {story && (
          <div className="co-flow" aria-live="polite">
            <AnimatePresence initial={false}>
              {bubbles.map((t) => (
                <motion.div
                  key={t.key}
                  className={`co-bubble co-bubble--${t.role}${
                    t.kind === "guide" ? " co-bubble--guide" : ""
                  }${t.kind === "reject" ? " co-bubble--reject" : ""}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ type: "spring", stiffness: 300, damping: 26 }}
                >
                  <div className="co-bubble-speaker">
                    {speakerOf(t, childName)}
                    {t.kind === "guide" && <span className="co-bubble-tag">💡 小提示</span>}
                  </div>
                  <div className="co-bubble-text">{t.content}</div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}

        {/* ---- 轮流输入（成品完成前） ---- */}
        {story && !finalData && (
          <div className="card co-compose">
            <div className="co-role-switch" role="group" aria-label="轮到谁接故事">
              <button
                type="button"
                className={`co-role-pill ${role === "child" ? "co-role-pill--on" : ""}`}
                onClick={() => setRole("child")}
                aria-pressed={role === "child"}
              >
                我是孩子
              </button>
              <button
                type="button"
                className={`co-role-pill ${role === "parent" ? "co-role-pill--on" : ""}`}
                onClick={() => setRole("parent")}
                aria-pressed={role === "parent"}
              >
                我是家长
              </button>
            </div>
            <textarea
              className="co-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                role === "child"
                  ? "轮到你了，接下一段故事吧…"
                  : "爸爸妈妈，接一段故事吧…"
              }
              rows={3}
              maxLength={500}
            />
            <div className="co-actions">
              <PillButton onClick={handleTurn} disabled={busy || !input.trim()}>
                {busy ? "正在接…" : "接一段 📮"}
              </PillButton>
              <PillButton
                variant={suggestFinalize ? "primary" : "ghost"}
                onClick={handleFinalize}
                disabled={busy}
                className={suggestFinalize ? "co-finalize--suggested" : ""}
              >
                ✨ 完成润色
              </PillButton>
            </div>
            {suggestFinalize && (
              <p className="co-suggest-hint">故事差不多长啦，可以点「完成润色」收尾哦～</p>
            )}
          </div>
        )}

        {/* ---- 成品页 ---- */}
        {finalData && (
          <motion.div
            className="card co-final"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 24 }}
          >
            <h2 className="co-final-title">📖 {finalData.story.title}</h2>
            <p className="co-final-authors">{finalData.authors}</p>
            <p className="co-final-text">{finalData.final_text}</p>
            <p className="co-final-planet">
              已种到你的小星球 📖 故事册里啦！
              <Link to="/planet" className="co-final-planet-link">
                去看看 →
              </Link>
            </p>
            <div className="co-actions">
              {shared ? (
                <p className="co-shared-note">爸爸妈妈现在可以看到啦 💛</p>
              ) : (
                <PillButton variant="ghost" onClick={handleShare} disabled={busy}>
                  给爸爸妈妈看
                </PillButton>
              )}
              <PillButton
                variant="ghost"
                onClick={() => {
                  setStory(null);
                  setFinalData(null);
                  setTitle("");
                  setRejects([]);
                }}
              >
                再写一篇
              </PillButton>
            </div>
          </motion.div>
        )}

        {error && (
          <p className="co-error" role="alert">
            {error}
          </p>
        )}
      </main>
    </div>
  );
}
