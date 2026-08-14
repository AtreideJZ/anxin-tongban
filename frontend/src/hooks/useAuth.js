/* ============================================================
 * useAuth.js — 认证 hook：登录/注册/退出，localStorage 持久化
 * token 存 anxin_token，user 存 anxin_user
 * ============================================================ */

import { useCallback, useState } from "react";
import {
  apiFetch,
  storeAuth,
  clearAuth,
  getToken,
  getStoredUser,
} from "../utils/api";

export function useAuth() {
  const [user, setUser] = useState(getStoredUser);
  const [token, setToken] = useState(getToken);

  const login = useCallback(async (username, pin) => {
    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      body: { username, pin },
    });
    storeAuth(data.token, data.user);
    setToken(data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const register = useCallback(async (form) => {
    const data = await apiFetch("/api/auth/register", {
      method: "POST",
      body: form,
    });
    storeAuth(data.token, data.user);
    setToken(data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setToken(null);
    setUser(null);
  }, []);

  return { user, token, login, register, logout };
}
