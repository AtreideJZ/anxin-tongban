/* ============================================================
 * time.js — 时段工具（儿童端共用）
 * timeBandOf： morning|afternoon|evening|night，驱动问候语与昼夜氛围
 * ============================================================ */

export function timeBandOf(hour) {
  if (hour >= 5 && hour < 11) return "morning";
  if (hour >= 11 && hour < 18) return "afternoon";
  if (hour >= 18 && hour < 22) return "evening";
  return "night";
}

export const TIME_GREETING = {
  morning: "早上好",
  afternoon: "下午好",
  evening: "晚上好",
  night: "夜深了",
};

export function currentTimeBand() {
  return timeBandOf(new Date().getHours());
}
