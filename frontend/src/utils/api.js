/* ============================================================
 * api.js — fetch 封装：统一 Bearer 头、错误信息中文友好化
 * ============================================================ */

const TOKEN_KEY = "anxin_token";
const USER_KEY = "anxin_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function storeAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** 把 FastAPI 的错误响应转成友好的中文提示 */
async function extractError(res) {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
      return "填写的内容好像不太对，请检查一下";
    }
  } catch {
    /* 忽略解析失败 */
  }
  return `网络出了点小问题（${res.status}），请再试一次`;
}

/** 普通 JSON 请求 */
export async function apiFetch(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const message = await extractError(res);
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  return res.json();
}
