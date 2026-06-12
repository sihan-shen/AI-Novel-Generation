# Brainstorm Agent Migration Design

## Summary

将现有独立头脑风暴页面（`/brainstorm`）迁移为 Agent Chat 内的 **Brainstorm Conversation Mode**。它使用 Agent 基础设施（SSE、工具、持久化），但本质是一个带特定 system prompt + 工具集的对话模式，而不是 Orchestrator 状态机中的一个 Agent 节点。

## Why Mode, Not Agent

Brainstorm 的职责是创意讨论和灵感拓展，不负责长链工具调用、不负责复杂执行规划。如果每个对话场景都变成一个独立 Agent（CharacterAgent、WorldbuildingAgent、OutlineAgent...），会导致 Agent 碎片化。实际上它们只是 `prompt + tools` 的组合差异。BrainstormSession 封装这个组合及其生命周期。

## Core Concepts

### BrainstormSession

```
BrainstormSession
├── session_id: str
├── project_id: str
├── status: "active" | "completed" | "cancelled" | "timeout"
├── history: list[{role, content, tool_calls?}]
├── pending_saves: list[dict]     # 待确认的灵感，批量确认
├── created_at: datetime
├── last_activity: datetime
├── token_count: int
└── handoff_depth: int            # 防 ping-pong，上限 3
```

- **持久化到 DB**（复用 `AgentTask` + `AgentMessage`，task_type="brainstorm"）
- 进程重启后可恢复
- 多个 timeout session 按 `last_activity` 排序，取最近一个询问恢复

### Single Source of Truth: `active_session`

```python
# Orchestrator / Blackboard
active_session: BrainstormSession | None
```

- `active_session is None` → 正常 Orchestrator 流程
- `active_session is not None` → 消息路由到 Brainstorm Session（bypass orchestrator state machine）
- 不需要在 `OrchestratorState` 中新增 `BRAINSTORMING`。Orchestrator 状态机只处理写作流水线
- 无 state/active_agent 双重真相问题

### Routing

```
User Message
    ↓
active_session?
    ├── Yes → BrainstormSession.handle(message)
    │           ├── /done      → save → active_session = None
    │           ├── /cancel    → discard history, keep confirmed saves → active_session = None
    │           ├── timeout    → save draft → active_session = None
    │           ├── handoff    → save history → active_session = None → re-enter intent detection
    │           └── otherwise  → Brainstorm response → persist to history
    │
    └── No → Orchestrator state == IDLE?
                ├── Yes → Intent Detection
                │           ├── "brainstorm" → create BrainstormSession → handle(message)
                │           └── "writing" / "other" → normal flow
                └── No → continue orchestrator pipeline
```

## Intent Detection

单一 LLM 调用（小模型，低 temperature），只在 `state == IDLE` 且 `active_session is None` 时：

```
用户消息: "{user_message}"

判断意图：
- "brainstorm": 创意帮助、灵感拓展、方案探索、设定讨论、剧情构思。
  隐含表达："不知道怎么写"、"不够精彩"、"有什么推荐"、"还能怎么玩"、
  "卡住了"、"没思路"、"主角职业推荐"、"后面怎么发展"
- "writing": 明确的写作/修改/生成请求
- "other": 以上都不是

返回 JSON: {"intent": "brainstorm|writing|other"}
```

**命令优先级**：`/brainstorm` 直接创建 BrainstormSession，跳过检测。`/brainstorm 写第一章` → 进入 brainstorm 模式（显式命令优先于消息内容）。

## Context Management（防爆炸）

Brainstorm Agent **不预注入**全部项目上下文。它通过工具按需获取：

```python
# Brainstorm Agent 可用的上下文获取工具
- lookup_settings(keywords)     # 按关键词搜索设定
- get_outline_context(node_id)  # 查询特定大纲节点
- search_any(q, type, limit)    # 跨实体搜索
```

启动时只注入最小上下文：

```python
initial_context = {
    "project_meta": {"genre": "...", "status": "..."},
    "brainstorm_history": [...],  # 当前会话轮次
}
```

**brainstorm_history 的滑动窗口**：

- 保留最近 20 轮完整内容
- 超过 20 轮的部分 → 每 10 轮压缩为一条摘要（保留关键决策、分支方案、被否决方向）
- 摘要由 LLM 生成，确保不丢失被否决的方案和分支思路
- `token_count` 追踪总 token，超过 `max_brainstorm_tokens`（默认 50K）时触发压缩

## Handoff（防重复、防循环）

当用户在 Brainstorm 中发写作请求：

1. Brainstorm Agent 收到消息
2. Agent 简洁总结脑暴成果
3. Emit `action: handoff, summary: "..."` 
4. 保存完整 history，`active_session = None`
5. 将 **Agent 的总结**（而非用户原始消息）作为输入传递给写作流程 → 避免消息重复消费
6. 写作流程从总结开始，而非重新处理用户消息

**防 ping-pong**：

```python
handoff_depth: int = 0  # 每次 handoff +1
max_handoff_depth: int = 3  # 超过此值 → 停止流转，请用户明确指令
```

Writer handoff → Brainstorm 同样受此限制。

## Idea 与聊天记录分离

- **对话历史** → 存储为 `AgentTask(type="brainstorm")` + `AgentMessage`（与现有 agent 消息机制一致）
- **灵感产物** → 用户确认的 `save_inspiration` 结果保存为 `Idea(source="brainstorm")`
- 不会出现"嗯、继续、好的"出现在 Idea 搜索中的情况

## save_inspiration：批量确认

- 脑暴过程中，Agent 可以提议保存灵感（emit `save_inspiration` proposal）
- 所有 proposal 累积在 `pending_saves` 列表中
- **不打断用户**：提案只在 Agent 回复末尾展示 "可保存的灵感 (N)"
- 脑暴正常结束时（`/done`）：批量展示所有 pending_saves，用户一次性确认
- `/cancel`：丢弃 pending_saves，但已确认保存的 Idea 保留
- `/timeout`：pending_saves 保留在 draft 中，恢复时可继续确认

## /cancel 语义

- 丢弃 `brainstorm_history`（对话）
- 保留已确认的 `Idea`（曾显式批准的写入）
- 丢弃 `pending_saves`（未确认的）
- session status → "cancelled"

## Lock：覆盖完整 read-check-write

```python
# Per-project lock covers the entire message handling cycle
async with project_lock:
    # read state
    # check intent / route
    # update state
    # run agent
    # persist
```

锁覆盖整个处理周期，消除 check-then-act 竞态。并发请求收到 `{"status": "busy"}`。

## Timeout & 恢复

- 15 分钟无 `last_activity` → timeout
- 保存 BrainstormSession（status="timeout"，完整 history）
- 用户下次进入时：
  - 查询 `status == "timeout"` 的 session，按 `last_activity` 降序
  - 只有 1 个且 < 24 小时 → 自动恢复
  - 多个或 > 24 小时 → 展示列表让用户选择
  - 恢复后 `status → "active"`，`last_activity` 更新

## Observability（实现阶段记录）

追踪指标（为迁移效果评估服务）：
- 意图命中率（brainstorm/writing/other 分布）
- 平均脑暴轮数、中位数、P95
- handoff 次数及成功率
- timeout 率、取消率、恢复率
- per-session token 消耗

## Files

### New
- `app/agents/agents/brainstorm.py` — `build_brainstorm_config()`
- `app/agents/tools/brainstorm.py` — `save_inspiration` (accumulate proposals, batch confirm)
- `app/agents/prompts/brainstorm_system.txt` — system prompt

### Modified
- `app/agents/blackboard.py` — add `BrainstormSession`, `active_session` field
- `app/routers/agent.py` — routing logic, command handling, per-project lock, session recovery
- `app/routers/__init__.py` — 302 redirect for `/brainstorm`

### Deprecated (remove in next version)
- `app/routers/brainstorming.py` → 302 redirect
- `app/templates/brainstorm/`

### Reused
- `AgentTask` + `AgentMessage` for BrainstormSession persistence (task_type="brainstorm")
- Existing tools: `lookup_settings`, `get_outline_context`, `search_any`
