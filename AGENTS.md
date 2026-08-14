# AGENTS.md · 安心童伴

面向 5-14 岁儿童的 AI 陪伴助手。SpaceMind AI Agent 创新应用大赛参赛作品。
当前主线版本为 **v2.1-final 全栈版**：React 18 前端 + FastAPI 后端 + SQLite 数据库，安全引擎 (`core/`) 前后端复用。Streamlit 旧版（`app.py` / `pages/` / `parent_app.py`）保留为兜底。

---

## 1. 项目概述

### 1.1 产品定位

- 目标用户：5-14 岁儿童少年及其家长。
- 核心卖点：不是“把大模型换成儿童语气”，而是在每一轮对话中跑完整的安全 Pipeline——关键词检测 → LLM 风险分类 → 策略决策 → Prompt 构建 → LLM 生成 → 批判 Agent 审计 → 输出拦截替换。
- 两条客户端：
  - **儿童端** (`/home` 主页 → `/chat`)：主页二选一入口；统一对话框，AI 自动识别故事 / 百科 / 情绪 / 聊天意图；我的小星球 (`/planet`) 记录成长。
  - **家长端** (`/parent/*`)：仪表盘、告警、话题偏好设置、安全引擎可视化。

### 1.2 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + Vite + React Router + Framer Motion + Recharts + Web Speech API |
| 后端 | FastAPI + Uvicorn + SQLAlchemy 2.x + SQLite（WAL 模式） |
| 认证 | JWT（pyjwt HS256）+ 4 位数字 PIN（pbkdf2_sha256 哈希） |
| LLM | DeepSeek 双模型：`deepseek-v4-pro` 主回复（流式）、`deepseek-chat` 轻量任务（分类/审计/摘要） |
| 安全引擎 | `core/` 下纯 Python + LLM 混合的 8 步 Pipeline |
| 部署 | 单进程：FastAPI 直接托管 `frontend/dist` 静态产物，默认端口 `8765` |
| 测试 | pytest，36 项自动化测试，无 API Key 也能全绿 |

### 1.3 关键架构决策

- **v2.1-final Pipeline 为 8 步**（0→1→2→3→4→5→6→6b）。`core/qwen_guard.py` 与 `models/` 下的 Qwen3Guard GGUF 已弃用保留，**不再接入 Pipeline**。
- **SSE 是“先审计、后伪流式”**：`backend/routes/chat.py` 在 `process_message()` 返回时 Pipeline 已完整跑完（含 Step 6 审计与 Step 6b 拦截），再按 `step` → `token` → `done` 回放给前端。任何回复文本必须在完整审计后才离开后端。
- **情景记忆 per-user 隔离**：正式对话通过 `episodic_retriever / episodic_store / episodic_count` 回调写入 SQLite（`backend/services/episodic_service.py`）；`safety-demo` 演示路径传空回调（不读不写）；全局 JSON 仅 Streamlit 旧版使用。

---

## 2. 项目结构与模块划分

```
.
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 入口、路由注册、CORS、托管前端 dist + SPA 回退
│   ├── config.py               # pydantic-settings，读项目根 .env / 环境变量
│   ├── database.py             # SQLAlchemy 引擎、SessionLocal、建表
│   ├── models/                 # ORM：user / session / planet / capsule / memory / parent / cocreation
│   ├── routes/                 # auth / chat / planet / capsule / challenges / parent
│   ├── services/               # chat_service / planet_service / parent_service / user_service / episodic_service
│   ├── seed.py                 # 演示账号与满血演示数据（幂等）
│   └── tests/                  # 36 项 pytest
├── core/                       # 安全引擎核心（两端复用，改动需格外谨慎）
│   ├── pipeline.py             # 8 步 Pipeline 主编排
│   ├── guardrails.py           # Step 1 关键词检测 + 家长话题偏好命中
│   ├── risk_classifier.py      # Step 2 风险分类 + mode 意图自动识别
│   ├── policy_engine.py        # Step 3 策略决策
│   ├── prompt_builder.py       # Step 4 Prompt 构建（反谄媚 + 年龄分层 + 文化元素）
│   ├── llm_client.py           # Step 5/6 DeepSeek 客户端
│   ├── critic_agent.py         # Step 6 批判审计
│   ├── memory_manager.py       # Step 0 策展记忆（小星球检索 / 生态 / 天气 / 勇敢芽校验）
│   ├── episodic_memory.py      # Step 0 Tier 2 情节记忆摘要逻辑
│   ├── proactive_engine.py     # 主动预警（情绪 / 深夜 / 沉默 / 高风险 / 使用时长）
│   ├── recommendation_engine.py# 内容推荐
│   ├── daily_challenges.py     # 每日小挑战
│   ├── voice.py                # 语音模块（浏览器 Web Speech API 为主）
│   └── qwen_guard.py           # 已弃用，仅保留代码参考
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── App.jsx / main.jsx  # 路由与挂载
│   │   ├── pages/              # Landing / ChildHome(儿童主页/home，登录后首站) / ChildrenChat / MyPlanet / CoCreation / parent/*
│   │   ├── components/         # ChatBubble / PlanetCard / PlanetCompass / SafetyShield / VoiceButton 等
│   │   ├── hooks/              # useChat (SSE) / usePlanet / useVoice / useAuth / useUsageTimer
│   │   ├── styles/             # tokens.css / global.css / track-child.css / track-parent.css
│   │   └── utils/api.js        # fetch 封装、localStorage token 管理
│   ├── package.json
│   └── vite.config.js          # 开发代理 /api → localhost:8765
├── scripts/
│   └── start_server.py         # 生产一键启动（建库 + seed + uvicorn）
├── pages/                      # Streamlit 旧版儿童端页面
├── app.py                      # Streamlit 旧版入口
├── parent_app.py               # Streamlit 旧版家长端入口
├── data/                       # demo_cases.py、运行时库文件与全局 JSON（不入库）
├── docs/                       # 方案书、设计系统、部署指南、重构进展报告
└── AGENTS.md                   # 本文件
```

---

## 3. 常用命令

### 3.1 全栈启动（主线）

```bash
# 1. 安装后端依赖
pip install -r backend/requirements.txt

# 2. 安装并构建前端
cd frontend && npm install && npm run build && cd ..

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env：填入 DEEPSEEK_API_KEY；生产必改 JWT_SECRET

# 4. 一键启动（默认 0.0.0.0:8765，自动建库 + seed）
python scripts/start_server.py --port 8765
```

### 3.2 开发模式

```bash
# 终端 A：后端热重载（端口固定 8765）
uvicorn backend.main:app --reload --port 8765

# 终端 B：前端开发服务器（已代理 /api 到 8765）
cd frontend && npm run dev
```

### 3.3 测试

```bash
# 36 项测试，无 API Key 也必须全绿
python -m pytest backend/tests -q
```

**修改 `core/` 任何文件后必须跑上述测试回归。**

### 3.4 Streamlit 旧版（兜底）

```bash
pip install -r requirements.txt        # Streamlit + openai
streamlit run app.py                   # 儿童端入口，端口 8501
streamlit run parent_app.py            # 家长端入口
```

### 3.5 演示账号

- 儿童端：`demo_kid`，PIN `1234`，年龄档 `8-10`
- 家长端：`demo_parent`，PIN `0000`

seed 脚本幂等：`demo_kid` 已存在则跳过。

---

## 4. 配置与环境变量

配置统一走环境变量 / 项目根 `.env` 文件（`backend/config.py` 加载），**不再读取 `.streamlit/secrets.toml`**。

| 变量 | 说明 | 默认值 / 是否必填 |
|------|------|------------------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 不填则进入脚本回退模式 |
| `ANXIN_MAIN_MODEL` | 主回复模型 | `deepseek-v4-pro` |
| `ANXIN_SMALL_MODEL` | 轻量任务模型 | `deepseek-chat` |
| `JWT_SECRET` / `ANXIN_JWT_SECRET` | JWT 签名密钥 | **生产必须修改**，开发默认值公开 |
| `ANXIN_DATABASE_URL` | SQLite 路径 | `sqlite:///./data/anxin.db` |
| `ANXIN_EPISODIC_STORE` | 情景记忆全局 JSON 路径 | `data/episodic_memory.json`（仅 Streamlit 旧版用） |
| `ANXIN_CORS_ORIGINS` | CORS 允许来源（逗号分隔） | 默认仅 Vite 开发源（localhost:5173）；生产同源托管无需配置 |

生产启动时如果 `JWT_SECRET` 仍是开发默认值，`scripts/start_server.py` 会打印醒目警告。

---

## 5. 代码风格与开发约定

### 5.1 通用风格

- 代码注释、docstring、提交信息使用**中文**（项目既有惯例）。
- 每个 Python 文件顶部写模块级 docstring，说明职责、调用方式、关键不变量。
- 导入顺序：标准库 → 第三方 → 项目内部；尽量使用 `from __future__ import annotations`。
- 类型提示：函数参数与返回值加类型提示；复杂结构用 `dataclass` 或 Pydantic `BaseModel`。
- 配置与常量优先放在模块顶部，避免在函数内部硬编码业务规则。

### 5.2 后端约定

- FastAPI 路由按资源分文件（`backend/routes/*.py`），统一前缀 `/api/*`。
- 数据库访问：路由通过 `Depends(get_db)` 拿会话；服务层可接收 `Session`。
- ORM 使用 SQLAlchemy 2.0 `Mapped[int] = mapped_column(...)` 风格。
- 认证依赖：`get_current_user` 解析 JWT；`require_parent` 校验 `role == "parent"`。
- 服务层职责：
  - `chat_service.process_message()` 是核心安全不变量守卫者——Pipeline 必须完整跑完再返回。
  - `episodic_service` 的回调在线程池执行，内部必须新建独立 `SessionLocal()` 会话，禁止复用请求会话。
  - `cocreation_service`（v2.2 共创故事）：孩子接的每一段必须跑完整 `pipeline.run()` 审计，
    触发危机模板 / 批判拦截 / risk_level>=2 时不存储原文；共创全程不碰 `usage_minutes`。

### 5.3 安全引擎 (`core/`) 约定

- `core/` 是两端复用的敏感区域，改动前必须理解 Pipeline 数据流。
- Step 1 关键词检测为确定性规则，不依赖 LLM。
- Step 2 LLM 分类在不可用或解析失败时回退到规则分类器，保证 Demo 无 Key 可运行。
- Step 3 `policy_engine` 是决策树，`risk_level == 3` 直接使用危机模板，**跳过 LLM 自由生成**。
- Step 6 `critic_agent` 在 LLM 不可用时回退规则版审计。
- Step 6b 拦截替换是**确定性规则**：一旦 `critic_alert=True`，整段替换为 `SAFE_REPLACEMENT_TEMPLATE`，不再走 LLM。
- 危机模板 `CRISIS_TEMPLATE` 与替换模板 `SAFE_REPLACEMENT_TEMPLATE` 是 `core/pipeline.py` 中的常量，任何修改需同步测试。

### 5.4 前端约定

- 样式使用 CSS 变量，设计 token 见 `frontend/src/styles/tokens.css`，设计系统见 `docs/DESIGN-anxin.md`。
- 儿童端与家长端分别引入 `track-child.css` / `track-parent.css`。
- API 调用统一走 `utils/api.js`，错误提示中文友好化。
- SSE 由 `hooks/useChat.js` 解析 `step` / `token` / `done` 事件；`step` 事件驱动家长端安全引擎页决策链点亮。
- 儿童端 UI 纪律：**不给孩子显示风险等级、决策链、技术步骤名**；这些信息仅展示给家长端。

### 5.5 重构进展报告制度（必须遵守）

每完成一部分任务或一个阶段，必须在 `docs/重构进展报告/` 写一份 Markdown 报告：

1. 完成了什么（交付物清单 + 验证结果）
2. 偏差（与计划不一致之处及原因）
3. 需要注意的事项（坑、遗留问题、给后续阶段的提醒）

命名规范：`DayNN-YYYY-MM-DD-主题.md`，并在 `docs/重构进展报告/README.md` 的索引表中登记。本制度对人协作和 AI 编程助手同样生效。

---

## 6. 测试策略

### 6.1 测试结构

- `backend/tests/conftest.py`：
  - 创建临时 SQLite（不污染 `data/anxin.db`）。
  - 强制清除 `DEEPSEEK_API_KEY`，确保测试走 fallback 模式。
  - 将 `core.episodic_memory` 初始化为 `:memory:`。
  - 提供 `client`、`register_and_login`、`send_chat`、`parse_sse` 等 fixture / 辅助函数。
- `backend/tests/test_pipeline.py`（8 项）：覆盖危机模板、SSE 顺序不变量、拦截替换、完整步骤、持久化、mode 自动识别等。
- `backend/tests/test_api_smoke.py`（26 项）：覆盖注册/登录、监护人同意、planet CRUD、胶囊、每日挑战、家长端权限与偏好生效、守护/信任/过渡模式摘要差异、per-user 隔离、安全演示台、分龄四档、亲子话题卡、共创故事（完整流程/安全闭环/隐私/不计时/轮次上限）等。

### 6.2 本地测试与回归

```bash
python -m pytest backend/tests -q
```

- 所有测试不依赖外部 LLM API。
- 修改 `core/` 后必须全绿再提交。
- 新增安全相关行为必须补充测试，尤其是 SSE 顺序 / 拦截 / 危机模板路径。

---

## 7. 部署流程

### 7.1 生产启动脚本

```bash
python scripts/start_server.py --port 8765
```

脚本自动完成：
1. `init_db()` 建表（幂等）。
2. `run_seed()` 生成演示账号与演示数据（幂等，可用 `--no-seed` 跳过）。
3. 检查 `JWT_SECRET` 是否为开发默认值并告警。
4. 启动 `uvicorn` 单 worker 托管 `backend.main:app`。

### 7.2 长驻后台（systemd 示例）

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

### 7.3 域名与 HTTPS

建议用 Nginx / Caddy 反代 `8765` 并配置 HTTPS；否则浏览器 Web Speech API 可能在非安全上下文下不可用。

Caddy 示例：

```
anxin.example.com {
    reverse_proxy localhost:8765
}
```

### 7.4 部署检查清单

- [ ] `python -m pytest backend/tests -q` 全绿
- [ ] `curl http://<IP>:8765/api/health` → `{"status":"ok"}`
- [ ] 浏览器首页注册/登录正常
- [ ] `demo_kid` 登录后聊天、小星球、胶囊有演示数据
- [ ] `demo_parent` 登录后仪表盘 7 日趋势 + 告警列表有数据
- [ ] 家长端「安全引擎」→ 案例 4（"我不想活了"）→ Step 1 命中自伤 → 危机模板拦截

---

## 8. 安全考虑

### 8.1 认证与密钥

- JWT 签名密钥由 `JWT_SECRET` 环境变量控制，**开发默认值是公开的**，生产必须覆盖。
- PIN 使用 `hashlib.pbkdf2_hmac("sha256", ...)` 加盐哈希存储，不引入额外依赖。
- Streamlit 旧版 `parent_app.py` 的家长 PIN 仍从 `PARENT_PIN` 环境变量或 `.streamlit/secrets.toml` 读取，全栈版家长端已改为 JWT 登录，不再使用该 PIN 机制。

### 8.2 内容安全不变量

- **SSE 安全不变量**：任何回复文本必须在 Pipeline 完整审计（Step 6 + 6b）后才离开后端；测试 `test_sse_tokens_after_all_steps` 与 `test_critic_alert_intercepts_output` 守护该不变量。**禁止改回真流式**。
- **危机模板路径**：`risk_level == 3` 时直接返回预置危机模板，不调用 LLM 自由生成。
- **输出拦截**：Step 6 批判审计告警后，整段替换为安全模板，不走 LLM 再生成，避免二次风险。

### 8.3 数据隔离与隐私

- 情景记忆、星球条目、对话历史、胶囊、家长告警/偏好全部按 `user_id` 隔离。
- `data/episodic_memory.json` 仅被 Streamlit 旧版路径写入，全栈正式对话与 safety-demo 演示都不走该全局文件。
- 情节摘要不保存原始对话原文，仅保留结构化摘要，符合数据最小化原则。
- 信任模式（14 岁及以上）：家长端星球概览不可见，告警仅在高风险时触发；过渡模式（11-13）星球默认私密、周度摘要。
- 共创故事成品默认孩子私密，孩子主动分享后家长端可见（`shared_with_parent`）。

### 8.4 儿童端信息纪律

- 不给孩子展示风险等级、决策链、技术步骤名、家长告警详情。
- 家长端展示脱敏摘要，不展示对话原文。

### 8.5 合规对应

依据《人工智能拟人化互动服务管理暂行办法》：

- 注册强制勾选监护人同意（前后端双校验）。
- 年龄分层（v2.2 四档三模式）：5-7 / 8-10 守护模式（每轮摘要）/ 11-13 过渡模式（周度摘要）/ 14+ 信任模式（仅高风险告警）。
- AI 身份标识：聊天页常驻 `AiIdentityBadge` + Prompt 声明。
- 2 小时使用时长提醒：`chat_sessions.usage_minutes` 累计，前端 `useUsageTimer` 弹窗提示。
- 禁止诱导不安全行为、禁止虚拟亲密关系：由反谄媚 Prompt + 批判审计兜底。

---

## 9. 给 AI 协作者的快速检查单

修改代码前，先确认自己落在哪个区域：

1. **改 `core/`**：必须通读 `core/pipeline.py` 数据流，跑 `python -m pytest backend/tests -q`。
2. **改数据库模型**：在 `backend/models/` 新增 / 修改后，FastAPI 启动时 `init_db()` 会自动建表；测试库由 `conftest.py` 单独创建。
3. **改环境变量读取**：统一走 `backend/config.py` 的 `Settings`，不要直接读 `os.environ` 或 `.streamlit/secrets.toml`。
4. **改 SSE / 聊天流**：必须保证“先审计、后流出”，否则破坏安全架构。
5. **改前端儿童端 UI**：不要暴露风险等级 / 决策链 / 技术步骤名。
6. **完成阶段任务**：按“重构进展报告制度”在 `docs/重构进展报告/` 写报告并登记索引。

---

## 10. 常用文件速查

| 文件 | 用途 |
|------|------|
| `backend/main.py` | FastAPI 入口、路由挂载、静态托管、SPA 回退 |
| `backend/routes/chat.py` | `/api/chat/send` SSE 端点，安全不变量守门 |
| `backend/services/chat_service.py` | Pipeline 调用 + 持久化 + 告警 + 推荐 |
| `backend/config.py` | 环境变量配置 |
| `backend/database.py` | SQLAlchemy 引擎与建表 |
| `core/pipeline.py` | 8 步 Pipeline 主编排 |
| `core/guardrails.py` | Step 1 关键词检测 + 家长偏好命中 |
| `core/risk_classifier.py` | Step 2 风险分类 + mode 自动识别 |
| `core/policy_engine.py` | Step 3 策略决策 |
| `core/prompt_builder.py` | Step 4 Prompt 构建 |
| `core/llm_client.py` | DeepSeek 客户端 |
| `core/critic_agent.py` | Step 6 批判审计 |
| `core/memory_manager.py` | 小星球检索 / 天气 / 生态 / 勇敢芽校验 |
| `core/episodic_memory.py` | 情节记忆摘要逻辑 |
| `frontend/src/App.jsx` | React 路由表 |
| `frontend/src/hooks/useChat.js` | SSE 解析与聊天状态 |
| `scripts/start_server.py` | 生产一键启动 |
| `backend/seed.py` | 演示账号与演示数据 |
| `backend/tests/conftest.py` | 测试 fixture 与辅助函数 |
