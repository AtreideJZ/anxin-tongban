/* App.jsx — 路由表 + 路由守卫
 * 无 token 一律跳回 /；按角色守护 /chat 与 /parent（家长端角色守卫在 ParentLayout 内）
 */
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { getToken, getStoredUser } from "./utils/api";
import Landing from "./pages/Landing";
import ChildHome from "./pages/ChildHome";
import ChildrenChat from "./pages/ChildrenChat";
import MyPlanet from "./pages/MyPlanet";
import CoCreation from "./pages/CoCreation";
import ParentLayout from "./pages/parent/ParentLayout";
import ParentDashboard from "./pages/parent/ParentDashboard";
import ParentAlerts from "./pages/parent/ParentAlerts";
import ParentSettings from "./pages/parent/ParentSettings";
import SafetyEngine from "./pages/parent/SafetyEngine";

/** 登录守卫：无 token → / */
function RequireAuth({ children }) {
  if (!getToken()) return <Navigate to="/" replace />;
  return children;
}

/** 已登录用户访问 / 时按角色分流 */
function LandingGate() {
  const user = getToken() ? getStoredUser() : null;
  if (user) {
    return <Navigate to={user.role === "parent" ? "/parent" : "/home"} replace />;
  }
  return <Landing />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingGate />} />
        <Route
          path="/home"
          element={
            <RequireAuth>
              <ChildHome />
            </RequireAuth>
          }
        />
        <Route
          path="/chat"
          element={
            <RequireAuth>
              <ChildrenChat />
            </RequireAuth>
          }
        />
        <Route
          path="/planet"
          element={
            <RequireAuth>
              <MyPlanet />
            </RequireAuth>
          }
        />
        <Route
          path="/cocreation"
          element={
            <RequireAuth>
              <CoCreation />
            </RequireAuth>
          }
        />
        <Route
          path="/parent"
          element={
            <RequireAuth>
              <ParentLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/parent/dashboard" replace />} />
          <Route path="dashboard" element={<ParentDashboard />} />
          <Route path="alerts" element={<ParentAlerts />} />
          <Route path="settings" element={<ParentSettings />} />
          <Route path="safety" element={<SafetyEngine />} />
        </Route>
        {/* 未知路径回入口 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
