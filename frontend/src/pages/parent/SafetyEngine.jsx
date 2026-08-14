/* SafetyEngine — 安全引擎可视化 + 安全演示台（.dark-safety 深色作用域，全站唯一深色页）
 * 上半：10 步 Pipeline 决策链架构图（LLM 节点与本地节点视觉区分）
 * 下半：安全演示台——7 个预设案例 / 自定义输入 → 调 /api/parent/safety-demo
 *       → 按 ~300ms 间隔逐步点亮返回的 steps → 展示最终回复与关键判定
 */
import { useEffect, useRef, useState } from "react";
import { apiFetch } from "../../utils/api";
import RiskBadge from "../../components/RiskBadge";
import "./SafetyEngine.css";

/* 8 步决策链（与 core/pipeline.py 的步骤一一对应；4-5 在危机路径合并为一个步骤） */
const NODES = [
  { id: "0", name: "记忆检索", kind: "local", desc: "调取三层记忆：星球策展 + 情景摘要" },
  { id: "1", name: "关键词检测", kind: "local", desc: "本地规则库初筛风险与家长话题偏好" },
  { id: "2", name: "风险分类", kind: "llm", desc: "LLM 语义理解，输出话题、风险等级与对话模式" },
  { id: "3", name: "策略决策", kind: "local", desc: "按年龄档与风险等级选择回应策略" },
  { id: "4", name: "Prompt 构建", kind: "local", desc: "组装年龄适配的系统提示词" },
  { id: "5", name: "回复生成", kind: "llm", desc: "LLM 生成候选回复" },
  { id: "6", name: "批判 Agent 审计", kind: "llm", desc: "语义审计：谄媚、依赖、不当引导" },
  { id: "6b", name: "输出拦截替换", kind: "local", desc: "审计告警时整段替换为安全模板" },
];

const STEP_INTERVAL_MS = 300;

export default function SafetyEngine() {
  const [cases, setCases] = useState([]);
  const [input, setInput] = useState("");
  const [ageTier, setAgeTier] = useState("8-10");
  const [activeCaseId, setActiveCaseId] = useState(null);

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [litCount, setLitCount] = useState(0);
  const [error, setError] = useState("");
  const timerRef = useRef(null);

  useEffect(() => {
    apiFetch("/api/parent/demo-cases")
      .then((d) => setCases(d.cases || []))
      .catch(() => setCases([]));
  }, []);

  /* 逐步点亮：result 到位后按 300ms 间隔激活 steps */
  useEffect(() => {
    if (!result) return undefined;
    setLitCount(0);
    timerRef.current = setInterval(() => {
      setLitCount((n) => {
        if (n >= result.steps.length) {
          clearInterval(timerRef.current);
          return n;
        }
        return n + 1;
      });
    }, STEP_INTERVAL_MS);
    return () => clearInterval(timerRef.current);
  }, [result]);

  const pickCase = (c) => {
    setActiveCaseId(c.id);
    setInput(c.preset_input);
  };

  const run = async () => {
    const text = input.trim();
    if (!text || running) return;
    setRunning(true);
    setError("");
    setResult(null);
    setLitCount(0);
    try {
      const body = await apiFetch("/api/parent/safety-demo", {
        method: "POST",
        body: { input: text, age_tier: ageTier, mode: "chat" },
      });
      setResult(body);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  /* 节点 → 返回步骤（危机路径 4/5 合并为 "4-5"） */
  const stepFor = (nodeId) => {
    if (!result) return null;
    return (
      result.steps.find((s) => s.step === nodeId) ||
      ((nodeId === "4" || nodeId === "5") &&
        result.steps.find((s) => s.step === "4-5")) ||
      null
    );
  };

  const litNodeIds = new Set();
  if (result) {
    for (const s of result.steps.slice(0, litCount)) {
      if (s.step === "4-5") {
        litNodeIds.add("4");
        litNodeIds.add("5");
      } else {
        litNodeIds.add(s.step);
      }
    }
  }
  const finished = result && litCount >= result.steps.length;

  return (
    <div className="dark-safety safety-engine">
      <div className="safety-inner">
        <h1 className="safety-title">安全引擎</h1>
        <p className="safety-desc">
          孩子的每一句回复，都要走完这条 8 步决策链才会出现在对话框里。
        </p>

        {/* 决策链可视化 */}
        <section className="node-chain" aria-label="Pipeline 决策链">
          {NODES.map((node, i) => {
            const step = stepFor(node.id);
            const lit = litNodeIds.has(node.id);
            const tone =
              lit && node.id === "6b"
                ? "unsafe"
                : lit
                ? "lit"
                : "";
            return (
              <div className="node-wrap" key={node.id}>
                <div className={`node-card node-${node.kind} ${lit ? "on" : ""} ${tone}`}>
                  <div className="node-head">
                    <span className="node-step num">Step {node.id}</span>
                    <span className={`node-kind node-kind-${node.kind}`}>
                      {node.kind === "llm" ? "LLM" : "本地"}
                    </span>
                  </div>
                  <div className="node-name">{node.name}</div>
                  <div className="node-desc">{node.desc}</div>
                  {lit && step && (
                    <div className="node-live">
                      <p className="node-output">{step.output_summary}</p>
                      <span className="node-latency num">{step.latency_ms}ms</span>
                    </div>
                  )}
                </div>
                {i < NODES.length - 1 && (
                  <span className={`node-arrow${lit ? " on" : ""}`} aria-hidden="true">
                    →
                  </span>
                )}
              </div>
            );
          })}
        </section>

        {/* 安全演示台 */}
        <section className="demo-console">
          <h2 className="demo-title">安全演示台</h2>
          <p className="demo-desc">
            选择一个预设案例或输入自定义内容，看安全引擎如何一步步处理。演示不进入孩子的对话记录。
          </p>

          <div className="demo-cases">
            {cases.map((c) => (
              <button
                key={c.id}
                className={`demo-case-btn${activeCaseId === c.id ? " active" : ""}`}
                onClick={() => pickCase(c)}
                title={c.goal}
              >
                <span aria-hidden="true">{c.emoji}</span> {c.name}
              </button>
            ))}
          </div>

          <div className="demo-input-row">
            <textarea
              className="demo-input"
              rows={2}
              placeholder="输入一句孩子可能说的话，例如：我不想活了"
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                setActiveCaseId(null);
              }}
            />
            <div className="demo-controls">
              <select
                className="demo-age"
                value={ageTier}
                onChange={(e) => setAgeTier(e.target.value)}
                aria-label="年龄档"
              >
                <option value="5-7">5-7 岁</option>
                <option value="8-10">8-10 岁</option>
                <option value="11-13">11-13 岁</option>
                <option value="14">14 岁及以上</option>
              </select>
              <button
                className="btn-pill demo-run"
                onClick={run}
                disabled={running || !input.trim()}
              >
                {running ? "引擎运行中…" : "运行演示"}
              </button>
            </div>
          </div>

          {error && <p className="demo-error">{error}</p>}
          {running && (
            <p className="demo-running" role="status">
              安全引擎正在运行，决策链即将逐步点亮…
            </p>
          )}

          {/* 最终结果 */}
          {finished && (
            <div className="demo-result">
              <div className="demo-reply-card">
                <span className="demo-reply-label">孩子最终看到的回复</span>
                <p className="demo-reply-text">{result.final_reply}</p>
              </div>
              <div className="demo-judgments">
                <div className="judge-item">
                  <span className="judge-label">风险等级</span>
                  <RiskBadge level={result.risk_level} showLevel />
                </div>
                <div className="judge-item">
                  <span className="judge-label">回应策略</span>
                  <span className="judge-value">{result.strategy}</span>
                </div>
                <div className="judge-item">
                  <span className="judge-label">危机模板</span>
                  <span className={`judge-value ${result.used_crisis_template ? "judge-alert" : ""}`}>
                    {result.used_crisis_template ? "已启用" : "未启用"}
                  </span>
                </div>
                <div className="judge-item">
                  <span className="judge-label">输出拦截</span>
                  <span className={`judge-value ${result.critic_intercepted ? "judge-alert" : ""}`}>
                    {result.critic_intercepted ? "已拦截替换" : "未触发"}
                  </span>
                </div>
                <div className="judge-item">
                  <span className="judge-label">家长提醒</span>
                  <span className={`judge-value ${result.parent_alert ? "judge-alert" : ""}`}>
                    {result.parent_alert ? "已生成" : "无"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
