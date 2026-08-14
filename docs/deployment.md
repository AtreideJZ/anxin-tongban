# 安心童伴 v2.1 — 生产部署指南

> 单进程部署：FastAPI 直接托管 React 构建产物，一台国内轻量云服务器即可跑通。
> 无 Docker、无云数据库、零 CORS（同源托管）。

## 架构

```
浏览器 → 国内轻量云服务器 :8765
         └─ FastAPI (uvicorn) → /api/* 后端路由（SQLite + core 安全引擎）
                              → / 前端 vite build 产物（frontend/dist）
```

## 部署步骤

### 1. 准备服务器

- 一台国内轻量云服务器（阿里云 / 腾讯云均可），系统 Ubuntu 22.04+ / CentOS 7+
- 安全组放行 **8765 端口**（或你自定义的端口）
- 建议 2C4G 起（FastAPI + SQLite + 静态托管，无本地模型推理负载）

### 2. 拉取代码 + 装依赖

```bash
git clone <仓库地址> && cd kid-accompany
pip install -r requirements.txt            # 根 requirements（Streamlit 兜底）
pip install -r backend/requirements.txt    # 后端依赖
cd frontend && npm install && npm run build && cd ..   # 构建前端产物
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env：填入 DEEPSEEK_API_KEY，生产必改 JWT_SECRET
```

### 4. 一键启动

```bash
python scripts/start_server.py --port 8765
```

启动脚本会自动：建库 → 生成演示账号（幂等）→ 启动 uvicorn。

- 演示账号：`demo_kid`（PIN 1234）· `demo_parent`（PIN 0000）
- API 文档：`http://<服务器IP>:8765/docs`
- 健康检查：`http://<服务器IP>:8765/api/health`

### 5. 长驻后台（nohup / systemd 二选一）

**nohup：**

```bash
nohup python scripts/start_server.py --port 8765 > server.log 2>&1 &
```

**systemd**（推荐，开机自启 + 崩溃重启）：

```ini
# /etc/systemd/system/anxin.service
[Unit]
Description=Anxin Tongban AI
After=network.target

[Service]
WorkingDirectory=/root/kid-accompany
ExecStart=/usr/bin/python scripts/start_server.py --port 8765
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload && systemctl enable --now anxin
```

### 6. 域名 + HTTPS（可选但建议）

用 Nginx / Caddy 反代 `8765` 并配置 HTTPS，避免浏览器语音（Web Speech API）
在非安全上下文下不可用：

```
# Caddy 一行搞定（Caddyfile）
anxin.example.com {
    reverse_proxy localhost:8765
}
```

## 本地快速验证（评委 clone 后 3 步跑通）

```bash
pip install -r backend/requirements.txt
python scripts/start_server.py --port 8765
# 打开 http://localhost:8765
```

## 部署检查清单

- [ ] `python -m pytest backend/tests -q` 全绿
- [ ] `curl http://<IP>:8765/api/health` → `{"status":"ok"}`
- [ ] 浏览器打开首页 → 注册/登录正常
- [ ] `demo_kid` 登录 → 聊天/小星球/时间胶囊有演示数据
- [ ] `demo_parent` 登录 → 仪表盘 7 日趋势 + 告警列表有数据
- [ ] 家长端「安全引擎」→ 案例4（"我不想活了"）→ Step 1 命中自伤 → 危机模板拦截
