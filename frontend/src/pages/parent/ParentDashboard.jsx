/* ParentDashboard — 家长仪表盘
 * 统计卡行 + 7 日风险趋势（柱色按 max_risk_level 映射语义色）
 * + 话题分布 + 情绪趋势（空态温和）+ 星球概览（仅计数）
 */
import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiFetch } from "../../utils/api";
import RiskBadge from "../../components/RiskBadge";
import "./ParentDashboard.css";

const RISK_COLORS = [
  "var(--risk-0)",
  "var(--risk-1)",
  "var(--risk-2)",
  "var(--risk-3)",
];

const EMOTION_META = [
  { key: "positive", label: "积极", color: "var(--risk-0)" },
  { key: "neutral", label: "平和", color: "var(--accent)" },
  { key: "slightly_negative", label: "略低落", color: "var(--risk-1)" },
  { key: "negative", label: "低落", color: "var(--risk-3)" },
];

const PLANET_META = [
  { key: "star", label: "好奇星" },
  { key: "cloud", label: "心情云" },
  { key: "sprout", label: "探索芽" },
  { key: "story", label: "故事册" },
  { key: "capsule", label: "时间胶囊" },
];

function formatMinutes(min) {
  if (!min) return "0 分钟";
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h > 0 ? `${h} 小时 ${m} 分钟` : `${m} 分钟`;
}

export default function ParentDashboard() {
  const { selectedChild, selectedChildId } = useOutletContext();
  const [dash, setDash] = useState(null);
  const [emotion, setEmotion] = useState(null);
  const [planet, setPlanet] = useState(null);
  const [familyStories, setFamilyStories] = useState(null); // 共创故事（v2.2 C）
  const [expandedStory, setExpandedStory] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/api/parent/dashboard")
      .then(setDash)
      .catch((e) => setError(e.message));
  }, []);

  // 共创故事：仅孩子主动点「给爸爸妈妈看」的成品（默认孩子私密）
  useEffect(() => {
    apiFetch("/api/cocreation/family-stories")
      .then((d) => setFamilyStories(d.stories || []))
      .catch(() => setFamilyStories([]));
  }, []);

  // 情绪趋势按当前选中的孩子独立统计（per-user 隔离，方案 3.4）
  useEffect(() => {
    if (!selectedChildId) {
      setEmotion(null);
      setPlanet(null);
      return;
    }
    apiFetch(`/api/parent/emotion-trend?child_id=${selectedChildId}`)
      .then((d) => setEmotion(d.emotion_trend_7d))
      .catch(() => setEmotion(null));
    apiFetch(`/api/parent/planet-overview?child_id=${selectedChildId}`)
      .then(setPlanet)
      .catch(() => setPlanet(null));
  }, [selectedChildId]);

  if (error) return <div className="parent-page"><p className="parent-empty">{error}</p></div>;
  if (!dash) return <div className="parent-page"><p className="parent-empty">加载中…</p></div>;

  const topicData = Object.entries(dash.topic_distribution || {}).map(
    ([topic, count]) => ({ topic, count })
  );
  const emotionTotal = emotion
    ? Object.values(emotion).reduce((a, b) => a + b, 0)
    : 0;
  const hasTrend = (dash.risk_trend_7d || []).some((d) => d.alert_count > 0);

  return (
    <div className="parent-page">
      <h1 className="parent-page-title">守护仪表盘</h1>
      <p className="parent-page-desc">
        了解孩子的使用概况与风险信号——守护而非监视，细节只属于孩子。
      </p>

      {/* 统计卡行 */}
      <section className="stat-row">
        <div
          className={`card stat-card${
            dash.unacknowledged_alerts > 0 ? " stat-card-attention" : ""
          }`}
        >
          <div className="stat-label">本周告警</div>
          <div className="stat-value num">{dash.alerts_7d}</div>
          <div className="stat-sub">
            {dash.unacknowledged_alerts > 0
              ? `${dash.unacknowledged_alerts} 条未读`
              : "全部已读"}
          </div>
        </div>
        <div className="card stat-card">
          <div className="stat-label">累计使用时长</div>
          <div className="stat-value num">
            {formatMinutes(dash.usage_minutes_total)}
          </div>
          <div className="stat-sub">全部孩子合计</div>
        </div>
        <div className="card stat-card">
          <div className="stat-label">当前孩子</div>
          <div className="stat-value stat-value-mode">
            {selectedChild ? (
              <>
                {selectedChild.username}
                <span className="mode-badge">
                  {["5-7", "8-10"].includes(selectedChild.age_tier)
                    ? "守护模式"
                    : selectedChild.age_tier === "11-13"
                      ? "过渡模式"
                      : "信任模式"}
                </span>
              </>
            ) : (
              "—"
            )}
          </div>
          <div className="stat-sub">
            {selectedChild ? `${selectedChild.age_tier} 岁` : "未选择孩子"}
          </div>
        </div>
      </section>

      {/* 图表行 */}
      <section className="chart-row">
        <div className="card chart-card">
          <h2 className="card-title">7 日风险趋势</h2>
          {hasTrend ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={dash.risk_trend_7d}>
                <XAxis
                  dataKey="date"
                  tickFormatter={(d) => d.slice(5)}
                  fontSize={12}
                  stroke="var(--muted)"
                />
                <YAxis allowDecimals={false} fontSize={12} stroke="var(--muted)" />
                <Tooltip
                  formatter={(value, name) =>
                    name === "alert_count" ? [value, "告警数"] : [value, name]
                  }
                  labelFormatter={(d) => `日期：${d}`}
                />
                <Bar dataKey="alert_count" radius={[6, 6, 0, 0]}>
                  {dash.risk_trend_7d.map((d) => (
                    <Cell
                      key={d.date}
                      fill={RISK_COLORS[d.max_risk_level] || RISK_COLORS[0]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="parent-empty">最近 7 天没有告警，一切安好。</p>
          )}
          <p className="chart-note">柱色对应当日最高风险等级（绿→红）。</p>
        </div>

        <div className="card chart-card">
          <h2 className="card-title">告警话题分布</h2>
          {topicData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={topicData} layout="vertical">
                <XAxis type="number" allowDecimals={false} fontSize={12} stroke="var(--muted)" />
                <YAxis
                  type="category"
                  dataKey="topic"
                  width={110}
                  fontSize={12}
                  stroke="var(--muted)"
                />
                <Tooltip formatter={(value) => [value, "次数"]} />
                <Bar dataKey="count" fill="var(--accent)" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="parent-empty">还没有话题数据。</p>
          )}
        </div>
      </section>

      {/* 情绪趋势 + 星球概览 */}
      <section className="chart-row">
        <div className="card chart-card">
          <h2 className="card-title">近 7 天情绪趋势</h2>
          {emotion && emotionTotal > 0 ? (
            <div className="emotion-bars">
              {EMOTION_META.map((m) => {
                const n = emotion[m.key] || 0;
                const pct = Math.round((n / emotionTotal) * 100);
                return (
                  <div className="emotion-row" key={m.key}>
                    <span className="emotion-label">{m.label}</span>
                    <span className="emotion-track">
                      <span
                        className="emotion-fill"
                        style={{ width: `${pct}%`, background: m.color }}
                      />
                    </span>
                    <span className="emotion-count num">{n} 次</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="parent-empty">
              还没有情绪数据，孩子聊几天就有了。
            </p>
          )}
        </div>

        <div className="card chart-card">
          <h2 className="card-title">星球概览</h2>
          {!selectedChild ? (
            <p className="parent-empty">请先在右上角选择一个孩子。</p>
          ) : planet?.visible ? (
            <>
              <div className="planet-counts">
                {PLANET_META.map((m) => (
                  <div className="planet-count" key={m.key}>
                    <span className="planet-count-value num">
                      {planet.counts?.[m.key] ?? 0}
                    </span>
                    <span className="planet-count-label">{m.label}</span>
                  </div>
                ))}
              </div>
              <p className="chart-note">
                只看数量，不看内容——星球里的具体条目属于孩子自己。
              </p>
            </>
          ) : (
            <div className="trust-card">
              <RiskBadge level={0} />
              <p>
                {planet?.reason ||
                  "过渡/信任模式（11 岁及以上）：星球内容对孩子私密，家长不可见。"}
              </p>
            </div>
          )}
        </div>
      </section>

      {/* 共创故事（v2.2 C）：孩子主动分享的成品，可展开读全文 */}
      <section className="chart-row">
        <div className="card chart-card">
          <h2 className="card-title">共创故事</h2>
          {familyStories === null ? (
            <p className="parent-empty">加载中…</p>
          ) : familyStories.length === 0 ? (
            <p className="parent-empty">孩子分享的共创故事会出现在这里。</p>
          ) : (
            <ul className="family-story-list">
              {familyStories.map((s) => (
                <li key={s.id} className="family-story-item">
                  <button
                    type="button"
                    className="family-story-head"
                    onClick={() =>
                      setExpandedStory(expandedStory === s.id ? null : s.id)
                    }
                    aria-expanded={expandedStory === s.id}
                  >
                    <span className="family-story-title">📖 {s.title}</span>
                    <span className="family-story-meta">
                      {s.child_username} · {String(s.created_at).slice(0, 10)}
                    </span>
                  </button>
                  {expandedStory === s.id && (
                    <p className="family-story-text">{s.final_text}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
          <p className="chart-note">
            只有孩子主动点「给爸爸妈妈看」的成品才会出现在这里。
          </p>
        </div>
      </section>
    </div>
  );
}
