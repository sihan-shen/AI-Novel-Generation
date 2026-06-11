# Agent 化重构设计文档

> 版本：v1.4
> 日期：2026-06-11
> 状态：设计完成，已通过审阅（第四轮：并发控制、动态干预、崩溃恢复）

---

## 1. 目标与范围

### 1.1 目标

将现有"人类在环"的 LLM 辅助写作工具，重构为 **Agent 驱动的自主写作系统**。核心能力：

- Agent 自行从设定集中查询和获取信息
- Agent 自行写作章节正文
- Agent 自行审阅产出质量
- Agent 自行更新设定集（提案或直接写入）

### 1.2 设计决策

| 决策点 | 选择 |
|--------|------|
| Agent 架构 | 主编调度模式 (Orchestrator) + 协作空间元素 |
| Agent 数量 | 3 个专用 Agent：Writer / Reviewer / Setting Manager |
| 用户角色 | 主编 (Editor-in-Chief)，通过对话界面调度 Agent |
| 自主程度 | 渐进式：三个维度可独立配置 |
| UI 策略 | 混合：新增 Agent 对话界面 + 保留现有手动工坊 |
| 技术方案 | Agent Framework + Tool-Calling Loop |

### 1.3 不在范围内

- 不替换现有手动编辑页面
- 不修改现有 Service 层逻辑
- 不改变现有数据表结构（只在已有表上增加 nullable 字段）
- 不引入外部 Agent 框架依赖（LangChain 等）

---

## 2. 总体架构

```
┌──────────────────────────────────────────────────────────┐
│                    Web UI                                 │
│   ┌─────────────────────┐  ┌───────────────────────────┐ │
│   │  Agent 对话界面 (新)  │  │  手动工坊 (现有页面保留)   │ │
│   │  /project/{id}/agent │  │  outline/writer/settings  │ │
│   └──────────┬──────────┘  └─────────────┬─────────────┘ │
├──────────────┼───────────────────────────┼───────────────┤
│              │        Routers             │               │
│   ┌──────────┴──────────┐  ┌─────────────┴─────────────┐ │
│   │  agent_router (新)  │  │  现有 routers (不动)       │ │
│   │  POST /chat/stream  │  │                            │ │
│   │  GET  /tasks        │  │                            │ │
│   └──────────┬──────────┘  └─────────────┬─────────────┘ │
├──────────────┼───────────────────────────┼───────────────┤
│              │       Agent Layer (新增)                   │
│   ┌──────────┴──────────────────────────────────┐       │
│   │              Orchestrator                    │       │
│   │   ┌──────────┐ ┌──────────┐ ┌────────────┐ │       │
│   │   │ Writer   │ │ Reviewer │ │ Settings   │ │       │
│   │   │ Agent    │ │ Agent    │ │ Mgr Agent  │ │       │
│   │   └─────┬────┘ └─────┬────┘ └──────┬─────┘ │       │
│   │         └────────────┼─────────────┘        │       │
│   │                 ┌────┴────┐                  │       │
│   │                 │Blackboard│                 │       │
│   │                 └─────────┘                  │       │
│   └──────────────────────┬───────────────────────┘       │
│                          │ 调用 Tools                     │
├──────────────────────────┼───────────────────────────────┤
│              Service 层 (现有，不动)                       │
│   Project / Outline / Setting / Chapter / Style          │
│   Review / Brainstorm / Search / Cleaning               │
├──────────────────────────┼───────────────────────────────┤
│              LLM 层 (现有，扩展)                           │
│   Adapter / ContextBuilder / Prompts / Templates        │
│   + Agent-specific prompt templates (新增)              │
├──────────────────────────┼───────────────────────────────┤
│              Data 层 (现有，少量扩展)                       │
│   + agent_tasks 表   + agent_messages 表                │
│   + settings 表扩展  + chapters 表扩展  + reviews 表扩展  │
└──────────────────────────────────────────────────────────┘
```

**核心原则**：
- Agent 层只新增不替换
- Agent 通过 Tool 调用 Service，不跨层直接访问数据库
- 手动工坊和 Agent 对话共享同一套底层数据和 Service
- 用户随时可切回手动页面，Agent 产出的所有内容在数据库里可见可编辑

---

## 3. Agent 基类与 Tool-Calling 循环

### 3.1 循环机制

```
观察 (Blackboard state) → 思考 (LLM decide) → 行动 (Tool execute) → 结果写回 Blackboard → 循环
```

终止条件：LLM 返回 `finish` 动作 或 达到 `max_steps`（默认 15）

### 3.2 核心数据结构

```python
class AgentConfig:
    system_prompt: str          # Agent 的系统提示词
    tools: list[Tool]           # 可调用的工具列表
    model: str                  # 使用的 LLM 模型
    temperature: float = 0.7
    max_steps: int = 15
    token_budget: int = 100_000 # 单次 Agent 运行的最大 token 消耗

class Tool:
    name: str
    description: str            # 写入 LLM prompt
    parameters: dict            # JSON Schema 参数定义
    handler: Callable           # 实际执行的 Python 函数
    confirm_before: bool = False
    idempotent: bool = True     # 重复调用是否安全（幂等），默认要求为 True

class AgentStep:
    thought: str
    tool_name: str | None
    tool_args: dict | None
    result: str
    token_usage: dict

class AgentRunResult:
    steps: list[AgentStep]
    output: str
    blackboard_changes: dict
    status: str                 # 'completed' | 'max_steps_reached' | 'budget_exceeded' | 'error'
    error_code: str | None      # 'llm_unavailable' | 'tool_timeout' | 'db_error' | 'rate_limited' | 'malformed_response' | ...
    retry_count: int = 0

# 错误码映射表与重试策略
RETRY_POLICY = {
    'llm_unavailable':     {'max_retries': 3, 'backoff': 'exponential'},
    'tool_timeout':        {'max_retries': 2, 'backoff': 'exponential'},
    'rate_limited':        {'max_retries': 5, 'backoff': 'exponential'},
    'db_error':            {'max_retries': 0, 'backoff': None},       # 不重试，直接失败
    'malformed_response':  {'max_retries': 2, 'backoff': 'immediate'}, # 见 §3.4
    'budget_exceeded':     {'max_retries': 0, 'backoff': None},
}
```

### 3.3 循环执行逻辑

1. 组装 messages：system prompt + Blackboard 上下文 + 对话历史
2. 检查 token 预算：累计消耗 > `token_budget` 则强制 `status='budget_exceeded'` 退出
3. 调用 LLM，要求输出 JSON：`{"thought": "...", "tool": "tool_name", "args": {...}}` 或 `{"action": "finish", "summary": "..."}`
   - LLM 使用非流式模式获取完整 JSON（保证 JSON 解析完整性）。`thought` 字段在获得完整响应后一次性推送到前端
   - Phase 4 可选增强：启用 LLM 流式模式，边接收边解析，将 `thought` 的内容以 `thinking_chunk` SSE 事件逐字符推送给前端，减少用户等待感（JSON 完整性通过缓冲区 + 流式解析器保证）
4. 解析 LLM 响应（见 §3.5 鲁棒性处理）
5. 如果 `finish` → 退出循环，返回结果
6. 如果 `tool` → 检查 `confirm_before` 和自主级别配置
   - 需要确认 → 暂停循环，通过 SSE 推送确认请求，等待用户响应（见 §3.6 确认机制）
   - 不需要确认 → 执行 Tool，结果写回 Blackboard，进入下一步
7. 达到 `max_steps` → 强制要求 LLM 给出 finish

### 3.4 LLM 输出鲁棒性

Agent 循环依赖 LLM 输出结构化 JSON，必须处理格式异常：

| 异常类型 | 处理策略 |
|----------|---------|
| JSON 格式错误 | 将原始响应文本原样放回 messages，追加系统消息"上一轮输出不是有效 JSON，请用 JSON 格式重新输出"。最多重试 2 次，第 3 次仍失败则终止，状态 `error` |
| `tool` 名称不在注册表中 | 追加系统消息"工具 'xxx' 不存在。可用工具：[列出 tools]。请重新选择。"。最多重试 2 次 |
| `args` 与 schema 不匹配 | 尝试用默认值填充缺失字段；多余的参数忽略；类型不匹配时根据错误信息追加到 messages 让 LLM 修正。最多重试 2 次 |
| 连续 3 步格式错误 | 熔断：终止循环，状态 `error`。向用户展示已产生的部分结果 |

重试不额外消耗 `max_steps` 计数，但正常计入 token 消耗。

### 3.5 Prompt 注入防护

设定集、章节标题等用户数据在拼入 prompt 前做以下处理：

1. 敏感模式过滤：扫描所有用户数据，将包含 `<|SYSTEM|>`、`<|END|>`、`[INST]`、`</SYSTEM>` 等已知分隔标记的行替换为 ASCII 转义序列（如 `<|SYSTEM|>` → `[SYSTEM_ESCAPED]`、`<|END|>` → `[END_ESCAPED]`）。不使用不可见 Unicode 字符（LLM tokenizer 可能意外吞掉或乱码）
2. Agent Tool handler 中对用户输入做校验：`lookup_settings` 的关键词参数限制在 100 字符内，拒绝包含 JSON 结构的内容
3. Blackboard 组装上下文时，用户数据始终包裹在明确的 XML 标签内，例如 `<user_setting key="...">...</user_setting>`，即便是恶意的用户输入也无法逃逸标签

### 3.6 确认请求与超时机制

当循环内触发 `confirm_before=True` 的 Tool 且干预阈值要求暂停时：

```
1. Orchestrator 生成 confirm_id，暂停 Agent 循环
2. 通过 SSE 推送 confirm_request 事件给前端
3. 前端显示确认按钮，启动客户端倒计时（默认 5 分钟）
4. 三种结局：
   ├── 用户点击"批准"/"拒绝"/"修改" → 前端回 POST /chat/confirm
   ├── 倒计时到期 → 前端自动发送 POST /chat/confirm?auto=timeout
   └── SSE 断连超过 30s → 前端重连后轮询 GET /tasks/{id}/pending-actions
5. 服务端收到响应后恢复 Agent 循环继续执行
```

**SSE 断连恢复**：
- 每次 SSE 事件携带 `&sequence=N` 递增序号
- 前端维护 `last_received_seq`，收到事件时若 `seq <= last_received_seq` 则丢弃（客户端去重）
- 前端断连重连时发送 `GET /chat/stream?task_id={id}&resume_from={last_received_seq}`，服务端从该序号起重放未送达的事件
- 如果 task 已不在内存（服务重启），从 `agent_messages` 表重建消息历史返回
- `sequence` 全局严格递增，不重用

**`WAITING_USER` 超时处理**：
- 超时默认行为：`confirm_before` Tool 自动降级——写入模式为 `suggest` 的只做建议不写入，`draft` 的写入草稿但不发布
- 用户可在自主级别配置中修改默认超时行为：`timeout_action = "skip" | "abort_task" | "downgrade_and_continue"`
- 任务不可在 `WAITING_USER` 状态停留超过 24 小时，超时自动取消（`status='cancelled'`）

### 3.7 自主级别对循环的控制

| 配置维度 | 在循环中的作用 |
|----------|---------------|
| 里程碑粒度 | 决定 Orchestrator 分配多少任务后才汇报 |
| 干预阈值 | 决定 `confirm_before=True` 的 Tool 是否真的暂停请求确认 |
| 写入模式 | 决定 Tool 执行时调 `create()` / `save_draft()` / 只返回建议文本 |

---

## 4. Blackboard 与上下文压缩

### 4.1 三层存储结构

```
1. 持久层（始终在上下文中，压缩后保留摘要）
   ├── 项目元信息（genre、状态、目标字数）
   ├── 当前章节大纲
   ├── 相关设定摘要（权重标记，按需展开）
   └── 文风要求

2. 工作层（最近 N 步的完整信息，默认 N=5）
   ├── 最近 tool 调用及结果原文
   ├── 当前正在写的正文
   └── 最近一次审阅的具体发现

3. 归档层（压缩后以摘要形式注入）
   ├── 之前步骤的压缩摘要（≤ 200 字/步）
   ├── 已完成的审阅结论（只保留严重度和维度）
   └── 设定变更历史（只保留最终决定）
```

### 4.2 压缩触发

当 messages 估算 token 数 > 阈值（默认 30K）：
1. 取工作层外的旧 steps
2. 调用轻量 LLM 压缩为每条 ≤ 200 字的摘要
3. 替换 messages 中对应的旧内容为一条 system 消息："[上下文摘要] 步骤 1-5: 已查询火系魔法和时间循环设定，已完成第3章写作(2450字)，审阅发现1个设定矛盾(已修正)，更新了'魔法风暴系'条目的使用频率标记"
4. 重新计算，如仍超则扩大压缩范围

**压缩失败 Fallback**：若压缩 LLM 调用失败（超时、错误、返回不合理摘要）：
- 丢弃最旧的 1/3 上下文（截断），保留最近的内容
- 记录 WARN 级别日志（截断量、原因）
- 截断后若仍超过阈值，重复截断直到低于阈值或只剩工作层
- 截断优于卡死——部分上下文丢失比 Agent 循环失败好

**Token 估算方法**：
- **首选**（Claude 模型）：调用 Anthropic 的 `messages.count_tokens` API（免费，不消耗推理配额）。对每次 Agent LLM 调用前的 messages 做精确计数
- **降级**（非 Claude 模型或 API 不可用）：tiktoken `o200k_base` + 20% 裕量。基于 `len(text) * 0.4`（中文）和 `len(text) / 3.5`（英文）取加权平均后乘以 1.2 作为安全边界
- 压缩阈值 30K 指触发线——实际可到达的上下文通常比阈值低约 20%，因为触发压缩时已预留裕量

**Token 预算控制**：
- `agent_tasks.total_tokens` 记录每次 Agent 运行的实际消耗（含压缩调用）
- 每个 Agent 配置有 `token_budget`（默认 100K），超出后强制终止并保留部分结果
- 用户可在项目配置中设置单次任务预算上限

### 4.3 Blackboard 核心接口

```python
class Blackboard:
    project_id: str
    task: Task
    orchestrator_state: str      # 状态机当前所处 state
    current_chapter_id: str | None
    current_draft: str | None
    last_review: ReviewResult | None
    pending_setting_changes: list[SettingChange]
    agent_steps: list[StepRecord]
    rewrite_round: int = 0       # 当前章节重写轮次
    autonomy_config: AutonomyConfig
    events: asyncio.Queue        # SSE 事件流（不序列化）

    # Token 追踪
    cumulative_tokens: int
    compression_tokens: int
    token_budget: int

    def get_context_for(self, agent_type: str) -> str: ...
    def write_draft(self, content: str) -> None: ...
    def record_step(self, step: StepRecord) -> None: ...
    def emit_event(self, event: dict) -> None: ...
    def to_snapshot(self) -> dict: ...     # 序列化（不含 Queue）
    @classmethod
    def from_snapshot(cls, data: dict) -> 'Blackboard': ...  # 反序列化
```

### 4.4 Blackboard 持久化与任务恢复

**序列化规则**（`to_snapshot()` 生成存入 `agent_tasks.blackboard_snapshot` 的字典）：

| 字段 | 序列化 | 说明 |
|------|--------|------|
| `project_id` | 直接 | |
| `task` | 直接 | dict 表示 |
| `orchestrator_state` | 直接 | 状态机当前 state |
| `current_chapter_id` | 直接 | |
| `current_draft` | 直接 | |
| `last_review` | `__dict__` | ReviewResult 转 dict |
| `pending_setting_changes` | 列表 `__dict__` | |
| `agent_steps` | 列表 `__dict__` | 含 `AgentStep` 全部字段 |
| `rewrite_round` | 直接 | |
| `autonomy_config` | `__dict__` | |
| `cumulative_tokens` | 直接 | |
| `compression_tokens` | 直接 | |
| `token_budget` | 直接 | |
| `context_summaries` | 直接 | |
| `events` | **不序列化** | 重连时从 `agent_messages` 表重建 |

**快照保存时机与原子性**：

- **完整快照**：每个 Agent 运行**完成后**保存一次完整快照（包含全部 Blackboard 可序列化字段）
- **中间快照**：Agent 运行过程中，每 **5 个 step** 保存一次增量快照（轻量事务）。中间快照只包含 `agent_steps`、`cumulative_tokens`、`last_committed_step`，不更新 `orchestrator_state`。`agent_tasks` 新增字段 `last_committed_step INTEGER DEFAULT 0`
- **原子性保证**：每次快照写入采用单次数据库事务，完整快照同步更新 `blackboard_snapshot` + `orchestrator_state` + `status`；中间快照只更新 `blackboard_snapshot` + `total_steps` + `total_tokens` + `last_committed_step`

  ```sql
  -- 完整快照（Agent 完成后）
  UPDATE agent_tasks
  SET blackboard_snapshot = :snapshot,
      orchestrator_state = :new_state,
      status = :new_status,
      total_steps = :steps,
      total_tokens = :tokens,
      last_committed_step = :steps
  WHERE id = :task_id AND status = 'running';

  -- 中间快照（每 5 steps）
  UPDATE agent_tasks
  SET blackboard_snapshot = :snapshot,
      total_steps = :steps,
      total_tokens = :tokens,
      last_committed_step = :steps
  WHERE id = :task_id AND status = 'running';
  ```
  条件 `AND status = 'running'` 作为乐观锁——如果快照写到一半时状态已被外部修改（如用户取消了任务），更新不会生效

- **恢复时的重放范围**：从 `last_committed_step` 之后重放（而非从整个 Agent 起始点重跑）。恢复流程读取 `last_committed_step`，只重跑尚未持久化的 Tool 调用（`step_number > last_committed_step`）。配合 Tool 幂等性，重跑安全
- **任务完成后的快照**：任务 `DONE` 时写入最终快照，状态变为 `completed`。此后的快照不再变更

**恢复流程**：
1. 服务启动时扫描 `agent_tasks WHERE status IN ('running', 'waiting_user')`，加载 `blackboard_snapshot`
2. `from_snapshot()` 重建 Blackboard 实例（`events` 创建新的空 Queue）
3. Orchestrator 从 `orchestrator_state` 恢复状态机
4. 如果恢复的是 `WAITING_USER` 状态 → 检查等待是否超时，超时按超时策略处理
5. 如果恢复的是 `WRITING` / `REVIEWING` / `FIXING_SETTINGS` 状态 → 从上一个 Agent 的起始点重新运行

**恢复的安全性前提——Tool 幂等性**：
- 恢复后重跑 Agent 意味着同一 Agent 可能执行同样的 Tool 调用两次（第一次已写入数据库，第二次重跑再次写入）
- 因此**所有写入型 Tool 的 handler 必须是幂等的**：`write_chapter` 使用 `outline_id` 作为去重键覆盖而非新增行；`propose_setting` 使用 `key` 字段做 upsert；`submit_review` 使用 `(chapter_id, sequence)` 做 upsert（记录每次审阅调用，不覆盖之前的审阅）
- `Tool.idempotent` 字段默认为 `True`。非幂等 Tool（例如可能需要对每章生成多个审阅报告的批量场景）必须显式声明 `idempotent=False`，且 Orchestrator 恢复时不重跑包含非幂等 Tool 的 Agent，转为 `WAITING_USER` 让用户决定
- 读取型 Tool（如 `lookup_settings`）天然幂等，不受影响

---

## 5. 三个 Agent 的 Tool 定义

### 5.1 Writer Agent

| Tool | 描述 | 写入模式控制 |
|------|------|-------------|
| `lookup_settings` | 按关键词查相关设定 | 只读 |
| `get_outline_context` | 获取当前章节的上级大纲、同级章节摘要 | 只读 |
| `get_recent_chapters` | 获取前 N 章正文，默认前 3 章 | 只读 |
| `get_style_guide` | 获取项目配置的目标文风特征 | 只读 |
| `write_chapter` | 生成/重写章节正文 | draft / direct |
| `update_outline_status` | 将完成的大纲节点标记为 done | draft / direct |

**草稿生命周期**：
- `write_chapter` 在写入模式为 `draft` 时：新建或**覆盖**同一 `outline_id` 对应的已有草稿（一章节一草稿，防止累积）
- **版本保留**：被覆盖的旧草稿内容以 `message_type='draft_version'` 存入 `agent_messages` 表（`metadata={chapter_id, version, word_count, timestamp}`），支持版本回溯对比。用户可在 Agent 对话界面看到章节的历史版本列表
- 重写轮次内：每次重写产生新的 `chapter` 行，旧版本保留在数据库但标记 `status='superseded'`。审阅通过后旧版本可清理
- `generated_by` 字段格式：`'agent:{task_id}:{step_number}'`，可追溯到具体的生成步骤
- 草稿在手动工坊中可见可编辑，用户发布时 `status` 从 `draft` 变为 `published`

### 5.2 Reviewer Agent

| Tool | 描述 | 写入模式控制 |
|------|------|-------------|
| `get_chapter_content` | 获取指定章节完整正文 | 只读 |
| `get_style_guide` | 获取文风配置（与 Writer 共享） | 只读 |
| `get_recent_chapters` | 获取前文章节作对比 | 只读 |
| `check_setting_consistency` | 逐条对照设定集检查章节正文 | 只读 |
| `check_style_consistency` | 检查文风是否偏离目标 | 只读 |
| `check_logic_structure` | 检查情节逻辑和节奏 | 只读 |
| `submit_review` | 提交审阅报告到 reviews 表 | draft / direct |

### 5.3 Setting Manager Agent

| Tool | 描述 | 写入模式控制 |
|------|------|-------------|
| `search_settings` | 按分类/关键词搜索已有设定 | 只读 |
| `get_setting_detail` | 获取单个设定的完整信息（含关系图谱） | 只读 |
| `get_related_settings` | 沿关系链获取关联设定 | 只读 |
| `propose_setting` | 提案创建/更新设定 | suggest / draft / direct |
| `detect_conflicts` | 检测新旧设定之间是否存在矛盾 | 只读 |
| `resolve_conflict` | 对检测到的矛盾给出修正方案 | suggest / draft / direct |
| `link_settings` | 创建/修改设定之间的关联关系 | draft / direct |

**批量设定检测的性能考虑**：当设定条目超过 1000 条时，`detect_conflicts` 逐条对照可能超时或 token 爆炸。处理策略：按分类分批检测，每批最多 20 条；先按 `weight >= 4` 过滤高权重设定后再全量检测；`check_setting_consistency` 同理，只将当前章节可能涉及的相关设定（按关键词/TF-IDF）注入 prompt，而非全量注入。

### 5.4 共用 Tool

| Tool | 描述 |
|------|------|
| `search_any` | 跨实体搜索（复用现有 SearchService） |
| `report_progress` | Agent 向 Blackboard 写入进度摘要，用户可见 |

### 5.5 审阅评分定义

`submit_review` 产出的 `ReviewResult` 结构：

```python
class ReviewResult:
    overall_score: float              # 1.0 ~ 5.0，加权平均
    setting_consistency_score: float  # 设定一致性
    style_consistency_score: float    # 文风一致性
    logic_structure_score: float      # 逻辑与结构
    language_polish_score: float      # 语言润色
    findings: list[ReviewFinding]     # 发现的问题
    summary: str                      # 综合评语
```

| 分数区间 | 行为 |
|----------|------|
| >= 3.5 | 通过，进入下一阶段 |
| 2.5 ~ 3.4 | 可接受但有改进空间，提示用户决定是否重写 |
| < 2.5 | 不合格，触发重写（`rewrite_round < max_rewrite_rounds` 时） |
| < 2.5 且 `rewrite_round >= max_rewrite_rounds` | 不再重写，降格保存为 draft，标记 `WAITING_USER` 让用户决策 |

---

## 6. Orchestrator（主编编排器）

Orchestrator 是规则引擎（非 LLM Agent），根据用户任务和 Blackboard 状态决定下一个调哪个 Agent。

### 6.1 调度策略

Orchestrator 采用**单队列串行调度**——同一时间只有一个 Agent 在运行。不存在并行 Agent，因此 Blackboard 不需要锁。

**项目级并发控制**：同一项目同时最多有 1 个 `running` 或 `waiting_user` 状态的 `agent_tasks`。Router 在创建新任务前检查：

```sql
-- 原子检测，约束保证不会出现两个活跃任务
SELECT COUNT(*) FROM agent_tasks
WHERE project_id = :pid AND status IN ('running', 'waiting_user')
```

若已有活跃任务，返回 `409 Conflict` 并提示"该项目已有 Agent 任务进行中，请等待完成或取消当前任务"。此约束在应用层实现（SQLite 不支持唯一索引上的条件表达式），配合 `status` 字段的 CHECK 约束使用。

三个 Agent 之间没有直接的 Agent-to-Agent 通信。Writer 产出写入 Blackboard → Orchestrator 读取结果 → Orchestrator 决定是否调 Reviewer → Reviewer 产出写入 Blackboard → Orchestrator 读取结果 → 决定是否调 Setting Manager。

**`GATHERING_CONTEXT` 状态说明**：状态机转换到 `GATHERING_CONTEXT` 时，Orchestrator 执行一次同步的上下文收集操作（非 LLM 调用）——从数据库读取项目元信息、相关设定、大纲上下文、文风配置，组装为 Blackboard 持久层数据。此状态不产生独立的 Agent 运行，不消耗 token。完成后自动进入 `WRITING`。在 SSE 事件流中，此状态仅产生一条 `orchestrator_thought` 事件（如"正在收集设定和大纲上下文..."），无 `agent_start` 事件。若数据库读取失败（网络中断、数据损坏），状态退至 `IDLE`，任务标记 `failed` 并将错误信息推送给用户。

### 6.2 状态机

```
IDLE → GATHERING_CONTEXT → WRITING → REVIEWING
     → FIXING_SETTINGS → REWRITING → DONE
     → WAITING_USER → CANCELLED

Transitions:
  GATHERING_CONTEXT → WRITING          (上下文组装完成)
  WRITING → REVIEWING                  (writer finish)
  REVIEWING → FIXING_SETTINGS           (审阅发现设定问题)
  REVIEWING → REWRITING                (score < 2.5 且 rewrite_round < max_rewrite_rounds)
  FIXING_SETTINGS → REWRITING          (设定修复完成，需要重写)
  REVIEWING → DONE                     (score >= 3.5 且无设定问题)
  REVIEWING → WAITING_USER             (confirm_before Tool 触发，或 score 介于 2.5-3.4)
  FIXING_SETTINGS → WAITING_USER       (propose_setting 触发确认请求)
  WRITING → WAITING_USER               (write_chapter confirm_before 触发)
  WAITING_USER → WRITING / REVIEWING / FIXING_SETTINGS  (用户确认后恢复)
  WAITING_USER → CANCELLED             (超时取消)
  DONE → WRITING                       (里程碑未到，继续下一章)
  DONE → IDLE                          (任务完成)
  任意 → IDLE                          (错误 / 预算超限)
```

### 6.3 循环守卫

| 守卫 | 配置项 | 默认值 | 超限行为 |
|------|--------|--------|---------|
| 单章最大重写轮次 | `max_rewrite_rounds` | 3 | 降格保存 draft，`WAITING_USER` |
| 单次任务最大 Agent 执行次数 | `max_agent_executions` | 30 | 强制完成，汇报已产出内容 |

`max_agent_executions` 计算公式参考：章节数 × 平均重写轮次 × （Writer + Reviewer + Setting Manager Agent 各 1 次）。例如 5 章 × 2 轮 × 3 = 30，覆盖典型场景。超限时强制 `DONE`，保留已产出内容。
| 单次任务 token 预算 | `token_budget` | 100,000 | 终止并保留部分结果 |
| WAITING_USER 最大等待 | `confirm_timeout_s` | 300s (5 min) | 按 `timeout_action` 处理 |
| 任务最大存活时间 | `max_task_age_hours` | 24 | 自动取消 |

### 6.4 执行流程示例

```
用户："写第3章，约3000字"
  → Orchestrator 读 Blackboard → 获取自主级别
  → 组装任务单 { agent: "writer", input: {...}, autonomy: {...} }
  → 启动 Writer Agent（单队列运行）
  → Writer 完成 → Orchestrator 读结果
  → 有正文产出 → 调 Reviewer Agent
  → 审阅 score=4.0 无设定问题 → DONE
  → 里程碑未到（还需写第4章）→ 继续 WRITING
  → 全部通过 → 里程碑触发 → 向用户汇报
```

---

## 7. Agent 对话界面

### 7.1 页面路由

`/project/{id}/agent`，从项目工作台功能卡片区进入。

### 7.2 布局

左栏（对话区）：用户消息 + 主编思维 + Agent Tool 调用卡片 + Agent 产出卡片 + 确认请求按钮 + 输入框

右栏（任务面板）：当前状态、进度、自主级别、最近产出链接、手动工坊捷径

### 7.3 消息类型

| 类型 | 呈现方式 | 来源 |
|------|---------|------|
| 用户消息 | 普通聊天气泡 | 用户输入 |
| 主编思维 | 小字灰色文本，折叠显示 | Orchestrator 状态转换 |
| Agent 工具调用 | 可展开卡片：工具名 + 参数 + 结果摘要 | Agent Tool handler |
| Agent 产出 | 醒目卡片：章节/审阅/设定变更预览 | Agent finish |
| 确认请求 | 高亮按钮："批准" / "拒绝" / "修改" | 干预阈值触发 |
| 待应用建议 | 醒目卡片 + "应用" / "忽略" / "查看详情" 按钮 | suggest 模式下写入型 Tool 产出 |

**`pending_suggestion` 与 `confirm_request` 的区别**：
- `confirm_request`：暂停 Agent 循环等待用户决策（阻断式），回复后 Agent 继续执行
- `pending_suggestion`：不暂停循环，Agent 继续执行，但建议内容保存在 `agent_messages.metadata` 中，用户可以稍后回来批量查看和应用。Agent 产出卡片底部附带"此建议尚未写入，点击应用生效"的提示

**非阻断模式的已知 trade-off**：`pending_suggestion` 不阻断 Agent 意味着 Setting Manager 可能在用户审批前就提议了新设定，而 Writer 的后续章节可能已经基于这个"悬空"建议开始写作。如果用户最终拒绝该建议，已写的内容可能包含了基于被拒设定的情节。这是流畅体验与数据一致性之间的权衡——非阻断避免了频繁的等待确认，代价是偶尔需要回滚。

**缓解措施（设定依赖追踪）**：
- Writer Agent 的 `write_chapter` 在生成过程中记录引用了哪些设定（含 `setting_id` 和是否为 `pending_suggestion`）。该信息存入 `chapters.metadata` JSON 字段或 `agent_messages.metadata`
- 用户拒绝某个 `pending_suggestion` 后，系统自动查询所有标记了该建议的章节，将其 `status` 置为 `stale`，界面上显示 ⚠ "此章节依赖的设定已被修改，可能需要重写"
- `task_complete` 事件携带 `suggestions` 数组及每个建议被哪些章节引用，方便用户批量审核
- 被拒建议的内容保留在 `agent_messages` 中供参考，不会丢失

### 7.4 SSE 事件流

```
event: orchestrator_thought   → {"text": "...", "step": 1, "sequence": 1}
event: agent_start            → {"agent": "writer", "task": "写第3章", "sequence": 2}
event: tool_call              → {"agent": "writer", "tool": "lookup_settings", "args": {...}, "sequence": 3}
event: tool_result            → {"agent": "writer", "tool": "lookup_settings", "result": "...", "summary": "...", "sequence": 4}
event: agent_output           → {"agent": "writer", "type": "chapter_draft", "chapter_id": "...", "preview": "...", "sequence": 5}
event: pending_suggestion     → {"id": "sug-1", "agent": "settings_mgr", "tool": "propose_setting", "summary": "建议新增设定：时间裂隙副作用", "detail": {...}, "sequence": 6}
event: confirm_request        → {"id": "confirm-1", "agent": "settings_mgr", "action": "propose_setting", "sequence": 7}
event: task_complete          → {"task_id": "t1", "summary": "第3章完成", "outputs": [...], "suggestions": [...], "sequence": 8}
event: error                  → {"agent": "writer", "message": "LLM 调用失败，正在重试...", "sequence": 9}
```

### 7.5 与现有页面衔接

Agent 产出均提供"在 xx 页打开"链接，用户可随时跳转到手动编辑页面继续修改。现有手动页面不做任何改动。

---

## 8. 数据模型变更

### 8.1 新增表

**`agent_tasks`**：

```sql
CREATE TABLE agent_tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    task_type TEXT NOT NULL CHECK (task_type IN (
        'write_chapter', 'write_volume', 'write_act',
        'review_chapter', 'review_all',
        'clean_settings', 'general'
    )),
    target_desc TEXT,
    autonomy_config JSON NOT NULL,
    orchestrator_state TEXT,              -- 当前状态机 state，用于恢复
    blackboard_snapshot JSON,             -- 可恢复的 Blackboard 序列化状态
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN (
        'running', 'paused', 'waiting_user', 'completed', 'failed', 'cancelled'
    )),
    total_steps INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    last_committed_step INTEGER DEFAULT 0,  -- 最近一次持久化的 step 序号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
CREATE INDEX agent_tasks_project ON agent_tasks(project_id);
CREATE INDEX agent_tasks_created ON agent_tasks(created_at DESC);
CREATE INDEX agent_tasks_status ON agent_tasks(status);  -- 启动恢复扫描用
```

**`orchestrator_state` 与 `status` 的映射**（由 Orchestrator 在状态转换时同步写入，单次事务保证一致）：

| `orchestrator_state` | `status` | 说明 |
|----------------------|----------|------|
| `GATHERING_CONTEXT` | `running` | 上下文准备中 |
| `WRITING` | `running` | Writer Agent 执行中 |
| `REVIEWING` | `running` | Reviewer Agent 执行中 |
| `FIXING_SETTINGS` | `running` | Setting Mgr Agent 执行中 |
| `REWRITING` | `running` | 重写轮次中 |
| `WAITING_USER` | `waiting_user` | 等待用户决策 |
| `DONE` | `completed` | 任务正常完成 |
| `IDLE` | `completed` | 等同于完成 |
| `CANCELLED` | `cancelled` | 已取消 |
| (任何 state) | `paused` | 用户手动暂停（不常用） |
| (任何 state) | `failed` | 出错终止 |

`running` 是唯一覆盖多个 `orchestrator_state` 的 status 值——因为从外部视角看，Agent 在执行中就是 running，内部的 WRITING/REVIEWING 是状态机细节。

**`agent_messages`**：

```sql
CREATE TABLE agent_messages (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES agent_tasks(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN (
        'user', 'orchestrator', 'writer', 'reviewer', 'settings_mgr', 'system'
    )),
    content TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text' CHECK (message_type IN (
        'text', 'tool_call', 'tool_result', 'agent_output',
        'confirm_request', 'confirm_response', 'pending_suggestion', 'error'
    )),
    metadata JSON,
    sequence INTEGER NOT NULL DEFAULT 0,  -- 全局递增序号，用于 SSE 断连恢复
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX agent_messages_task ON agent_messages(task_id);
CREATE INDEX agent_messages_sequence ON agent_messages(task_id, sequence);
```

### 8.2 已有表扩展

```sql
-- settings 表：Agent 来源追踪拆分为两个字段
ALTER TABLE settings ADD COLUMN proposed_by_type TEXT CHECK (proposed_by_type IN ('user', 'agent'));
ALTER TABLE settings ADD COLUMN proposed_by_task_id TEXT REFERENCES agent_tasks(id);
ALTER TABLE settings ADD COLUMN approved_at TIMESTAMP;
ALTER TABLE settings ADD COLUMN change_summary TEXT;

-- chapters 表
ALTER TABLE chapters ADD COLUMN generated_by_type TEXT CHECK (generated_by_type IN ('user', 'agent'));
ALTER TABLE chapters ADD COLUMN generated_by_task_id TEXT REFERENCES agent_tasks(id);
ALTER TABLE chapters ADD COLUMN generation_prompt TEXT;
ALTER TABLE chapters ADD COLUMN status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'superseded'));

-- reviews 表
ALTER TABLE reviews ADD COLUMN triggered_by_type TEXT CHECK (triggered_by_type IN ('user', 'agent'));
ALTER TABLE reviews ADD COLUMN triggered_by_task_id TEXT REFERENCES agent_tasks(id);
```

`chapters.status` 已有字段，将默认值从 `'draft'` 改为 `'draft'`（不变），增加 `'superseded'` 合法值。

**SQLite CHECK 约束迁移提示**：SQLite 不支持 `ALTER TABLE ... ALTER COLUMN ... ADD CONSTRAINT`。最终选择 **路径 A**——在 Python 模型层用 `@validates` 或 Pydantic schema 做应用层校验，不在 SQLite 层加 CHECK 约束。原因：SQLite 在生产环境重建表风险高，应用层校验足以保证数据一致性。对于 SQLite 原生支持的 CHECK（新表、新字段），在 CREATE TABLE 时写入。

所有新增字段均为 nullable，不影响现有手动工作流。查询 Agent 产出的方式：

```sql
-- 查找某个 task 生成的所有章节
SELECT * FROM chapters WHERE generated_by_type='agent' AND generated_by_task_id='{task_id}';
```

---

## 9. 自主级别配置

三个维度在配置页面独立设置，存储于 `app_config` 表。

### 9.1 里程碑粒度

| 级别 | 行为 |
|------|------|
| 章级 (`chapter`) | Agent 写完一章后暂停汇报 |
| 卷级 (`volume`) | Agent 写完一卷的所有章节后才汇报 |
| 幕级 (`act`) | Agent 完成用户指定的完整目标后汇报 |

### 9.2 干预阈值

干预阈值控制的是 **Tool 执行后**的行为——`Tool.confirm_before` 标注哪些 Tool 属于"重大决策"，干预阈值决定这些决策是否真的触发暂停。当 `confirm_before=True` 的 Tool 执行完毕后，Orchestrator 检查其返回结果：

| 级别 | 行为 |
|------|------|
| 每决策确认 (`all`) | 所有 `confirm_before=True` 的 Tool 执行后都暂停请求确认 |
| 仅矛盾时暂停 (`conflict_only`) | `confirm_before=True` 的 Tool 执行后检查结果：若包含冲突发现或 `overall_score < 2.5`，则插入 `confirm_request` 暂停；否则自动继续 |
| 从不暂停 (`never`) | 忽略 `confirm_before` 标记，所有 Tool 执行后自动继续 |

**干预条件定义**（`conflict_only` 模式下检查）：

```python
class InterventionConditions:
    setting_conflicts: bool = True      # detect_conflicts 返回非空列表
    low_score: float = 2.5              # 审阅 overall_score 低于此阈值
    propose_new_setting: bool = True    # propose_setting 创建新条目（非更新）
    # 可扩展更多条件
```

条件配置存储在 `AutonomyConfig` 中（与 §9.5 的 JSON 默认值一致），可在项目设置中按需调整。设计采用方案 A（工具执行后检查结果决定是否暂停），因为 `confirm_before` 是静态标记，冲突/低分是动态结果——只有工具执行完才能判断。

### 9.3 写入模式

| 级别 | 行为 |
|------|------|
| 只建议不写入 (`suggest`) | Agent 生成建议但不写入数据库，用户手动点击"应用"生效 |
| 写草稿 (`draft`) | Agent 写入 `status='draft'`，用户可编辑后发布 |
| 直接写入 (`direct`) | Agent 直接写入正式数据 (`status='published'`) |

### 9.4 超时行为

| 级别 | 行为 |
|------|------|
| 跳过 (`skip`) | 超时时跳过当前确认步骤，Tool 降级为 suggest |
| 终止任务 (`abort_task`) | 超时时直接取消整个任务 |
| 降级继续 (`downgrade_and_continue`) | 超时时将当前 Tool 的写入模式从 direct 降为 draft，继续执行 |

### 9.5 默认配置

任务创建时深拷贝当前 `AutonomyConfig` 存入 `agent_tasks.autonomy_config`。运行期间只读取任务内部的配置快照，不响应全局配置变更——用户修改设置不影响正在运行的任务。

```json
{
  "milestone_granularity": "chapter",
  "intervention_threshold": "conflict_only",
  "write_mode": "draft",
  "timeout_action": "downgrade_and_continue",
  "max_rewrite_rounds": 3,
  "token_budget": 100000,
  "confirm_timeout_s": 300
}
```

---

## 10. 文件变更清单

### 10.1 新增文件

```
app/agents/
├── __init__.py
├── base.py                  # Agent 基类 + AgentConfig + Tool + AgentStep + 鲁棒性解析
├── orchestrator.py          # 主编编排器（状态机 + 循环守卫）
├── blackboard.py            # 共享状态黑板 + 上下文压缩 + 序列化/反序列化
├── autonomy.py              # 自主级别配置解析
├── tools/
│   ├── __init__.py
│   ├── writing.py           # Writer Agent Tool handlers
│   ├── review.py            # Reviewer Agent Tool handlers
│   ├── setting.py           # Setting Mgr Agent Tool handlers
│   └── shared.py            # 共用 Tool handlers
├── agents/
│   ├── __init__.py
│   ├── writer.py            # Writer Agent 配置
│   ├── reviewer.py          # Reviewer Agent 配置
│   └── settings_mgr.py      # Setting Manager Agent 配置
└── prompts/
    ├── writer_system.txt
    ├── reviewer_system.txt
    └── settings_mgr_system.txt

app/routers/agent.py

app/models/agent_task.py
app/models/agent_message.py

app/templates/agent/
├── index.html
├── _chat.html
├── _sidebar.html
├── _task_card.html
└── _message.html

app/static/js/agent-chat.js

tests/
├── test_agent_base.py       # 含鲁棒性/格式错误测试
├── test_orchestrator.py     # 含循环守卫/状态恢复测试
├── test_blackboard.py       # 含序列化/反序列化测试
├── test_agent_tools.py
└── test_agent_router.py     # 含 SSE 重连/确认超时测试
```

### 10.2 修改文件

| 文件 | 改动 |
|------|------|
| `app/main.py` | 注册 `agent.router` |
| `app/database.py` | `init_db()` 中 import agent_task + agent_message 模型 |
| `app/models/__init__.py` | 导出新增模型 |
| `app/models/setting.py` | 新增 `proposed_by_type`, `proposed_by_task_id`, `approved_at`, `change_summary` |
| `app/models/chapter.py` | 新增 `generated_by_type`, `generated_by_task_id`, `generation_prompt` |
| `app/models/review.py` | 新增 `triggered_by_type`, `triggered_by_task_id` |
| `app/templates/project/detail.html` | 功能卡片区新增「Agent 写作」入口 |
| `app/templates/base.html` | nav 中在项目内页面时增加 Agent 链接 |

### 10.3 不动的文件

- 所有 `app/services/*`
- 所有现有 `app/routers/*`（除 main.py 注册新 router）
- 所有现有 `app/templates/*`（除上述两处加链接）
- `app/llm/*`

---

## 11. 实施阶段

### Phase 1 — Writer Agent MVP（用户可用的最小闭环）
- Agent 基类 + Tool 注册 + LLM 输出鲁棒性处理
- Blackboard 基础版（三层上下文 + 压缩 + 序列化）
- Writer Agent 全部 Tools 实现
- Agent 对话界面基础版（SSE 流式 + 消息渲染）
- Orchestrator 最小状态机（GATHERING_CONTEXT → WRITING → DONE，无审阅无重写）
- 单元测试 + 集成测试
- **可交付**：用户可以在对话界面让 Agent 写一章，看到实时进度，产出可查

### Phase 2 — Reviewer + Setting Manager + 完整编排
- Reviewer Agent 全部 Tools + 审阅评分
- Setting Manager Agent 全部 Tools
- Orchestrator 完整状态机（WRITING → REVIEWING → FIXING_SETTINGS → REWRITING 闭环）
- 循环守卫全部就位
- 集成测试覆盖完整三 Agent 协作
- **可交付**：Agent 写完一章后自动审阅、自动修设定、自动重写不合格产出

### Phase 3 — 渐进式自主 + 可靠性
- 三个维度自主级别配置 UI 和后端
- 确认请求 / 暂停 / 恢复 / 超时处理
- SSE 断连恢复机制
- 任务恢复（从 blackboard_snapshot 重建）
- Prompt 注入防护
- 历史任务查看与重跑
- Token 预算统计与展示
- 手工验证全部流程
- **可交付**：用户可以调节自主级别，Agent 出错时有明确的降级和恢复路径

### Phase 4 — 打磨
- Prompt 版本管理与快照测试
- LLM 流式 `thinking_chunk` 可选增强
- 性能优化（压缩策略调优、tool 调用合并）
- 边界情况打磨（空项目、超大设定集、极限章节数）
- 监控埋点：Agent 循环关键路径（tool 调用耗时、token 消耗、压缩频率、重试次数、错误码分布）——输出结构化日志供生产排查
- **可交付**：生产可用级别

---

## 12. 测试策略

### 12.1 单元测试

- Agent 基类：tool-calling 循环 mock LLM 测试，含格式错误/幻觉工具/连续失败熔断
- Blackboard：上下文压缩逻辑、三层存储正确性、序列化/反序列化往返
- Orchestrator：状态机转换正确性、循环守卫超限行为、状态恢复
- Tool handlers：每个 Tool 的读写行为

### 12.2 集成测试

- Agent Router：SSE 事件流格式、`sequence` 递增、`resume_from` 重放
- 端到端：单章写作完整流程（模拟 LLM 响应）
- 端到端：审阅低分触发重写循环（含 `max_rewrite_rounds` 超限测试）
- 自主级别切换：三个维度的行为差异验证
- 确认超时：`WAITING_USER` → 超时降级 → 继续执行
- **崩溃恢复模拟**：启动任务 → 写入中间快照 → 杀死服务进程 → 重启服务 → 断言任务从 `last_committed_step` 恢复并正确完成

### 12.3 手工验证

- [ ] Agent 对话界面在项目内页面可进入
- [ ] 写一章完整流程无报错（设定查询 → 写作 → 审阅 → 设定更新）
- [ ] 审阅触发设定变更后手动到设定页查看数据正确
- [ ] 三种写入模式下产出的数据状态正确（suggest/draft/direct）
- [ ] 自主级别切换后行为符合预期
- [ ] SSE 断连后重连能恢复事件流
- [ ] 服务重启后未完成任务能正确恢复或取消
- [ ] 现有手动页面功能不受影响

### 12.4 Prompt 版本管理

- `prompts/*.txt` 文件在 git 中管理，变更可追溯
- 每个 prompt 文件附带一个 JSON 快照文件 `prompts/*.golden.json`，记录最后一个该 prompt 产出的已知正确输出
- CI 中跑 golden file 对比：用相同的 mock 输入跑 prompt，对比输出与 golden file，偏差超过阈值则告警
- 可选：引入 model-graded eval——用另一个 LLM 作为评判者，对比新旧 prompt 对同一写作任务的质量评分

---

## 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-11 | 初始设计 |
| v1.1 | 2026-06-11 | 第一轮审阅修正：循环守卫、LLM 鲁棒性、确认超时、SSE 断连、Token 预算、审阅评分定义、草稿生命周期、DB schema 严格性、prompt 注入防护、Phase 重排、prompt 版本管理 |
| v1.2 | 2026-06-11 | 第二轮审阅修正：token 估算改用 Claude count_tokens API + 裕量；Tool 增加 idempotent 字段和幂等性要求；suggest 模式增加 pending_suggestion 消息类型和 SSE 事件；orchestrator_state 与 status 映射表 + 同步写入规则；快照保存时机和原子性事务明确；chapters.status CHECK 约束 SQLite 迁移路径说明 |
| v1.3 | 2026-06-11 | 第三轮审阅修正：修复 agent_tasks SQL 被映射表格截断的问题；agent_messages.message_type CHECK 约束补上 pending_suggestion；补充 GATHERING_CONTEXT 状态实现说明；文档化 suggest 非阻断模式 trade-off 及缓解措施 |
| v1.4 | 2026-06-11 | 第四轮审阅修正（20 条）：并发控制（项目级锁 + 409）；审阅幂等键改为 (chapter_id, sequence)；干预阈值改为后执行语义 + intervention_conditions；中间快照 + last_committed_step；SSE 去重 + sequence 严格递增；GATHERING_CONTEXT 失败处理；suggest 设定依赖追踪 + stale 标记；压缩 Fallback（截断策略）；LLM 流式 thinking_chunk 规划；错误分类 + 重试策略映射表；监控埋点；prompt 注入 ASCII 转义；agent_messages CASCADE；批量设定分批检测；配置快照深拷贝；max_agent_executions 重命名 + 上调配额 30；CHECK 约束选择路径 A；崩溃恢复集成测试；agent_tasks 补 last_committed_step；章节版本支持（draft_version） |
