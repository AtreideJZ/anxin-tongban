/* main.jsx — 入口：挂载 App，引入设计 token 与全局样式
 * Nunito 走 @fontsource（拉丁/数字）；中文圆润黑体走系统字体栈（token 内），
 * 不引外部 CJK 网络字体
 */
import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource/nunito/400.css";
import "@fontsource/nunito/600.css";
import "@fontsource/nunito/700.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "./styles/tokens.css";
import "./styles/track-child.css";
import "./styles/track-parent.css";
import "./styles/global.css";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
