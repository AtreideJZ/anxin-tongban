/* ParentSettings — 守护设置（方案 4.3：真正生效）
 * 话题偏好编辑器：三列互斥多选（允许/限制/禁止），保存写库，
 * 孩子的下一轮对话起生效（Pipeline Step 1 检测）
 */
import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { apiFetch } from "../../utils/api";
import PillButton from "../../components/PillButton";
import "./ParentSettings.css";

/* 话题类别与 core/guardrails.py 的 PREFERENCE_KEYWORDS 保持一致（后端检测用同一清单） */
const TOPIC_CATEGORIES = [
  "游戏",
  "消费",
  "暴力",
  "色情",
  "自伤",
  "危险操作",
  "故事",
  "百科",
  "学习",
  "情绪",
  "安全教育",
];

const COLUMNS = [
  { key: "allowed_topics", icon: "✅", title: "允许", hint: "放心畅聊的话题" },
  { key: "limited_topics", icon: "⚠️", title: "限制", hint: "AI 会避免深入" },
  { key: "forbidden_topics", icon: "🚫", title: "禁止", hint: "命中即安全引导" },
];

const EMPTY_PREF = {
  allowed_topics: [],
  limited_topics: [],
  forbidden_topics: [],
};

export default function ParentSettings() {
  const { selectedChild, selectedChildId } = useOutletContext();
  const [pref, setPref] = useState(EMPTY_PREF);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setSaved(false);
    setError("");
    if (!selectedChildId) {
      setPref(EMPTY_PREF);
      return;
    }
    setLoading(true);
    apiFetch(`/api/parent/preferences?child_id=${selectedChildId}`)
      .then((d) => {
        const p = d.preferences || {};
        setPref({
          allowed_topics: p.allowed_topics || [],
          limited_topics: p.limited_topics || [],
          forbidden_topics: p.forbidden_topics || [],
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selectedChildId]);

  /* 三列互斥：点某列的 chip → 该话题归入此列（再点取消），其余列移除 */
  const toggle = (columnKey, topic) => {
    setSaved(false);
    setPref((cur) => {
      const next = {
        allowed_topics: cur.allowed_topics.filter((t) => t !== topic),
        limited_topics: cur.limited_topics.filter((t) => t !== topic),
        forbidden_topics: cur.forbidden_topics.filter((t) => t !== topic),
      };
      if (!cur[columnKey].includes(topic)) {
        next[columnKey] = [...next[columnKey], topic];
      }
      return next;
    });
  };

  const save = async () => {
    if (!selectedChildId) return;
    setSaving(true);
    setError("");
    try {
      await apiFetch("/api/parent/preferences", {
        method: "PUT",
        body: { child_id: selectedChildId, ...pref },
      });
      setSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="parent-page">
      <h1 className="parent-page-title">守护设置</h1>
      <p className="parent-page-desc">
        为 {selectedChild ? selectedChild.username : "孩子"}{" "}
        定制话题边界。设置保存后立即生效——孩子的下一轮对话就会按新边界来。
      </p>

      {saved && (
        <div className="save-banner" role="status">
          已生效——孩子的下一轮对话起生效。
        </div>
      )}
      {error && <p className="parent-empty">{error}</p>}

      {/* 话题偏好编辑器 */}
      <section className="card settings-card">
        <h2 className="card-title">话题偏好</h2>
        {!selectedChildId ? (
          <p className="parent-empty">请先在右上角选择一个孩子。</p>
        ) : loading ? (
          <p className="parent-empty">加载中…</p>
        ) : (
          <>
            <div className="pref-columns">
              {COLUMNS.map((col) => (
                <div className="pref-column" key={col.key}>
                  <h3 className="pref-column-title">
                    {col.icon} {col.title}
                    <span className="pref-column-hint">{col.hint}</span>
                  </h3>
                  <div className="pref-chips">
                    {TOPIC_CATEGORIES.map((topic) => {
                      const active = pref[col.key].includes(topic);
                      return (
                        <button
                          key={topic}
                          className={`pref-chip pref-chip-${col.key}${
                            active ? " active" : ""
                          }`}
                          aria-pressed={active}
                          onClick={() => toggle(col.key, topic)}
                        >
                          {topic}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
            <div className="pref-actions">
              <PillButton onClick={save} disabled={saving}>
                {saving ? "保存中…" : "保存设置"}
              </PillButton>
            </div>
          </>
        )}
      </section>

      {/* 效果说明 */}
      <section className="card settings-card">
        <h2 className="card-title">这些设置会怎样影响对话？</h2>
        <ul className="effect-list">
          <li>
            <strong>🚫 禁止</strong>：孩子聊到该话题时，安全引擎会提升风险等级，
            转为温和的安全引导，并根据等级给您发送提醒。
          </li>
          <li>
            <strong>⚠️ 限制</strong>：AI 会避免深入讨论该话题，自然地把对话引向其他方向。
          </li>
          <li>
            <strong>✅ 允许</strong>：您标记放心的方向，作为家庭约定的一份记录。
          </li>
        </ul>
      </section>

      {/* 守护/过渡/信任模式说明（方案 4.2 + v2.2 三档化：家长可见性） */}
      <section className="card settings-card">
        <h2 className="card-title">守护、过渡与信任模式</h2>
        <div className="mode-compare">
          <div className="mode-col">
            <h3 className="mode-col-title">守护模式 · 5-10 岁</h3>
            <ul>
              <li>每次对话后生成摘要与必要提醒</li>
              <li>星球条目数量可见（只看数量，不看内容）</li>
              <li>回复更简短、选题更稳妥</li>
            </ul>
          </div>
          <div className="mode-col">
            <h3 className="mode-col-title">过渡模式 · 11-13 岁</h3>
            <ul>
              <li>每周生成一次对话摘要，高风险时即时告警</li>
              <li>星球默认私密，由孩子选择分享给家长</li>
              <li>支持身份探索话题，回复可适度深入</li>
            </ul>
          </div>
          <div className="mode-col">
            <h3 className="mode-col-title">信任模式 · 14 岁及以上</h3>
            <ul>
              <li>仅高风险时向您告警</li>
              <li>星球完全私密，家长不可见</li>
              <li>回复可适度深入，选题更广泛</li>
            </ul>
          </div>
        </div>
        <p className="mode-note">
          模式由孩子注册时的年龄档自动决定。我们相信：渐进的信任，本身就是成长的一部分。
        </p>
      </section>
    </div>
  );
}
