/* ============================================================
 * useCapsules.js — 时间胶囊 hook
 *
 * - GET /api/capsules 时服务端会自动破壳到期的胶囊
 * - createCapsule：payload {title, content, unlock_at(ISO)}
 * - deleteCapsule：温和删除
 * ============================================================ */

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../utils/api";

export function useCapsules() {
  const [capsules, setCapsules] = useState([]);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await apiFetch("/api/capsules");
      setCapsules(data.capsules || []);
    } catch {
      /* 胶囊加载失败不影响星球其他区域 */
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const createCapsule = useCallback(async (payload) => {
    const data = await apiFetch("/api/capsules", {
      method: "POST",
      body: payload,
    });
    if (data.capsule) {
      setCapsules((prev) => [...prev, data.capsule]);
    }
    return data.capsule;
  }, []);

  const deleteCapsule = useCallback(async (id) => {
    await apiFetch(`/api/capsules/${id}`, { method: "DELETE" });
    setCapsules((prev) => prev.filter((c) => c.id !== id));
  }, []);

  return { capsules, loaded, createCapsule, deleteCapsule, reload: load };
}
