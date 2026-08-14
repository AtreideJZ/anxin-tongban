/* ============================================================
 * useDailyChallenge.js — 今日小挑战（儿童端共用）
 * 拉取 /api/challenges/today；失败或为空返回 null（调用方静默降级，不占位）
 * ============================================================ */

import { useEffect, useState } from "react";
import { apiFetch } from "../utils/api";

export function useDailyChallenge() {
  const [challenge, setChallenge] = useState(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch("/api/challenges/today")
      .then((d) => {
        if (!cancelled && d?.challenge?.text) setChallenge(d.challenge);
      })
      .catch(() => {
        /* 挑战拉不到就静默降级 */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return challenge;
}
