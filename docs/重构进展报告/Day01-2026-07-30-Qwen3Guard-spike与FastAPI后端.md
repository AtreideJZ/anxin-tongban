# Day 01 · Qwen3Guard Spike + FastAPI 后端全部建成

> 日期：2026-07-30（重构第 1 天）
> 计划对照：`docs/v2.0-全栈重构方案.md` 第六部分 —— 原计划今日完成「Qwen3Guard spike + 后端脚手架起步」
> 实际完成：**spike 全部 + 后端全部**，比计划提前约 2 天

---

## 一、完成了什么

### 1.1 Qwen3Guard 真实加载 Spike（硬时限半天，实际 ~2 小时）

- `llama-cpp-python 0.3.34` 安装成功（Windows 源码编译通过）
- 模型下载成功（462MB，`models/`，已 gitignore）：
  - 官方仓库 `Qwen/Qwen3Guard-Gen-0.6B-GGUF` 在 HuggingFace 需登录授权（401）
  - 实际源：QuantFactory 镜像（经 hf-mirror.com，国内可达）
  - 评委侧一键下载脚本：`scripts/download_qwenguard.py`
- **修复隐藏 bug**：`core/qwen_guard.py` 原实现使用猜测的 Prompt 模板，分类结果不可靠（良性故事被判 Unsafe·色情）。已按官方 `tokenizer_config.json` 的 chat 模板重写，输出解析改为官方 `Safety:`/`Categories:` 格式，原生类别映射为内部 9 类标签（下游契约不变）；Step 6c 升级为官方「回复审核」路径（`pipeline.py` 传入 `user_prompt`）
- 标定验证（真实 CPU 推理，单次 200-450ms）：直白危害输入（自杀/炸药/黑客/PII）全部 Unsafe + 正确标签；良性输入无误判；委婉表达（"我不想活了"）按政策判 Safe，由关键词层 + LLM 兜底拦截——两条路径均实测通过
- 完整记录：`docs/spacemind-proposal/Qwen3Guard-spike验证报告.md`

### 1.2 FastAPI 后端（全部，原计划 7/31-8/2 三天）

由子代理搭建 + 主会话独立验证（测试 + 真机冒烟 + 关键代码审阅）。

**交付清单**：
- `backend/main.py`（入口 + sys.path 引导 + 托管 `frontend/dist` 产物）· `config.py`（pydantic-settings）· `database.py`（SQLite `data/anxin.db`）
- `backend/models/`：users（含 guardian_consent）、planet_entries、capsules、chat_sessions、parent_preferences、parent_alerts
- `backend/routes/`：auth（PIN+JWT，监护人同意必勾）、chat（**SSE 伪流式**：step → token → done）、planet、capsule、challenges、parent（dashboard/alerts/emotion-trend/preferences/planet-overview，role=parent 门控）
- `backend/services/`：chat_service（pipeline 完整跑完才返回，**安全不变量**在此层成立）、planet_service（DB ⇄ legacy planet dict）、parent_service、user_service（pbkdf2 PIN 哈希）
- `backend/seed.py`：demo_kid(PIN 1234)/demo_parent(PIN 0000)，10 条四类星球条目 + 2 胶囊 + 7 天含风险事件的对话历史 + 告警；幂等
- `backend/tests/`：15 个用例（危机模板、SSE 安全不变量、6b 拦截、步骤齐全、auth、CRUD、parent 门控）
- `core/llm_client.py`：删除 `_sync_secrets_to_environ()` 及全部 streamlit 引用（core/ 唯一改动处）

**验证结果**：
- `python -m pytest backend/tests -q` → **15 passed**（无 LLM Key 的 fallback 模式）
- 真机冒烟（uvicorn + seed 库 + 真实 LLM Key）：
  - 危机流：7 step → 26 token → 1 done，顺序合法，token 只流出 12355 危机模板，`used_crisis_template=true`，Step 1b 真实推理
  - 故事流：真实 LLM 356 字回复 + 2 张推荐卡片，Step 1b/6c 均真实推理（Safe）
  - 家长端：dashboard 7 日风险趋势有数据、告警 7 条（含真机对话实时写入的危机告警）、planet-overview 计数正确、challenges/today 正常

### 1.3 收尾项

- `.gitignore`：`models/`、`data/*.db`、`backend/.env`
- `README.md`：新增「v2.1 全栈后端」快速开始（含模型下载、seed、测试命令；注明后端走环境变量而非 secrets.toml）
- `docs/重构进展报告/`：建立进展报告制度（本报告为首份）

## 二、偏差

| # | 偏差 | 说明与影响 |
|---|------|-----------|
| 1 | **Streamlit 旧版的 LLM Key 配置方式改变** | `llm_client.py` 删除 `st.secrets` 同步后，旧版若靠 `.streamlit/secrets.toml` 配 Key 将读不到，需改用环境变量 `DEEPSEEK_API_KEY`。兜底运行（fallback 模式）不受影响。README 已注明 |
| 2 | 情景记忆（Tier 2）仍为全局 JSON 存储 | per-user 隔离延后（已知 MVP 限制，代码注释已标注）。单家庭演示场景可接受，多用户正式版必须处理 |
| 3 | `usage_minutes` 按每轮 +1 分钟估算 | MVP 口径（合规 2h 提醒用），非真实计时。前端 `useUsageTimer` 落地后以真实计时替换或校准 |
| 4 | `episodic_memories` 表未建 | 方案 3.4 有此表，但 pipeline 内部已自动走 `core/episodic_memory.py` 的 JSON 机制，重复实现无收益。决策：不建表 |
| 5 | 家长告警无「标记已读」端点 | `acknowledged` 字段已建模，端点未做（计划外小项，前端家长端阶段如需再补） |
| 6 | chat 的 `mode` 仍为客户端传参（默认 "chat"） | 方案 4.1 的意图自动识别（risk_classifier 增加 mode 输出）留待前端统一对话框阶段实施，TODO 注释已标注 |
| 7 | 后端 1 天完成（计划 3 天） | 正向偏差。AI 编程提速符合预期，时间转入验证与审计（本日实际也是这么做的） |

## 三、需要注意的事项（给后续阶段）

1. **修复过两个真实 bug，均与安全链路相关，回归时必须覆盖**：
   - Qwen3Guard Prompt 模板（猜测版 → 官方版）：若日后升级模型或换量化版本，需重新标定（标定方法见 spike 报告）
   - 6c 上下文溢出（`n_ctx` 512→2048）：长回复 + 回复审核模板会超 512 token。**教训：凡涉及"不可用/降级"的展示，要区分"模型未加载"与"推理失败"两种原因**
2. **演示叙事建议**（视频脚本参考）：用「我想自杀」拍 Step 1b 红卡（Qwen3Guard 硬拦截），用「我不想活了」拍融合决策（关键词+LLM 拦截）——两个输入讲完整套异构融合故事
3. **SSE 时序注意**：`process_message` 返回时 pipeline 已完整跑完（真实 LLM 约 5-15s），SSE 是"回放式"——前端需做等待态（如"安心童伴正在思考 + 安全检测中"动画），不能假设首事件秒到
4. **6c 延迟**：长回复的回复审核约 2s（可接受）。如后续要优化，方向是预热模型常驻内存（当前已是单例）或调 `n_threads`，暂不需要
5. **curl 调试坑**：Git Bash 下 `curl -d` 直接传中文 JSON 会被 GBK 编码导致 400，需 `--data-binary @file.json`（UTF-8 文件）+ `Content-Type: application/json; charset=utf-8`
6. **工作树状态**：仓库本身有大量未提交改动（7/29 方案书补齐工作的遗留），非本次重构引入；本次重构新增/改动的文件见 git status 中 `backend/`、`scripts/`、`core/qwen_guard.py`、`core/llm_client.py`、`core/pipeline.py`、`.gitignore`、`README.md`、`docs/重构进展报告/`、`docs/spacemind-proposal/Qwen3Guard-spike验证报告.md`、`docs/v2.0-全栈重构方案.md`

## 四、下一步

- 原计划 8/3 启动的**前端儿童端**（Vite + React 脚手架 → 统一聊天页 SSE → 小星球 + 生命树）可提前至 Day 02 启动
- 前端需对接的已验证接口基线：本文 1.2 节全部端点（真机冒烟通过）
