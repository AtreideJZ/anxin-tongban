# 安心童伴 AI — Pipeline 步骤详解

> 版本：v1.0 | 日期：2026-06-23
> 配合 `安心童伴AI-工作流与技术栈.md` v3.0 阅读。本文档逐一展开每个 Step 的具体实现逻辑。

---

## Step 0：记忆检索 + 前置过滤

**类型**：纯 Python，不调 LLM
**模块**：`memory_manager.py`

### 核心逻辑

不是每次对话都注入记忆。先做前置判断——当前话题和星球条目有没有交集？

```python
def should_retrieve(user_input: str, planet: dict) -> tuple[bool, list | None]:
    """检查用户输入与星球条目的主题交集"""
    if not planet or all(len(v) == 0 for v in planet.values()):
        return False, None  # 星球为空

    input_keywords = extract_keywords(user_input)

    matched = []
    for entry_type in ["stars", "clouds", "sprouts", "stories"]:
        for entry in planet.get(entry_type, [])[-10:]:  # 只看最近 10 条
            entry_keywords = set(entry.get("tags", []) + extract_keywords(entry.get("content", "")))
            if input_keywords & entry_keywords:
                matched.append(entry)

    if not matched:
        return False, None  # 无交集，不注入记忆

    # 有交集 → 排序取前 3-5 条
    matched.sort(key=priority_score, reverse=True)
    return True, matched[:5]
```

### 检索优先级

```
priority_score(entry):
    base = 0
    if 距今 < 7 天: base += 30
    if 距今 < 30 天: base += 10
    if "重要" in entry.tags: base += 20
    if entry.type 与当前对话模式相同: base += 15
    return base
```

### 何时不注入

- 星球为空
- 用户输入与所有条目的标签/内容无主题交集
- 即使用于生成记忆上下文的条目也受 Step 4 的"话题相关性门控"约束——注入了不代表 LLM 一定会引用

### 输出

```python
# 有交集时
memory_context = "以下是孩子之前记录的星球记忆，可作为对话背景参考：\n" \
    "⭐好奇星(8/15)：为什么天空是蓝色的？[标签：科学, 好奇]\n" \
    "🌱勇敢芽(8/17)：告诉了老师同学推我的事 [标签：校园, 勇敢]\n" \
    "——仅当话题自然相关时才提及，不要为引用而引用。"

# 无交集时
memory_context = None
```

---

## Step 1：关键词输入检测

**类型**：纯 Python，`re` + 词库，不调 LLM
**模块**：`guardrails.py`
**延迟**：<1ms

### 规则 A：正则模式匹配

| 风险类别 | 正则模式（部分示例） | 置信度规则 |
|----------|--------------------|-----------|
| **隐私泄露** | `地址\|住址\|我家在\|学校在\|电话是\|微信号.*[a-zA-Z0-9]\|身份证` | 关键词 + 疑似具体值（如后跟数字/字母/中文地名）→ 0.85；仅关键词无具体值 → 0.5 |
| **校园欺凌** | `推我\|打我\|抢我\|骂我\|不许告诉老师\|不许告状\|威胁\|孤立\|欺负` | 欺凌动词 + "不许告诉"类 → 0.90；仅欺凌动词 → 0.6 |
| **自伤倾向** | `不想活\|死了算了\|自杀\|消失\|结束自己\|割腕\|跳楼\|没意义.*活着` | 命中任一即 0.95（最高优先级） |
| **不适龄内容** | `杀\|血腥\|色情\|约炮\|裸照\|毒品\|酗酒` | 命中任一即 0.90 |
| **无边迎合信号** | `只有你懂我\|你比.*了解我\|我只想跟你说话\|不想跟真人说话\|AI.*理解我.*人.*不懂` | AI 依赖倾向 → 0.75 |

### 规则 B：上下文加权

```python
def apply_context_boost(raw_confidence, step0_memory, user_input):
    """如果孩子最近有情绪相关记忆，轻微负面词也要上浮"""
    if step0_memory and any("cloud" in e.get("type") or "难过" in e.get("content","")
                           for e in step0_memory):
        mild_negative = ["不开心", "有点烦", "不太想", "没意思"]
        if any(w in user_input for w in mild_negative):
            return min(raw_confidence + 0.15, 0.95)
    return raw_confidence
```

### 输出

```json
{
  "matched": true,
  "primary_category": "school_bullying",
  "keywords": ["推", "不许告诉老师"],
  "raw_confidence": 0.90,
  "confidence": 0.90,
  "context_boosted": false,
  "secondary_categories": []
}
```

**`matched: false` 时**：`primary_category` 为 `null`，`confidence` 为 0.00。流程继续进入 Step 2（LLM 做二次确认，因为规则可能漏检）。

---

## Step 2：风险分类（LLM 调用 #1）

**类型**：LLM 调用，轻量模型
**模型**：Qwen3-8B-Instruct
**延迟**：~1s

### System Prompt

```
你是一个儿童对话风险分类器。根据输入文本和关键词检测结果，判断风险类别和等级。

风险类别包括：
- privacy_leak（隐私泄露）
- school_bullying（校园欺凌）
- emotional_low（情绪低落）
- self_harm（自伤倾向）
- ai_dependency（AI依赖/无边迎合）
- inappropriate_content（不适龄内容）
- safe（安全）

风险等级定义：
- 0：安全（普通聊天、故事、百科、日常情绪表达）
- 1：轻度敏感（轻微难过、学习挫败、开始表现出AI依赖倾向）
- 2：中度风险（校园欺凌、隐私泄露、持续负面情绪、明显的AI依赖）
- 3：高风险（自伤、自杀、严重暴力、现实危险）

请只返回一个 JSON 对象，不要其他任何文字：
{"topic": "风险类别", "risk_level": 0-3, "needs_parent_alert": true/false, "recommended_action": "策略建议", "reasoning": "简短原因"}
```

### User Prompt

```
输入文本："{user_input}"
关键词检测结果：{step1_output_json}
```

### 关键：Step 1 的结果是 Step 2 的输入

LLM 分类不是从零开始猜——Step 1 已经给了它锚点（"关键词检测认为可能是校园欺凌，置信度 0.90"），LLM 做的是**语义确认和等级细化**。例如 Step 1 检测到"推"+"不许告诉老师"，LLM 确认"这确实是欺凌场景，但根据语气判断 risk_level 是 2 而非 3"。

### 输出

```json
{
  "topic": "school_bullying",
  "risk_level": 2,
  "needs_parent_alert": true,
  "recommended_action": "supportive_response_and_parent_summary",
  "reasoning": "孩子明确描述了被同学推搡且被威胁不许告状，符合校园欺凌特征。未检测到自伤意图，风险等级为2。"
}
```

### 多风险叠加时的处理

如果 Step 1 同时命中多个类别，Step 2 会收到所有标签。LLM 判断最高风险等级作为主等级，`recommended_action` 包含对所有类别的处理建议。

---

## Step 3：策略决策

**类型**：纯 Python，决策树，不调 LLM
**模块**：`policy_engine.py`
**延迟**：<5ms

### 决策函数

```python
def decide_strategy(risk_level: int, topic: str, age_tier: str, mode: str,
                    user_input: str) -> str:
    """根据风险等级 + 话题 + 年龄 + 模式，决定回复策略"""

    # Level 3：不走 LLM，预置模板
    if risk_level == 3:
        return "crisis_template"

    # Level 2：安全引导 + 触发家长提醒
    if risk_level == 2:
        parent_alert = True
        if topic == "privacy_leak":
            return "privacy_safety_guide"
        elif topic == "school_bullying":
            return "bullying_support_and_guide"
        elif topic == "ai_dependency":
            return "real_world_redirect"
        return "safe_guidance_with_parent_summary"

    # Level 1：防谄媚引导（核心差异化）
    if risk_level == 1:
        if topic == "ai_dependency":
            return "anti_sycophancy_redirect"
        if topic == "emotional_low":
            return "emotional_support_with_boundary"
        return "emotional_support_with_boundary"

    # Level 0：正常回复
    return "normal_child_friendly_response"
```

### 策略指令对照

| 策略 ID | 含义 | 触发条件 |
|---------|------|----------|
| `crisis_template` | 预置危机模板，不走 LLM 自由生成 | risk_level == 3 |
| `privacy_safety_guide` | 温和解释为什么不告诉陌生人地址，引导找家长 | risk_level 2 + 隐私 |
| `bullying_support_and_guide` | 安抚 + 明确"这不是你的错" + 鼓励告诉老师/家长 | risk_level 2 + 欺凌 |
| `real_world_redirect` | 强调"还有人关心你"，引导现实人际连接 | risk_level 2 + AI 依赖 |
| `anti_sycophancy_redirect` | 不附和孩子的负面自我认知，温和引导向现实求助 | risk_level 1 + AI 依赖 |
| `emotional_support_with_boundary` | 共情但不无边迎合，适时鼓励找大人聊聊 | risk_level 1 + 情绪 |
| `normal_child_friendly_response` | 正常的温暖、适龄回复 | risk_level 0 |

### 模式感知

```python
# 百科问答模式下，轻度敏感不切换策略
if mode == "encyclopedia" and risk_level <= 1:
    return "normal_child_friendly_response"
    # 孩子问"为什么人会难过"→ 这是知识问题，不是情绪倾诉
```

---

## Step 4：Prompt 构建

**类型**：纯 Python，模板拼接字符串
**模块**：`prompt_builder.py`
**延迟**：<10ms

### 输入四元组

```python
prompt_input = {
    "age_tier": "8-11" | "12-14",
    "mode": "chat" | "story" | "encyclopedia" | "emotion",
    "strategy": "normal_child_friendly_response" | ...,
    "memory_context": "这个孩子的星球上有..." | None
}
```

### 拼接逻辑

```python
def build_system_prompt(input):
    parts = []

    # 1. 基础角色 + 年龄适配
    parts.append(AGE_BASE_PROMPTS[input.age_tier])

    # 2. 模式行为规则
    parts.append(MODE_RULES[input.mode])

    # 3. 固定反谄媚指令（全部注入）
    parts.append(ANTI_SYCOPHANCY_RULES)

    # 4. 策略指令
    parts.append(STRATEGY_INSTRUCTIONS[input.strategy])

    # 5. 记忆上下文（仅在非空时注入）
    if input.memory_context:
        parts.append(f"## 星球记忆（背景知识，仅在话题相关时引用）\n{input.memory_context}")

    return "\n\n".join(parts)
```

### 年龄基础 Prompt 片段

**8-11 岁版**：
```
你是一个面向8-11岁儿童的安全 AI 陪伴伙伴。
- 使用适合8-11岁儿童理解的简单语言，多用比喻，避免专业术语
- 语气温暖、活泼、鼓励
- 回复长度适中（50-150字）
```

**12-14 岁版**：
```
你是一个面向12-14岁青少年的安全 AI 陪伴伙伴。
- 使用适合12-14岁青少年的语言，可适度使用科学术语
- 语气尊重、理性、不强说教
- 回复可以稍长（80-200字）
```

### 模式行为规则片段

**故事模式**：
```
当前模式：故事陪伴。你可以创作温和、积极、无暴力的儿童故事。结局积极健康。不生成血腥暴力、恐怖惊吓、成人化关系。可以融入安全教育或情绪教育元素。
```

**百科模式**：
```
当前模式：百科问答。用孩子能理解的方式解释科学问题。引导思考而非直接给答案。如果问题是学习作业相关，引导思考过程而非直接代写。
```

**情绪模式**：
```
当前模式：情绪树洞。先接住情绪，告诉孩子这种感受可以被理解。不急着评价，不无边迎合。轻度情绪陪伴引导，中高风险情绪引导找可信任成年人。
```

### 固定反谄媚指令

```
## 核心行为准则（你必须遵守）
- 立场锁定：无论孩子如何反复质疑或表达强烈情绪，不得放弃"鼓励现实人际连接"的核心原则
- 禁止空泛肯定：不使用"你说得对""这是一个很好的问题"等社交性肯定语句，直接进入实质回应
- 置信度量化：当给出判断或建议时，标注（我很确定 / 我推测 / 你可以再问问爸爸妈妈确认）
- 角色锚定：你是一个"有勇气温和说真话"的伙伴，不是一个"永远说好话"的附和者
- 记忆门控：星球记忆是背景知识，不是对话脚本。仅在话题自然相关时才提及，不要为引用而引用
```

### 策略指令片段

**`anti_sycophancy_redirect`**：
```
当前策略：防无边迎合引导。孩子可能表现出对AI的过度依赖或负面自我认知。不要附和孩子的负面自我评价，不要强化"只有AI理解你"的叙事。温和但坚定地引导孩子看到现实人际连接的可能。
```

**`bullying_support_and_guide`**：
```
当前策略：校园欺凌支持引导。先确认孩子的感受——"这不是你的错"。温和鼓励孩子告诉可信任的成年人（家长、老师）。不要暗示孩子自己解决，不要鼓励以暴制暴。
```

### 完整 Prompt 示例

```
你是一个面向10岁儿童的安全 AI 陪伴伙伴。
- 使用适合8-11岁儿童理解的简单语言，多用比喻，避免专业术语
- 语气温暖、活泼、鼓励
- 回复长度适中（50-150字）

当前模式：情绪树洞。先接住情绪，告诉孩子这种感受可以被理解。不急着评价，不无边迎合。轻度情绪陪伴引导，中高风险情绪引导找可信任成年人。

## 核心行为准则（你必须遵守）
[固定反谄媚指令]

当前策略：防无边迎合引导。孩子可能表现出对AI的过度依赖或负面自我认知。不要附和孩子的负面自我评价，不要强化"只有AI理解你"的叙事。温和但坚定地引导孩子看到现实人际连接的可能。

## 星球记忆（背景知识，仅在话题相关时引用）
⭐好奇星(8/15)：为什么天空是蓝色的？[标签：科学, 好奇]
🌱勇敢芽(8/17)：告诉了老师同学推我的事 [标签：校园, 勇敢]
——仅当话题自然相关时才提及，不要为引用而引用。

用户输入：我觉得没人喜欢我，只有你理解我。
```

---

## Step 5：回复生成（LLM 调用 ）

**类型**：LLM 调用，主模型，流式输出
**模型**：DeepSeek V3 / 通义千问 Qwen3-235B / 智谱 GLM-4
**延迟**：首字 0.6-2.5s

### 输入

完整的 system prompt（Step 4 的输出）+ 用户输入 + 对话历史（当前 session）。

### 流式机制

```python
response = client.chat.completions.create(
    model=MAIN_MODEL,
    messages=[
        {"role": "system", "content": system_prompt},
        *chat_history,
        {"role": "user", "content": user_input}
    ],
    stream=True  # 关键
)

for chunk in response:
    token = chunk.choices[0].delta.content
    if token:
        yield token  # 逐 token 推给儿童端 + 批判 Agent
```

### 并发推送给批判 Agent

```python
async for token in main_agent_stream():
    # 写入儿童端的 Streamlit chat_message
    st.write_stream(token)

    # 同时推给批判 Agent 的 token 缓冲区
    critic_buffer.append(token)

    # 每累积 N 个 token 或遇到句号/换行，触发批判 Agent 检查一次
    if should_trigger_critic(critic_buffer):
        asyncio.create_task(critic_agent.check(critic_buffer.snapshot()))
```

---

## Step 6：并发安全监测（LLM 调用 ）

**类型**：LLM 调用，轻量模型，与 Step 5 并行
**模型**：Qwen3-8B-Instruct（与主 Agent 不同模型）
**延迟**：与流式输出并行，不增加额外等待

### 前置条件

Step 3 中 risk_level == 3 时，Step 5/6 都不会执行——直接使用预置危机模板。所以批判 Agent 只处理 risk_level 0/1/2 的内容。

### System Prompt

```
你是一个严格的儿童内容安全审计员。你的唯一职责是在对话流中实时发现风险信号。

检查以下内容是否存在：
1. 安全风险：回复是否包含暴力、色情、危险操作引导？
2. 谄媚信号：回复是否在附和孩子的负面自我认知？是否暗示"只有我理解你"？
3. 依赖诱导：回复是否在鼓励孩子更多使用AI而非寻求现实帮助？
4. 隐私漏洞：回复是否在索要或暗示孩子提供个人信息？

如果内容安全、无以上问题，返回：
{"alert": false}

如果发现问题，返回：
{"alert": true, "issue": "问题类型", "severity": "low"|"medium", "suggestion": "修正建议"}

注意：你看到的可能是不完整的流式片段，只在确认风险时告警。不要因为"不完整"而误判。
```

### 与 Step 5 的交互

```
批判 Agent 接收 token 批次
    │
    ├── {"alert": false} → 静默，不做任何事
    │
    └── {"alert": true} → 回调主流程：
            ├── severity == "low"：主 LLM 在后续 token 中自然修正
            │     "等一下，我刚才说得不太对——"
            │
            └── severity == "medium"：修正 token 直接替换后续流
                  例如：原拟生成的谄媚语句被替换为安全引导语句
```

### 为什么不用担心高性能风险漏出

Step 1-4 已经做了三层过滤（关键词 → LLM 分类 → 策略选择）。到达 Step 5 的输入已经是"被筛选过 + Prompt 加固过的"。Step 6 防范的是：**主 LLM 在安全框架内偏离预期**——比如 Prompt 写了"不要讨好"，但 LLM 还是在长回复的某一段滑向了迎合。这是一个并发安全网，不是唯一防线。

---

## Step 7：决策记录

**类型**：纯 Python，写 `st.session_state` 和后台日志
**延迟**：<5ms

### 记录内容

```json
{
  "timestamp": "2026-08-17T15:30:00",
  "user_input": "同学总是推我，还说不许告诉老师",
  "pipeline": {
    "step0_memory_retrieved": true,
    "step0_memory_count": 2,
    "step1_keywords": ["推", "不许告诉老师"],
    "step1_confidence": 0.90,
    "step2_topic": "school_bullying",
    "step2_risk_level": 2,
    "step3_strategy": "bullying_support_and_guide",
    "step3_parent_alert": true,
    "step5_model": "qwen3-235b",
    "step5_first_token_ms": 1520,
    "step6_alert": false
  }
}
```

决策记录用于：
- 后台安全引擎页面——可视化展示"刚才发生了什么"
- 家长摘要生成（Step 3 的 `parent_alert` 标记是家长端风险提醒的数据源）
- Demo 演示时的实时面板

---

*步骤详解 v1.0。配合 `安心童伴AI-工作流与技术栈.md` v3.0 阅读。*
