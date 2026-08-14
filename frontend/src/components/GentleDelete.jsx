/* ============================================================
 * GentleDelete — 温和两步删除确认（条目卡/胶囊卡共用）
 * 第一次点变成"确定要删掉吗？"，再点"删掉"才执行，"留下"取消
 * ============================================================ */

import { useState } from "react";
import "./GentleDelete.css";

export default function GentleDelete({ onConfirm, label = "删除" }) {
  const [asking, setAsking] = useState(false);
  if (asking) {
    return (
      <span className="gentle-delete">
        <span className="gentle-delete-text">确定要删掉吗？</span>
        <button type="button" className="gentle-delete-yes" onClick={onConfirm}>
          删掉
        </button>
        <button
          type="button"
          className="gentle-delete-no"
          onClick={() => setAsking(false)}
        >
          留下
        </button>
      </span>
    );
  }
  return (
    <button
      type="button"
      className="gentle-delete-btn"
      onClick={() => setAsking(true)}
    >
      {label}
    </button>
  );
}
