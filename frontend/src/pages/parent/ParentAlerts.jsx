/* ParentAlerts — 风险告警列表
 * 告警卡：RiskBadge + 话题 + 摘要 + 建议区块 + 时间 + 孩子名
 * 支持按风险等级 / 按时间排序切换；空态温和
 */
import { useEffect, useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { apiFetch } from "../../utils/api";
import RiskBadge from "../../components/RiskBadge";
import "./ParentAlerts.css";

function formatTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${mm}-${dd} ${hh}:${mi}`;
}

export default function ParentAlerts() {
  const { children } = useOutletContext();
  const [alerts, setAlerts] = useState(null);
  const [sortBy, setSortBy] = useState("time"); // time | risk
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/api/parent/alerts")
      .then((d) => setAlerts(d.alerts || []))
      .catch((e) => setError(e.message));
  }, []);

  const childName = useMemo(() => {
    const map = {};
    for (const c of children || []) map[c.id] = c.username;
    return map;
  }, [children]);

  const sorted = useMemo(() => {
    if (!alerts) return [];
    const list = [...alerts];
    if (sortBy === "risk") {
      list.sort(
        (a, b) =>
          b.risk_level - a.risk_level ||
          new Date(b.timestamp) - new Date(a.timestamp)
      );
    }
    return list; // time：接口本已时间倒序
  }, [alerts, sortBy]);

  return (
    <div className="parent-page">
      <h1 className="parent-page-title">风险告警</h1>
      <p className="parent-page-desc">
        安全引擎发现的风险信号与陪伴建议。告警是为了帮您更好地守护，而不是责备孩子。
      </p>

      <div className="alerts-toolbar">
        <div className="sort-toggle" role="tablist" aria-label="排序方式">
          <button
            className={`sort-btn${sortBy === "time" ? " active" : ""}`}
            onClick={() => setSortBy("time")}
          >
            按时间
          </button>
          <button
            className={`sort-btn${sortBy === "risk" ? " active" : ""}`}
            onClick={() => setSortBy("risk")}
          >
            按风险等级
          </button>
        </div>
        {alerts && (
          <span className="alerts-count num">共 {alerts.length} 条</span>
        )}
      </div>

      {error && <p className="parent-empty">{error}</p>}
      {!error && alerts === null && <p className="parent-empty">加载中…</p>}
      {!error && alerts !== null && sorted.length === 0 && (
        <p className="parent-empty">
          目前没有任何告警。孩子和安全引擎相处得不错，继续保持。
        </p>
      )}

      <div className="alerts-list">
        {sorted.map((a) => (
          <article
            key={a.id}
            className={`card alert-card${a.acknowledged ? "" : " alert-card-unread"}`}
          >
            <header className="alert-head">
              <RiskBadge level={a.risk_level} showLevel />
              {a.topic && <span className="alert-topic">{a.topic}</span>}
              <span className="alert-meta">
                {childName[a.child_user_id] || "孩子"} ·{" "}
                <time>{formatTime(a.timestamp)}</time>
              </span>
              {!a.acknowledged && <span className="alert-unread-dot" title="未读" />}
            </header>
            <p className="alert-summary">{a.summary}</p>
            {a.suggestion && (
              <div className="alert-suggestion">
                <span className="alert-suggestion-label">建议</span>
                <p>{a.suggestion}</p>
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
