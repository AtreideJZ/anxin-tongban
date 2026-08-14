import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // 开发期把 /api 代理到 FastAPI 后端（生产由后端直接托管 dist）
      // 端口固定 8765：本机 8000 被其他项目占用（见重构进展报告 Day02）
      "/api": "http://localhost:8765",
    },
  },
  build: {
    outDir: "dist",
  },
});
