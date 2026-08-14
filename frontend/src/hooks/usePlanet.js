/* ============================================================
 * usePlanet.js — 小星球数据 hook：条目 / 天气 / 生态
 *
 * - 挂载时并行拉取 entries + weather + ecosystem
 * - createEntry：成功后本地追加（entries 按 created_at 倒序，新的插最前），
 *   并静默刷新天气/生态，保证生命树与横幅即时更新
 * - deleteEntry：成功后本地移除，同样刷新天气/生态
 * - createEntry 原样返回后端 {entry, validation}（sprout 校验信息给表单温和提示）
 * ============================================================ */

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../utils/api";

export function usePlanet() {
  const [entries, setEntries] = useState([]);
  const [weather, setWeather] = useState(null);
  const [ecosystem, setEcosystem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /** 静默刷新天气与生态（条目增减后心情天气可能变化） */
  const refreshSky = useCallback(async () => {
    try {
      const [w, eco] = await Promise.all([
        apiFetch("/api/planet/weather"),
        apiFetch("/api/planet/ecosystem"),
      ]);
      setWeather(w);
      setEcosystem(eco);
    } catch {
      /* 天气刷新失败不打断页面，下次操作再试 */
    }
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [e, w, eco] = await Promise.all([
        apiFetch("/api/planet/entries"),
        apiFetch("/api/planet/weather"),
        apiFetch("/api/planet/ecosystem"),
      ]);
      setEntries(e.entries || []);
      setWeather(w);
      setEcosystem(eco);
    } catch (err) {
      setError(err.message || "加载失败，请再试一次");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const createEntry = useCallback(
    async (payload) => {
      const data = await apiFetch("/api/planet/entries", {
        method: "POST",
        body: payload,
      });
      if (data.entry) {
        setEntries((prev) => [data.entry, ...prev]);
      }
      refreshSky(); // 不 await：树先长，天气随后跟上
      return data; // {entry, validation}
    },
    [refreshSky]
  );

  const deleteEntry = useCallback(
    async (id) => {
      await apiFetch(`/api/planet/entries/${id}`, { method: "DELETE" });
      setEntries((prev) => prev.filter((e) => e.id !== id));
      refreshSky();
    },
    [refreshSky]
  );

  return {
    entries,
    weather,
    ecosystem,
    loading,
    error,
    createEntry,
    deleteEntry,
    reload: loadAll,
  };
}
