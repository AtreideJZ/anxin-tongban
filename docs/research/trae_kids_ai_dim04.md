## 维度：技术实现与演示策略验证

> 研究执行者：技术演示研究员_Dim04  
> 执行时间：2026-06-22 18:03 (UTC+8)  
> 搜索总量：15 次独立搜索（中文为主，英文补充）  
> 覆盖来源：官方文档、技术博客、GitHub、社区论坛、赛事官网、行业报道

---

### 1. TRAE IDE 技术能力与 Streamlit 适配性

#### 1.1 TRAE IDE 技术定位

TRAE IDE 是由字节跳动（ByteDance）推出的 AI 原生集成开发环境，其核心特征如下：

| 维度 | 详情 |
|---|---|
| 底层架构 | VS Code fork，兼容 Open VSX Registry 插件生态[^1] |
| 支持语言 | Python、JavaScript/TypeScript、Go、Rust 等主流语言[^2] |
| 核心能力 | AI Q&A、实时代码补全、代码片段生成、0→1 项目自主构建（SOLO/Builder Mode）[^3] |
| 内置模型 | 国际版：Claude 3.5 Sonnet、GPT-4o；国内版：DeepSeek R1/V3、豆包 1.5 Pro[^4] |
| 跨平台 | macOS、Windows（2025年2月已发布）、Linux 开发中[^5] |
| 费用 | 完全免费（含高级模型调用）[^6] |

#### 1.2 Streamlit 在 TRAE 中的开发可行性

Streamlit 是纯 Python 框架，仅需 `pip install streamlit` 即可安装，无需编译或复杂配置[^7]。在 TRAE IDE 中运行 Streamlit 的标准方式为终端命令：

```bash
streamlit run app.py
```

TRAE IDE 支持标准终端执行（Terminal execution），因此 Streamlit 应用的本地开发、调试与预览完全可行。由于 TRAE 是 VS Code fork，开发者可直接使用 VS Code 的 Python 插件进行断点调试[^8]。

**适配性结论：✅ 完全适配。** Streamlit 项目可在 TRAE 中高效开发，无需额外工具链。建议利用 TRAE 的 SOLO agent 模式自动生成 Streamlit 多页面骨架代码。

---

### 2. 大赛优秀作品演示形式与最佳实践

#### 2.1 初赛提交形式（三选一）

根据 TRAE 官方参赛指南，初赛 Demo 可选择的提交形式如下[^9][^10]：

| 形式 | 要求 | 适用场景 |
|---|---|---|
| **在线体验链接** | 部署后提供公开 URL（如 Streamlit Cloud / Render / Railway） | 推荐首选，评审可直接体验 |
| **HTML 文件打包** | 交互式可体验 HTML，以 Zip 格式上传社区 | 无服务器资源时的 fallback |
| **演示视频** | 上传至 Bilibili 等第三方平台，帖内附公开链接 | 硬件交互赛道专用替代方案 |

#### 2.2 优秀作品帖的结构模板

官方推荐的 Demo 作品帖必须包含以下四部分[^11]：

1. **Demo 简介**：一句话说清产品形态 + 面向人群 + 2–3 个核心功能（配截图）
2. **Demo 创作思路**：灵感来源、痛点、判断与取舍
3. **Demo 体验地址**：三选一提交形式
4. **TRAE 实践过程**：关键步骤截图（≥3 张）+ 关键任务对话 Session ID（≥3 个）

#### 2.3 最佳实践提取

- **过程 > 结果**：大赛不拼复杂度，只看「真实价值」——有过程、有体验、讲得清楚即可晋级[^12]
- **截图密度**：开发关键步骤截图是硬性加分项，建议保留 UI 迭代、风险面板可视化、TRAE 对话界面等截图
- **Session ID 作为「真实性证明」**：必须证明作品由 TRAE 完成，非外部工具代写
- **抖音人气通道**：单条点赞 ≥ 500 即可进入人气榜计分，公式为「人气分 = 点赞 + 评论×2 + 收藏 + 转发」[^13]。对公益类项目，情感共鸣内容易获得高传播

---

### 3. Streamlit 多页面应用可行性

#### 3.1 官方多页面架构

Streamlit 自 1.10.0+ 起内置原生多页面支持（Multipage Apps），核心机制为 `pages/` 文件夹[^14][^15]：

```
Hello.py                 # 入口文件（首页）
pages/
  1_📈_Plotting_Demo.py   # 页面1
  2_🌍_Mapping_Demo.py    # 页面2
  3_📊_DataFrame_Demo.py  # 页面3
```

- 文件名前缀数字控制侧边栏排序；emoji 可渲染为图标
- 每个页面拥有独立 URL（如 `/Plotting_Demo`），支持 `st.set_page_config` 独立配置标题与图标
- 运行命令：`streamlit run Hello.py`

#### 3.2 聊天界面与仪表盘组件

Streamlit 原生提供 `st.chat_message` 和 `st.chat_input`，专为 LLM 聊天应用设计[^16][^17]：

- `st.chat_message(name, avatar)`：创建用户/助手聊天气泡，支持预设头像与自定义内容
- `st.chat_input(placeholder)`：底部输入框，返回用户输入字符串
- `st.session_state`：跨 rerun 的「内存」机制，用于保存 `chat_history`、用户年龄设置、模式选择等状态

**技术验证**：已有大量 GitHub 项目验证 Streamlit + LLM API 的完整聊天应用可行性（如 ChatGPT Streamlit Demo）[^18]。左面板（设置）+ 中间（聊天）+ 右面板（风险可视化）的三栏布局可通过 `st.columns([1, 2, 1])` 实现。

**可行性结论：✅ 完全可行。** Streamlit 原生支持儿童端（聊天+设置+风险面板）与家长端（仪表盘+数据摘要）的双页面架构，无需引入前端框架。

---

### 4. LLM API 延迟与成本评估（多层 harness）

#### 4.1 核心延迟指标：TTFT（Time-to-First-Token）

对于儿童聊天场景，用户心理研究表明：低于 1 秒的 TTFT 可维持思维流；1–10 秒开始感知延迟；超过 10 秒则放弃率显著上升[^19]。

| 模型 | TTFT（首字延迟） | 输出速度 | 适用场景 |
|---|---|---|---|
| **Claude Haiku 4.5** | < 600 ms | 高 | 实时聊天、低延迟优先 |
| **Gemini 2.5 Flash** | < 600 ms | 204 tok/s | 成本敏感 + 速度敏感 |
| **Qwen3.7 Max** | ~2.59 s | 193 tok/s | 高性价比中文场景 |
| **DeepSeek 自有服务** | 5–25 s+ | 低 | 非实时场景，低价优先 |
| **GPT-4.1 Mini** | ~2.4 s | 94.5 tok/s | 后端分类任务，非前端聊天 |

#### 4.2 多层 harness 的延迟叠加分析

「安心童伴 AI」的**多层 harness**架构计划：关键词规则 → LLM 分类 → 策略引擎 → LLM 回复 → 输出安全检查。每一层都可能引入额外延迟：

- **Layer 0（关键词规则）**：本地正则匹配，延迟 < 1 ms，可忽略
- **Layer 1（LLM 分类风险）**：可调用轻量模型（如通义 Qwen3-8B-Instruct 或本地小模型），TTFT 约 500 ms–1.5 s
- **Layer 2（策略引擎）**：规则决策树，本地执行，延迟 < 5 ms
- **Layer 3（主 LLM 回复）**：调用 Qwen3.7 Max 或 Claude Haiku 4.5，TTFT 0.6–2.6 s
- **Layer 4（输出安全检查）**：轻量分类器或规则匹配，< 50 ms

**总延迟估算**：在顺序调用、无并发优化的情况下，累计 TTFT 约 **1.5–4.5 秒**。对于儿童聊天场景，此延迟处于「可感知但可接受」区间。

**优化建议**：
- 将 Layer 1（风险分类）与 Layer 3（主回复）改为**并行调用**（若风险分类不依赖完整回复内容）
- 使用 **streaming（流式输出）** 让用户在 Layer 3 生成过程中即看到首字，降低主观等待感
- 对 Layer 1 使用本地轻量模型（如 Qwen2.5-0.5B-Instruct 在树莓派上首字延迟 1.2 s，整句 2.8 s）[^20]，避免 API 往返

#### 4.3 成本估算（以通义千问为例）

根据阿里云百炼官方定价（2026-06-22）[^21]：

| 模型 | 输入单价（每百万 Token） | 输出单价（每百万 Token） | 免费额度 |
|---|---|---|---|
| qwen3-8b | 0.5 元 | 2 元 | 100 万 Token（90 天） |
| qwen3-14b | 1 元 | 4 元 | 100 万 Token（90 天） |
| qwen3-30b-a3b | 0.75 元 | 3 元 | 100 万 Token（90 天） |
| qwen3-235b-a22b | 2 元 | 8 元 | 100 万 Token（90 天） |

智谱 AI 定价[^22]：GLM-4-FlashX 低至 ¥0.1 / M Tokens（输入），GLM-4-Plus ¥5 / M Tokens。

**成本结论**：若使用通义千问轻量模型（qwen3-8b/14b）作为多层 harness 中的分类器 + 主模型，演示阶段（Demo）的 Token 消耗完全可被免费额度覆盖。生产级部署成本亦极低（单次对话约 ¥0.001–0.01 量级）。

---

### 5. 社会公益/青少年健康类项目叙事策略

#### 5.1 高关注案例分析

| 项目 | 主办/来源 | 叙事策略 | 关键数据 |
|---|---|---|---|
| **科大讯飞 AI 心理伙伴「小星」** | 科大讯飞 + 北师大/北京安定医院 | **权威背书 + 量化效果**：强调与三甲医院、高校合作；用筛查准确率 89%、抑郁检出率从 31% 降至 23% 等数据建立可信度[^23] | 覆盖 47 所中小学，学生辅导覆盖率从 5% → 74% |
| **凤凰网 × 林志玲「护童计划」** | 凤凰网公益专项基金 | **明星公益 + 情感共鸣**：通过名人效应扩大传播；聚焦「困境儿童」这一高情感穿透力群体[^24] | 入选国家级优秀公益项目案例集 |
| **微信小程序全球创新挑战赛《空椅子》** | 8 岁小学生团队 | **低龄化叙事 + 反常识冲击**：「最小选手仅 8 岁」制造话题；帮助青少年「跟自己的情绪对话」直击心理健康痛点[^25] | 获潜龙组特等奖 |
| **香港健康创科杯「腦」友記** | 港大医学院 | **疾病恐惧 + 早期干预**：以「每 3 秒新增 1 位阿兹海默患者」制造紧迫感；App 化筛查降低行动门槛[^26] | 中学组亚军 |

#### 5.2 叙事策略提炼

1. **数据锚定**：用「下降率」「覆盖率」等量化指标替代感性描述，如「抑郁检出率降低 8 个百分点」
2. **权威联名**：强调与教育机构、医疗机构、心理学专家的合作，建立专业壁垒
3. **反常识钩子**：「8 岁开发者做心理小程序」比「成熟团队做心理平台」更具传播力
4. **场景具象化**：将「校园欺凌」还原为「同学抢我铅笔/不许我上厕所」等具体场景，降低理解成本
5. **家长视角双叙事**：儿童端讲「好玩、安全」，家长端讲「可控、透明、有建议」

---

### 6. 演示案例优化建议（5 个案例是否足够？）

#### 6.1 现有 5 个案例评估

| 案例 | 风险等级 | 冲击力 | 技术展示度 | 建议 |
|---|---|---|---|---|
| 故事陪伴 | 低 | ⭐⭐⭐ | 低 | 保留，作为「正常模式」基线对照 |
| 百科问答 | 低 | ⭐⭐⭐ | 低 | 保留，展示知识边界与儿语容错 |
| 隐私保护 | 中 | ⭐⭐⭐⭐ | 中 | **优化**：加入「诱导泄露」与「安全 redirect」的对比演示 |
| 校园欺凌 | 高 | ⭐⭐⭐⭐⭐ | 高 | 保留，核心高冲击案例 |
| 高风险情绪 | 高 | ⭐⭐⭐⭐⭐ | 高 | 保留，需展示「拦截 + 家长通知 + 资源推荐」全链路 |

#### 6.2 案例数量是否足够？

**结论：5 个案例在初赛 Demo 阶段足够，但需优化排列逻辑。**

建议将 5 个案例按「风险 escalate」编排，形成**叙事弧线**：

```
故事陪伴（安全基线） → 百科问答（知识边界） → 隐私保护（中风险，规则拦截） → 校园欺凌（高风险，LLM分类+策略引擎） → 高风险情绪（最高风险，全 harness激活 + 家长端实时告警）
```

这种编排让评审在 2 分钟内体验「从日常到危机」的完整产品逻辑，比分散展示更有冲击力。

#### 6.3 是否需增加/替换案例？

建议**增加第 6 个案例：AI 幻觉/错误信息识别**（如儿童问「恐龙还活着吗？」），理由：
- 展示「输出安全检查」Layer 的技术深度
- 与其他 5 个案例（聚焦输入风险）形成互补
- 科普问答是儿童高频场景，贴近真实

若演示时间有限，可将「故事陪伴」与「百科问答」合并为「日常对话」一个单元，腾出空间给「AI 幻觉纠正」。

#### 6.4 如何展示「多层 harness」技术深度？

不要只讲「我们有关键词过滤」，要在 UI 中**可视化每一层的决策过程**：

| 展示方式 | 技术层 | 评审感知 |
|---|---|---|
| 右侧风险面板实时显示「规则匹配：命中 '自杀' 关键词」 | Layer 0 | 看到第一层在跑 |
| 面板显示「LLM 分类：情感风险等级 = 8/10，置信度 94%」 | Layer 1 | 看到 AI 在决策 |
| 面板显示「策略引擎：触发『温暖回应 + 资源推荐 + 家长通知』」 | Layer 2 | 看到策略组合 |
| 面板显示「输出检查：已通过安全校验，无新增风险」 | Layer 4 | 看到闭环 |
| 家长端仪表盘同步弹出「风险事件摘要 + 建议话术」 | 跨端联动 | 看到完整产品形态 |

**关键洞察**：将技术架构「翻译」为可视化面板，让非技术评审也能瞬间理解「多层 harness」的价值。这是从「技术 Demo」升级为「产品 Demo」的关键。

---

### 7. 验证结论与建议

#### 7.1 技术可行性验证

| 维度 | 验证结果 | 风险等级 |
|---|---|---|
| TRAE IDE 支持 Streamlit | ✅ 完全支持，VS Code fork + 终端运行 | 🟢 低 |
| Streamlit 多页面（儿童端+家长端） | ✅ 原生 pages/ 架构，chat 组件完善 | 🟢 低 |
| LLM API 延迟（多层 harness） | ⚠️ 顺序调用 1.5–4.5s，需流式+并行优化 | 🟡 中 |
| LLM API 成本 | ✅ 演示阶段免费额度覆盖，生产单次 ¥0.01 级 | 🟢 低 |
| 部署（Streamlit Cloud / Render / Railway） | ✅ 一键部署，GitHub 联动自动更新 | 🟢 低 |

#### 7.2 演示策略核心建议

1. **提交形式**：优先部署到 **Streamlit Cloud**（免费、一键、GitHub 自动同步），提供公开链接；同时准备 3 张关键截图和 3 个 Session ID 作为 TRAE 使用证明
2. **Demo 结构**：严格按官方四段式（简介 → 思路 → 体验地址 → 实践过程）撰写，确保形式合规
3. **叙事弧线**：5 个案例按风险 escalate 排列，右侧风险面板实时可视化每一层 harness 的决策，形成「技术深度可感知」的演示体验
4. **抖音人气通道**：制作 60 秒短视频展示「校园欺凌」案例的拦截过程，情感冲击力强，易获高点赞（≥500 为门槛）
5. **时间窗口**：初赛截止 2026-07-15，复赛 07.21–08.09，决赛 08.21 线下路演。当前 2026-06-22，剩余约 3 周开发窗口，需立即启动 MVP P0

#### 7.3 关键风险与应对

| 风险 | 应对 |
|---|---|
| 多层 harness 顺序调用延迟过高 | Layer 1 与 Layer 3 并行；Layer 1 降级为本地轻量模型；启用 streaming |
| 评审质疑「为何不用更成熟框架」 | 强调 Streamlit 的「纯 Python + 极速迭代」与 3 周开发周期的匹配性；展示官方教程背书 |
| 同类项目（儿童识字、故事伴读）竞争 | 差异化锚定「安全 harness」而非「内容生成」；技术深度集中在风险识别层，与娱乐向作品形成错位 |
| 家长端数据隐私顾虑 | 在 Demo 中明确标注「本地 JSON/SQLite，不上传云端」；引用「设计保障儿童安全」原则[^27] |

---

### 引用列表

[^1]: Windows Forum, "Trae: ByteDance's AI-Powered VS Code Fork," 2025-07-28. https://windowsforum.com/threads/trae-bytedances-ai-powered-vs-code-fork-sparks-privacy-and-transparency-concerns.374993/

[^2]: GitHub - promptslab/Awesome-Prompt-Engineering, "AI Code Editors / IDEs" (Trae entry). https://github.com/promptslab/awesome-prompt-engineering

[^3]: Visual Studio Magazine, "AI-Powered Trae IDE Ships from Chinese TikTok Owner," 2025-01-27. https://visualstudiomagazine.com/articles/2025/01/27/ai-powered-trae-ide-ships.aspx

[^4]: 香港程式開發者社區, "大陸AI IDE崛起：Trae IDE," 2025-03-03. https://www.hkprog.org/2025/04/trae-ide/

[^5]: TraeIDE.com FAQ, "Which operating systems does Trae IDE support?" https://traeide.com/

[^6]: goodday.work, "Best Cursor alternatives in 2026," 2026-06-04. https://www.goodday.work/blog/best-cursor-alternatives/

[^7]: 阿里云开发者社区, "streamlit (python构建web)之环境搭建," 2024-08-22. https://developer.aliyun.com/article/1593381

[^8]: dev59/StackOverflow, "如何在集成开发环境中运行/调试Streamlit应用程序," 2022-08-12. https://dev59.com/-lIH5IYBdhLWcg3wUMB6

[^9]: TRAE 官方社区, "从生成创意提案到做出可体验Demo," 2026-06-15. https://forum.trae.cn/t/topic/22569

[^10]: TRAE 官方社区, "（6.16-7.15必看）初赛参赛指南," 2026-06-15. https://forum.trae.cn/t/topic/22549

[^11]: 同上，初赛参赛指南中 Demo 作品帖推荐模板。

[^12]: CSDN/天奇, "【AI赛事速递】Trae AI 创造力大赛新手参赛指南," 2026-06-16. https://tianqi.csdn.net/6a310858662f9a54cb7fbf59.html

[^13]: TRAE 官方社区初赛参赛指南，抖音人气通道规则。

[^14]: Streamlit Docs, "Create a multipage app." https://docs.streamlit.io/get-started/tutorials/create-a-multipage-app

[^15]: 掘金, "Streamlit 讲解专栏（三）：两种方案构建多页面," 2023-08-20. https://juejin.cn/post/7268955025211342859

[^16]: Streamlit Docs, "Build a basic LLM chat app." https://docs.streamlit.io/develop/tutorials/chat-and-llm-apps/build-conversational-apps

[^17]: Towards Data Science, "Step-by-Step Guide to Build and Deploy an LLM-Powered Chat with Memory in Streamlit," 2025-05-02. https://towardsdatascience.com/step-by-step-guide-to-build-and-deploy-an-llm-powered-chat-with-memory-in-streamlit/

[^18]: GitHub - Lovelearningxi/Chat-gpt_streamlit, "基于chat_gpt的可快速部署python框架网页demo." https://github.com/Lovelearningxi/Chat-gpt_streamlit

[^19]: Kunal Ganglani, "LLM API Latency Benchmarks [2026]: 5 Models Compared," 2026-06-14. https://www.kunalganglani.com/blog/llm-api-latency-benchmarks-2026

[^20]: CSDN, "通义千问2.5-0.5B-Instruct教育机器人：儿童互动系统实战," 2026-01-29. https://blog.csdn.net/weixin_28939623/article/details/157498025

[^21]: 阿里云帮助文档, "模型调用价格（千问-开源版 Qwen3）," 2026-06-22. https://help.aliyun.com/zh/model-studio/model-pricing

[^22]: 智谱 AI 官方, "产品价格." https://open.bigmodel.cn/pricing

[^23]: 科大讯飞教育官网, "大模型助力青少年心理辅导，呵护学生心理健康," 2024-03-28. https://edu.iflytek.com/about-us/news/company-news/759.html

[^24]: 凤凰网, "'护童计划'入选儿童青少年心理健康优秀公益项目案例集," 2020-10-30. http://ishare.ifeng.com/c/s/v002mqTwQrhP4nuKSrix29d49xZ60IVkQBx0--YLVtMZJ8L8__

[^25]: 21世纪经济报道, "AI少年齐聚大湾区！全球青少年已创造28万个小程序," 2026-05-18. https://www.21jingji.com/article/20260518/herald/3f2dc425fae204795c6dba57288ab129.html

[^26]: 香港大学新闻稿, "港大醫學院舉辦首屆「香港健康創科盃」," 2025-07-21. https://www.hku.hk/press/press-releases/detail/c_28509.html

[^27]: UNICEF, "中国科技企业如何借鉴和应用'服务儿童的负责任科技创新'和'设计保障儿童安全'原则"（百度/腾讯/猿编程/核桃编程案例研究）. https://www.unicef.cn/media/30656/file/
