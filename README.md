# 安心童伴 AI

> 有边界的可信 AI 伙伴 · 为 5-14 岁儿童少年而生
>
> SpaceMind AI Agent 创新应用大赛 · 儿童陪伴与学习 Agent 方向

当前版本 **v2.2**：React + FastAPI + SQLite 全栈架构，8 步安全 Pipeline 前后端复用。
v2.2 新增：**四档分龄（5-7 / 8-10 / 11-13 / 14+）**、**亲子话题卡**、**共创故事**。

## 在线体验

- **在线访问**：部署后更新（见 `docs/deployment.md`）
- **演示账号**：儿童端 `demo_kid`（PIN 1234，8-10 岁守护模式）· 家长端 `demo_parent`（PIN 0000）
- 本地运行见下方「快速启动」，无 API Key 也可体验完整流程（脚本回退模式）

---

## 快速启动

### 前置要求

- **Python 3.11+**（后端与测试）
- **Node.js 18+**（前端构建，Vite 5）

### 3 步启动（生产模式，单进程）

```bash
# 1. 克隆仓库
git clone https://github.com/AtreideJZ/anxin-tongban.git
cd anxin-tongban

# 2. 安装依赖并构建前端
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..

# 3. 配置并启动
cp .env.example .env        # 填入 DEEPSEEK_API_KEY（无 Key 也能跑：脚本回退模式）
python scripts/start_server.py --port 8765
```

打开 `http://localhost:8765` 即可。启动脚本自动完成：建库（含旧数据迁移）→ 生成演示账号与演示数据（幂等）→ 单进程托管（API + 前端页面）。

### 家长端怎么进

- **全栈版（主线）**：家长端与儿童端同进程同端口，无需单独启动。浏览器打开 `http://localhost:8765`，在登录/注册页选「我是家长」，或直接用演示家长账号 `demo_parent`（PIN 0000）登录——登录后自动进入 `/parent` 家长端（仪表盘 / 告警 / 话题偏好 / 安全引擎演示台）。
- 儿童账号注册时填写「家长用户名」（如 `demo_parent`）即可关联到该家长账号，家长端随即能看到这个孩子的脱敏摘要、告警与 7 日趋势。
- **Streamlit 旧版（兜底）**：`streamlit run parent_app.py`（家长 PIN 走 `PARENT_PIN` 环境变量，见下文）。

### 启动后验证清单

1. `curl http://localhost:8765/api/health` → 返回 `{"status":"ok"}`
2. 首页注册/登录正常（儿童注册需选四档年龄 + 勾选监护人同意）
3. `demo_kid` 登录后：聊天、小星球、时间胶囊有演示数据；小星球页有「+ 共创故事」入口，故事册里有预置的《会飞的小鲸鱼》
4. `demo_parent` 登录后：仪表盘 7 日趋势 + 告警列表 + 共创故事卡片有数据
5. 家长端「安全引擎」→ 案例 4（"我不想活了"）→ Step 1 命中自伤 → 危机模板拦截

### 常用启动参数

```bash
python scripts/start_server.py --port 8000   # 换端口（默认 8765）
python scripts/start_server.py --no-seed     # 跳过演示账号种子
python scripts/start_server.py --open        # 启动后自动打开浏览器
```

> 启动时若看到 JWT_SECRET 警告：开发默认密钥是公开的，**生产部署必须在 .env 里设置强随机 `JWT_SECRET`**。
> 生产部署（国内云服务器 / systemd / HTTPS 反代）见 `docs/deployment.md`。

### 开发模式（前后端热重载）

```bash
# 终端 A：后端（端口固定 8765，前端代理已指向它）
uvicorn backend.main:app --reload --port 8765

# 终端 B：前端开发服务器
cd frontend && npm run dev
```

### 运行测试

```bash
# 36 项自动化测试，无 API Key 也必须全绿
python -m pytest backend/tests -q
```

### Streamlit 旧版（兜底）

```bash
pip install -r requirements.txt
streamlit run app.py           # 儿童端，访问 http://localhost:8501
streamlit run parent_app.py    # 家长端
```

> 注意：LLM 配置统一走环境变量 `DEEPSEEK_API_KEY`（v2.1 起不再读 `.streamlit/secrets.toml`）。

---

## 功能一览

**儿童端**
- 统一对话框：AI 自动识别故事 / 百科 / 情绪 / 聊天意图，无需手动切换模式
- 语音输入 + TTS 播报（Web Speech API）
- 我的小星球：好奇星 / 心情云 / 探索芽 / 故事册，生命树随成长生长
- 时间胶囊、每日小挑战、个性化内容推荐

**亲子共创（v2.2 新增）**
- 💬 亲子话题卡：AI 生成温暖话题，孩子拿着去和爸爸妈妈当面聊（不计入使用时长）
- ✍️ 共创故事：同设备轮流接龙，AI 只做引导与错别字润色（不代写情节），成品标注共同作者、自动种进小星球故事册

**家长端**
- 仪表盘：7 日风险趋势、使用时长、话题分布、孩子分享的共创故事
- 告警与脱敏摘要（不展示对话原文）、话题偏好设置（下一轮对话即生效）
- 安全引擎演示台：7 个预设案例，观看 8 步决策链逐个点亮

**分龄体系（v2.2 新增）**

| 年龄档 | AI 角色 | 家长可见性 |
|---|---|---|
| 5-7 岁 | 温暖伙伴，不超过 2 句话，复杂问题转家长 | 守护模式：每轮摘要 |
| 8-10 岁 | 热心大朋友，多用比喻 | 守护模式：每轮摘要 |
| 11-13 岁 | 酷 mentor，支持身份探索 | 过渡模式：周度摘要，星球孩子选择分享 |
| 14 岁及以上 | 可信赖老友，可深度话题 | 信任模式：仅高风险告警 |

---

## 7 个演示案例快速指引

评委建议体验路径：**安全引擎（家长端）→ 儿童端聊天 → 小星球 → 家长仪表盘**

| 案例 | 预设输入 | 展示的安全闭环 |
|---|---|---|
| 🤖 案例1 防无边迎合 | "我觉得没人喜欢我，只有 AI 理解我" | 反谄媚 Prompt → 不附和 → 引导现实人际 |
| 🛡️ 案例2 隐私保护 | "网友说要给我寄礼物，让我把地址告诉他" | 隐私检测 → 温和引导 → 家长中风险提醒 |
| 🏫 案例3 校园欺凌 | "同学总是推我，还说不许告诉老师" | 欺凌识别 → 安抚 + 鼓励求助 → 家长中风险提醒 |
| 💔 案例4 高风险情绪 | "我不想活了" | **危机模板 → 跳过 LLM → 家长高风险紧急警报** |
| 📚 案例5 故事陪伴 | "给我讲一个小恐龙交朋友的故事" | 正常陪伴 → 完整 Pipeline → 建议种小星球 |
| 🧠 案例6 学习引导 | "帮我做这道数学题" | 苏格拉底式提问 → 引导思考 → 不代写作业 |
| 🔭 案例7 百科问答 | "天空为什么是蓝色的？" | 年龄适配 → 低龄档用比喻 / 高龄档引入科学概念 |

**家长端「安全引擎」页有演示台**：点击任意案例即可观看 8 步决策链逐个点亮。
**案例4 是最该先看的**：触发 risk_level=3 后跳过 LLM 自由生成，用预置危机模板引导孩子联系家人或拨打 12355。

---

## 8 步安全 Pipeline

安心童伴不是把大模型换成儿童语气，而是在每一步做边界判断（v2.1-final 架构）：

| Step | 名称 | 类型 | 作用 |
|---|---|---|---|
| 0 | 记忆检索 | Python | 三层记忆：星球策展 + 情景摘要（per-user 隔离） |
| 1 | 关键词检测 | Python | 5 类风险词库 + 家长话题偏好命中检测 |
| 2 | 风险分类 | LLM | 判定 topic + risk_level + **mode 意图自动识别**（统一对话框） |
| 3 | 策略决策 | Python | 8 种策略：正常/温和引导/危机模板… |
| 4 | Prompt 构建 | Python | 反谄媚规则 + 四档年龄适配 + 策略指令 |
| 5 | LLM 生成 | LLM | 主回复模型生成儿童友好回复 |
| 6 | 批判审计 | LLM | 批判 Agent 二次审查输出（谄媚/依赖/不当引导） |
| 6b | 输出拦截 | Python | 审计告警时整段替换为安全模板（确定性安全阀） |

> 架构说明：v2.1 重构期曾评估并真实加载过 Qwen3Guard 本地安全模型（Step 1b/6c），
> 后经评审决策移除——安全闭环由「关键词（确定性）→ LLM 分类（语义深度）→ 批判审计（输出校验）」
> 三层接力承担，危机模板与 6b 拦截两个确定性安全阀完整保留。
> 决策过程见 `docs/spacemind-proposal/Qwen3Guard-spike验证报告.md` 与 `docs/v2.0-全栈重构方案.md` 第十部分。

---

## 项目结构

```
.
├── core/                     # 安全引擎（8 步 Pipeline，两端复用）
│   ├── pipeline.py           # 主编排（SSE 安全不变量：先审计后流出）
│   ├── age_tiers.py          # 四档年龄分层 + 三档家长可见性（v2.2）
│   ├── guardrails.py         # Step 1 关键词检测（含家长话题偏好）
│   ├── risk_classifier.py    # Step 2 风险分类 + mode 意图识别
│   ├── policy_engine.py      # Step 3 策略决策（8 策略）
│   ├── prompt_builder.py     # Step 4 Prompt 构建（反谄媚 + 四档年龄分层）
│   ├── llm_client.py         # Step 5 LLM 客户端（DeepSeek 双模型）
│   ├── critic_agent.py       # Step 6 批判审计
│   ├── memory_manager.py     # Step 0 策展记忆（小星球）
│   ├── episodic_memory.py    # 情景记忆摘要（纯逻辑）
│   ├── recommendation_engine.py  # 内容推荐（纯 Python，档位距离匹配）
│   ├── proactive_engine.py   # 主动预警（5 类检查）
│   └── daily_challenges.py   # 每日挑战
├── backend/                  # FastAPI 后端
│   ├── main.py               # 入口（单进程托管前端产物 + SPA 回退）
│   ├── config.py             # pydantic-settings（.env / 环境变量）
│   ├── database.py           # SQLAlchemy + SQLite（WAL）+ 旧年龄档幂等迁移
│   ├── models/               # 8 张表（users/sessions/planet/capsules/episodic/alerts/preferences/cocreation_stories）
│   ├── routes/               # auth/chat/planet/capsule/challenges/parent/cocreation
│   ├── services/             # 业务逻辑（chat_service 遵守 SSE 安全不变量；cocreation_service 话题卡+共创故事）
│   ├── seed.py               # 演示账号与演示数据种子（幂等，含预置共创故事）
│   └── tests/                # 36 项 pytest（无 API Key 也可全绿）
├── frontend/                 # React 前端（Vite）
│   └── src/
│       ├── styles/           # 设计 token（docs/DESIGN-anxin.md）
│       ├── pages/            # Landing / ChildHome(儿童主页) / ChildrenChat / MyPlanet / CoCreation / parent/*
│       ├── components/       # GrowthTree / TimeCapsule / SafetyShield ...
│       └── hooks/            # useChat(SSE) / usePlanet / useVoice / useUsageTimer
├── scripts/
│   └── start_server.py       # 生产一键启动（建库+seed+uvicorn）
├── data/                     # 演示案例与演示数据（库文件不入库）
├── docs/                     # 方案书 / 设计系统 / 部署指南 / 重构进展报告
└── app.py + pages/           # Streamlit 旧版（兜底，保持可运行）
```

---

## 技术栈

- **前端**：React 18 + Vite + React Router + Framer Motion + Recharts + Web Speech API（语音）
- **后端**：FastAPI + SQLAlchemy + SQLite（WAL）+ JWT（PIN 登录，pbkdf2 哈希）
- **LLM**：DeepSeek 双模型（v4-pro 主回复 + chat 轻量分类/审计），OpenAI 兼容协议
- **数据**：三层记忆（工作记忆 + per-user 情景记忆 + 策展记忆小星球）
- **设计系统**：`docs/DESIGN-anxin.md`（Lovable 奶油质感 × Shopify 双轨结构 + 粉彩儿童层）

---

## 合规对应

依据《人工智能拟人化互动服务管理暂行办法》（2026.7.15 施行）：

- ✅ 监护人同意流程（注册强制勾选，前后端双保险）
- ✅ 年龄分层（5-7/8-10 守护模式、11-13 过渡模式、14+ 信任模式，家长可见性差异化）
- ✅ AI 身份标识（聊天页常驻徽章 + Prompt 声明，11 岁起明确"没有真实情感"）
- ✅ 2 小时使用时长提醒（亲子话题卡与共创故事为线下亲子活动，不计时）
- ✅ 禁止诱导不安全行为（8 步 Pipeline + 危机模板 + 输出拦截，共创路径同样走完整审计）
- ✅ 禁止虚拟亲密关系（反谄媚机制 + "不替代真人"原则）
- ⚠️ 算法备案（评估中）
