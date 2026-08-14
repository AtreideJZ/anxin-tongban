/* ParentLayout — 家长端共享布局（.track-parent 作用域）
 * 顶栏：品牌 + 导航（仪表盘/风险告警/守护设置/安全引擎）+ 孩子选择器 + 退出登录
 * 选中孩子通过 Outlet context 共享给各家长页面
 * 角色守卫：非 parent 一律跳 /chat
 */
import { useEffect, useMemo, useState } from "react";
import {
  Navigate,
  NavLink,
  Outlet,
  useNavigate,
} from "react-router-dom";
import { apiFetch, getStoredUser } from "../../utils/api";
import { useAuth } from "../../hooks/useAuth";
import "./ParentLayout.css";

const NAV_ITEMS = [
  { to: "/parent/dashboard", label: "仪表盘" },
  { to: "/parent/alerts", label: "风险告警" },
  { to: "/parent/settings", label: "守护设置" },
  { to: "/parent/safety", label: "安全引擎" },
];

export default function ParentLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [children, setChildren] = useState([]);
  const [selectedChildId, setSelectedChildId] = useState(null);

  const user = getStoredUser();
  const isParent = user?.role === "parent";

  useEffect(() => {
    if (!isParent) return;
    apiFetch("/api/parent/dashboard")
      .then((data) => {
        const list = data.children || [];
        setChildren(list);
        if (list.length > 0) setSelectedChildId((cur) => cur ?? list[0].id);
      })
      .catch(() => setChildren([]));
  }, [isParent]);

  const selectedChild = useMemo(
    () => children.find((c) => c.id === selectedChildId) || null,
    [children, selectedChildId]
  );

  if (!isParent) return <Navigate to="/chat" replace />;

  const handleLogout = () => {
    logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="track-parent parent-layout">
      <header className="parent-topbar">
        <div className="parent-brand">
          安心童伴 <span className="parent-brand-sub">· 家长守护</span>
        </div>
        <nav className="parent-nav" aria-label="家长端导航">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `parent-nav-link${isActive ? " active" : ""}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="parent-topbar-right">
          {children.length > 0 && (
            <label className="child-picker">
              <span className="child-picker-label">当前孩子</span>
              <select
                className="child-picker-select"
                value={selectedChildId ?? ""}
                onChange={(e) => setSelectedChildId(Number(e.target.value))}
              >
                {children.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.username}（{c.age_tier} 岁）
                  </option>
                ))}
              </select>
            </label>
          )}
          <button className="btn-ghost parent-logout" onClick={handleLogout}>
            退出登录
          </button>
        </div>
      </header>
      <main className="parent-main">
        <Outlet
          context={{ children, selectedChild, selectedChildId }}
        />
      </main>
    </div>
  );
}
