/* Landing — 入口页：品牌区 + 登录/注册切换卡片
 * 注册合规点（4.8）：监护人同意必勾，不勾禁用提交并提示
 * 登录/注册成功后按角色跳转：child → /home（儿童主页），parent → /parent
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../hooks/useAuth";
import PillButton from "../components/PillButton";
import "./Landing.css";

const AGE_TIERS = [
  { value: "5-7", label: "5-7 岁" },
  { value: "8-10", label: "8-10 岁" },
  { value: "11-13", label: "11-13 岁" },
  { value: "14", label: "14 岁及以上" },
];

const ROLES = [
  { value: "child", label: "我是孩子", emoji: "🧒" },
  { value: "parent", label: "我是家长", emoji: "👨‍👩‍👧" },
];

export default function Landing() {
  const [mode, setMode] = useState("login"); // login | register
  const [form, setForm] = useState({
    username: "",
    pin: "",
    age_tier: "",
    role: "child",
    guardian_consent: false,
    parent_username: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const set = (key) => (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
  };

  const goByRole = (user) => {
    navigate(user.role === "parent" ? "/parent" : "/home", { replace: true });
  };

  // 注册提交前置校验：监护人同意不勾则禁用提交（按钮 disabled + 提示文案双保险）
  const canSubmitRegister =
    form.username.trim().length >= 2 &&
    /^\d{4}$/.test(form.pin) &&
    form.role &&
    (form.role === "parent" || form.age_tier) &&
    form.guardian_consent;

  const canSubmitLogin = form.username.trim() && /^\d{4}$/.test(form.pin);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (mode === "login") {
        const user = await login(form.username.trim(), form.pin);
        goByRole(user);
      } else {
        const payload = {
          username: form.username.trim(),
          pin: form.pin,
          role: form.role,
          guardian_consent: form.guardian_consent,
        };
        if (form.role === "child") {
          payload.age_tier = form.age_tier;
          if (form.parent_username.trim()) {
            payload.parent_username = form.parent_username.trim();
          }
        }
        const user = await register(payload);
        goByRole(user);
      }
    } catch (err) {
      setError(err.message || "出了点小问题，请再试一次");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="landing track-child">
      {/* 品牌区 */}
      <motion.header
        className="landing-brand"
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 260, damping: 26 }}
      >
        <div className="landing-logo" aria-hidden="true">
          🪐
        </div>
        <h1 className="landing-title">安心童伴</h1>
        <p className="landing-slogan">
          一个会认真倾听、先把安全放在心上的 AI 好伙伴
        </p>
      </motion.header>

      {/* 登录/注册切换卡片 */}
      <motion.main
        className="landing-card card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 280, damping: 28, delay: 0.08 }}
      >
        <div className="landing-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={mode === "login"}
            className={`landing-tab ${mode === "login" ? "landing-tab--active" : ""}`}
            onClick={() => {
              setMode("login");
              setError("");
            }}
          >
            登录
          </button>
          <button
            role="tab"
            aria-selected={mode === "register"}
            className={`landing-tab ${mode === "register" ? "landing-tab--active" : ""}`}
            onClick={() => {
              setMode("register");
              setError("");
            }}
          >
            注册
          </button>
        </div>

        <form className="landing-form" onSubmit={handleSubmit}>
          <label className="landing-field">
            <span>用户名</span>
            <input
              type="text"
              value={form.username}
              onChange={set("username")}
              placeholder="给自己起个名字吧（至少 2 个字）"
              autoComplete="username"
            />
          </label>

          <label className="landing-field">
            <span>4 位数字 PIN 码</span>
            <input
              type="password"
              inputMode="numeric"
              maxLength={4}
              value={form.pin}
              onChange={set("pin")}
              placeholder="4 个数字，是你的小钥匙"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </label>

          {mode === "register" && (
            <>
              <div className="landing-field">
                <span>你是谁呀？</span>
                <div className="choice-row">
                  {ROLES.map((r) => (
                    <button
                      key={r.value}
                      type="button"
                      className={`choice-card ${
                        form.role === r.value ? "choice-card--active" : ""
                      }`}
                      onClick={() => setForm((f) => ({ ...f, role: r.value }))}
                    >
                      <span aria-hidden="true">{r.emoji}</span> {r.label}
                    </button>
                  ))}
                </div>
              </div>

              {form.role === "child" && (
                <>
                  <div className="landing-field">
                    <span>你几岁啦？</span>
                    <div className="choice-row">
                      {AGE_TIERS.map((t) => (
                        <button
                          key={t.value}
                          type="button"
                          className={`choice-card ${
                            form.age_tier === t.value ? "choice-card--active" : ""
                          }`}
                          onClick={() =>
                            setForm((f) => ({ ...f, age_tier: t.value }))
                          }
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <label className="landing-field">
                    <span>家长用户名（选填，用于关联家长账号）</span>
                    <input
                      type="text"
                      value={form.parent_username}
                      onChange={set("parent_username")}
                      placeholder="爸爸妈妈的账号名"
                    />
                  </label>
                </>
              )}

              {/* 监护人同意（合规 4.8，必勾） */}
              <label className="consent-row">
                <input
                  type="checkbox"
                  checked={form.guardian_consent}
                  onChange={set("guardian_consent")}
                />
                <span>
                  我的监护人（爸爸/妈妈或其他家长）已知晓并同意我使用安心童伴
                </span>
              </label>
              {!form.guardian_consent && (
                <p className="consent-hint">
                  需要先请爸爸妈妈同意并勾选上面的选项，才能开始哦
                </p>
              )}
            </>
          )}

          {error && (
            <p className="landing-error" role="alert">
              {error}
            </p>
          )}

          <PillButton
            type="submit"
            disabled={
              submitting ||
              (mode === "login" ? !canSubmitLogin : !canSubmitRegister)
            }
            className="landing-submit"
          >
            {submitting
              ? "请稍等…"
              : mode === "login"
                ? "出发！"
                : "注册并开始"}
          </PillButton>
        </form>
      </motion.main>

      <footer className="landing-footer">
        安心童伴是 AI 程序，不是真人 · 所有对话都会经过安全检查
      </footer>
    </div>
  );
}
