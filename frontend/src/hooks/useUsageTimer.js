/* ============================================================
 * useUsageTimer.js — 使用时长计时 + 2 小时温暖提醒（合规 4.8）
 * 进入页面开始计时，结合 history 返回的累计 usage_minutes；
 * 累计达 120 分钟弹出可关闭提醒（不强制锁屏）。
 * ============================================================ */

import { useEffect, useRef, useState } from "react";

const REMIND_AT_MINUTES = 120;
const TICK_MS = 30 * 1000; // 每 30 秒刷新一次显示

export function useUsageTimer(initialMinutes = 0) {
  const [sessionMinutes, setSessionMinutes] = useState(0);
  const [showReminder, setShowReminder] = useState(false);
  const startRef = useRef(Date.now());
  const remindedRef = useRef(false);
  const initialRef = useRef(initialMinutes);

  // history 返回后再同步一次累计基数
  useEffect(() => {
    initialRef.current = initialMinutes;
  }, [initialMinutes]);

  useEffect(() => {
    const timer = setInterval(() => {
      const elapsed = (Date.now() - startRef.current) / 60000;
      setSessionMinutes(elapsed);
      const total = initialRef.current + elapsed;
      if (!remindedRef.current && total >= REMIND_AT_MINUTES) {
        remindedRef.current = true;
        setShowReminder(true);
      }
    }, TICK_MS);
    return () => clearInterval(timer);
  }, []);

  const dismissReminder = () => setShowReminder(false);

  return {
    sessionMinutes: Math.floor(sessionMinutes),
    totalMinutes: Math.floor(initialRef.current + sessionMinutes),
    showReminder,
    dismissReminder,
  };
}
