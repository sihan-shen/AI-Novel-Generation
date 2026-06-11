# Agent 化重构设计文档

> 版本：v1.0
> 日期：2026-06-11
> 状态：设计完成，待实现

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
│   + settings 表增加 proposed_by / approved_at 字段       │
│   + chapters 表增加 generated_by / generation_prompt     │
│   + reviews 表增加 triggered_by 字段                     │
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

class Tool:
    name: str
    description: str            # 写入 LLM prompt
    parameters: dict            # JSON Schema 参数定义
    handler: Callable           # 实际执行的 Python 函数
    confirm_before: bool = False

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
```

### 3.3 循环执行逻辑

1. 组装 messages：system prompt + Blackboard 上下文 + 对话历史
2. 调用 LLM，要求输出 JSON：`{"thought": "...", "tool": "tool_name", "args": {...}}` 或 `{"action": "finish", "summary": "..."}`
3. 如果 `finish` → 退出循环，返回结果
4. 如果 `tool` → 检查 `confirm_before` 和自主级别配置
   - 需要确认 → 暂停循环，通过 SSE 推送给用户，等待响应
   - 不需要确认 → 执行 Tool，结果写回 Blackboard，进入下一步
5. 达到 `max_steps` → 强制要求 LLM 给出 finish

### 3.4 自主级别对循环的控制

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
2. 调轻量 LLM 压缩为每条 ≤ 200 字的摘要
3. 替换 messages 中对应的旧内容为一条 system 消息
4. 重新计算，如仍超则扩大压缩范围

### 4.3 Blackboard 核心接口

```python
class Blackboard:
    project_id: str
    task: Task
    current_draft: str | None
    last_review: ReviewResult | None
    pending_setting_changes: list[SettingChange]
    agent_steps: list[StepRecord]
    autonomy_config: AutonomyConfig
    events: asyncio.Queue          # SSE 事件流

    def get_context_for(self, agent_type: str) -> str: ...
    def write_draft(self, content: str) -> None: ...
    def record_step(self, step: StepRecord) -> None: ...
    def emit_event(self, event: dict) -> None: ...
```

- Blackboard 是内存状态，一次用户任务持有一个实例
- 任务完成后执行轨迹保存到 `agent_tasks` 表
- 服务重启时未完成任务可从数据库恢复

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

### 5.4 共用 Tool

| Tool | 描述 |
|------|------|
| `search_any` | 跨实体搜索（复用现有 SearchService） |
| `report_progress` | Agent 向 Blackboard 写入进度摘要，用户可见 |

---

## 6. Orchestrator（主编编排器）

Orchestrator 是规则引擎（非 LLM Agent），根据用户任务和 Blackboard 状态决定下一个调哪个 Agent。

### 6.1 状态机

```
IDLE → GATHERING_CONTEXT → WRITING → REVIEWING
     → FIXING_SETTINGS → REWRITING → DONE
     → WAITING_USER

Transitions:
  WRITING → REVIEWING         (自动，writer finish)
  REVIEWING → FIXING_SETTINGS  (自动，发现设定问题)
  REVIEWING → WRITING          (自动，score < threshold)
  REVIEWING → DONE             (自动，全部通过)
  REVIEWING → WAITING_USER     (需要确认时暂停)
  DONE → WRITING               (里程碑未到，继续下一章)
  DONE → IDLE                  (任务完成)
```

### 6.2 执行流程示例

```
用户："写第3章，约3000字"
  → Orchestrator 读 Blackboard → 获取自主级别
  → 组装任务单 { agent: "writer", input: {...}, autonomy: {...} }
  → 启动 Writer Agent，实时读 Blackboard
  → Writer 完成 → 读结果
  → 有正文产出 → 调 Reviewer Agent
  → 审阅发现设定问题 → 调 Setting Mgr Agent
  → 审阅分数 < 阈值 → 退回 Writer 重写
  → 全部通过 → 检查里程碑 → 向用户汇报
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

### 7.4 SSE 事件流

```
event: orchestrator_thought   → {"text": "...", "step": 1}
event: agent_start            → {"agent": "writer", "task": "写第3章"}
event: tool_call              → {"agent": "writer", "tool": "lookup_settings", "args": {...}}
event: tool_result            → {"agent": "writer", "tool": "lookup_settings", "result": "...", "summary": "..."}
event: agent_output           → {"agent": "writer", "type": "chapter_draft", "chapter_id": "...", "preview": "..."}
event: confirm_request        → {"id": "confirm-1", "agent": "settings_mgr", "action": "propose_setting", ...}
event: task_complete          → {"task_id": "t1", "summary": "第3章完成", "outputs": [...]}
event: error                  → {"agent": "writer", "message": "LLM 调用失败，正在重试..."}
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
    task_type TEXT NOT NULL,
    target_desc TEXT,
    autonomy_config JSON NOT NULL,
    blackboard_snapshot JSON,
    status TEXT DEFAULT 'running',
    total_steps INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
CREATE INDEX agent_tasks_project ON agent_tasks(project_id);
CREATE INDEX agent_tasks_created ON agent_tasks(created_at DESC);
```

**`agent_messages`**：

```sql
CREATE TABLE agent_messages (
    id TEXT PRIMARY KEY,
    task_id TEXT REFERENCES agent_tasks(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text',
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX agent_messages_task ON agent_messages(task_id);
```

### 8.2 已有表扩展

```sql
-- settings 表
ALTER TABLE settings ADD COLUMN proposed_by TEXT;        -- NULL / 'user' / 'agent:{task_id}'
ALTER TABLE settings ADD COLUMN approved_at TIMESTAMP;
ALTER TABLE settings ADD COLUMN change_summary TEXT;

-- chapters 表
ALTER TABLE chapters ADD COLUMN generated_by TEXT;       -- NULL / 'user' / 'agent:{task_id}'
ALTER TABLE chapters ADD COLUMN generation_prompt TEXT;

-- reviews 表
ALTER TABLE reviews ADD COLUMN triggered_by TEXT;        -- 'user' / 'agent:{task_id}'
```

所有新增字段均为 nullable，不影响现有手动工作流。

---

## 9. 自主级别配置

三个维度在配置页面独立设置，存储于 `app_config` 表：

### 9.1 里程碑粒度

| 级别 | 行为 |
|------|------|
| 章级 | Agent 写完一章后暂停汇报 |
| 卷级 | Agent 写完一卷的所有章节后才汇报 |
| 幕级 | Agent 完成用户指定的完整目标后汇报 |

### 9.2 干预阈值

| 级别 | 行为 |
|------|------|
| 每决策确认 | 所有 `confirm_before=True` 的 Tool 都暂停请求确认 |
| 仅矛盾时暂停 | 仅在发现设定冲突或审阅分数过低时暂停 |
| 从不暂停 | Agent 自行完成全部，仅在完成时汇报 |

### 9.3 写入模式

| 级别 | 行为 |
|------|------|
| 只建议不写入 | Agent 生成建议但不写入数据库，用户手动点击"应用"才生效 |
| 写草稿 | Agent 写入草稿态（status='draft'），用户可编辑后发布 |
| 直接写入 | Agent 直接写入正式数据 |

---

## 10. 文件变更清单

### 10.1 新增文件

```
app/agents/
├── __init__.py
├── base.py                  # Agent 基类 + AgentConfig + Tool + AgentStep
├── orchestrator.py          # 主编编排器（状态机）
├── blackboard.py            # 共享状态黑板 + 上下文压缩
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
├── test_agent_base.py
├── test_orchestrator.py
├── test_blackboard.py
├── test_agent_tools.py
└── test_agent_router.py
```

### 10.2 修改文件

| 文件 | 改动 |
|------|------|
| `app/main.py` | 注册 `agent.router` |
| `app/database.py` | `init_db()` 中 import agent_task + agent_message 模型 |
| `app/models/__init__.py` | 导出新增模型 |
| `app/models/setting.py` | 新增 nullable 字段 |
| `app/models/chapter.py` | 新增 nullable 字段 |
| `app/models/review.py` | 新增 nullable 字段 |
| `app/templates/project/detail.html` | 功能卡片区新增「Agent 写作」入口 |
| `app/templates/base.html` | nav 中增加 Agent 链接 |

### 10.3 不动的文件

- 所有 `app/services/*`
- 所有现有 `app/routers/*`（除 main.py 注册新 router）
- 所有现有 `app/templates/*`（除上述两处加链接）
- `app/llm/*`

---

## 11. 实施阶段建议

### Phase 1 — Agent 基础设施
- Agent 基类 + Tool 注册机制
- Blackboard + 上下文压缩
- 自主级别配置系统
- 单元测试覆盖核心循环和压缩逻辑

### Phase 2 — Writer Agent + 对话界面
- Writer Agent 全部 Tools 实现
- Agent 对话界面（SSE 流式渲染）
- Orchestrator 基础状态机（支持单 Agent 调度）
- 集成测试覆盖单章写作流程

### Phase 3 — Reviewer + Setting Manager Agent
- Reviewer Agent 全部 Tools 实现
- Setting Manager Agent 全部 Tools 实现
- Orchestrator 完整状态机（多 Agent 自动协调）
- 集成测试覆盖完整写作→审阅→设定更新循环

### Phase 4 — 渐进式自主 + 打磨
- 三个维度自主级别完整实现
- 确认请求 / 暂停 / 恢复机制
- 历史任务查看与重跑
- 手工验证全部流程 + 性能优化

---

## 12. 测试策略

### 12.1 单元测试

- Agent 基类：tool-calling 循环 mock LLM 测试
- Blackboard：上下文压缩逻辑、三层存储正确性
- Orchestrator：状态机转换正确性
- Tool handlers：每个 Tool 的读写行为

### 12.2 集成测试

- Agent Router：SSE 事件流格式和顺序
- 端到端：单章写作完整流程（模拟 LLM 响应）
- 自主级别切换：三个维度的行为差异验证

### 12.3 手工验证

- [ ] Agent 对话界面 Cmd+K 可唤起
- [ ] 写一章完整流程无报错
- [ ] 审阅触发设定变更后手动到设定页查看
- [ ] 三种写入模式下产出的数据状态正确
- [ ] 自主级别切换后行为符合预期
- [ ] 现有手动页面功能不受影响
