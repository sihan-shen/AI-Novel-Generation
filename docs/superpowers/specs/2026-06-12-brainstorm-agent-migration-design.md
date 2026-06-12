# Brainstorm Agent Migration Design

## Summary

将现有独立头脑风暴页面（`/brainstorm`）迁移为 Agent Chat 内的脑暴模式。不引入新抽象——只是 `AgentTask(task_type="brainstorm")`，复用现有基础设施。

## Architecture

单一控制平面，所有路由经 Orchestrator：

```
User Message → SSE endpoint
    ↓
active_task?
    ├── Yes → 根据 task.type 路由
    │           ├── "write_chapter" → Orchestrator state machine
    │           └── "brainstorm"    → _run_brainstorm(message)
    │
    └── No (IDLE) → Intent Detection
                      ├── "brainstorm" → AgentTask(type="brainstorm") → run
                      └── "writing"   → AgentTask(type="write_chapter") → normal flow
```

**路由依据**：`active_task.type` 是唯一路由键。`OrchestratorState.WAITING_USER` 仅表示 "等待用户输入"，不携带业务语义。无论 writer 等待还是 brainstorm 等待，状态值相同，路由由 `task.type` 决定。

## Brainstorm Task Lifecycle

```
创建 AgentTask(type="brainstorm", status="running")
    ↓
每轮用户消息 → run_agent() → 持久化 AgentMessage → SSE 推送
    ↓
┌─ /done 或前端按钮     → status="completed"
├─ /cancel              → status="cancelled"  
├─ 15min timeout        → status="timeout" (被动检测，但主动通知)
└─ max_steps/max_tokens → status="completed" (带 reached_limit 标记)

↓
→ state = IDLE, active_task = None
```

Agent 无权限主动结束。只允许用户触发结束。

## Routing Rules (Pseudocode)

```python
async def handle_message(project_id, message):
    async with project_lock:  # 仅锁状态决策，不锁 agent 执行
        task = get_active_task(project_id)

        if task is None:
            intent = await detect_intent(message)
            if intent == "brainstorm":
                task = create_task(type="brainstorm")
            elif intent == "writing":
                task = create_task(type="write_chapter")
            else:
                return general_response(message)

    # 锁释放，agent 执行不阻塞其他请求
    if task.type == "brainstorm":
        result = await run_brainstorm(task, message)
        # 状态转换重新加锁
        async with project_lock:
            handle_result(task, result)

# 并发保护：锁覆盖 task 创建、完成、取消等状态转换
# run_agent() 执行期间不持锁
```

## Intent Detection

单一 LLM 调用（小模型，低 temp），仅 IDLE + 无 active_task：

```
用户消息: "{user_message}"

判断意图：
- "brainstorm": 创意帮助、灵感拓展、方案探索、设定讨论。
  隐含表达："还能怎么玩"、"卡住了"、"没思路"、"有什么推荐"、"给我几个方案"
- "writing": 明确的写作/修改/生成请求。边界：即使用户表达困惑
  （"不知道怎么写第一章"），只要提到具体章节/写作动作，归类为 writing
- "other": 以上都不是

返回 JSON: {"intent": "brainstorm|writing|other"}
```

`/brainstorm` → 跳过检测，直接创建。显式命令优先。

## Brainstorm Tools

```
- lookup_settings(keywords)     # 按需查设定
- get_outline_context(node_id)  # 按需查大纲
- search_any(q, type, limit)    # 按需搜索
- save_inspiration(data)        # 提议保存，累积到 task.metadata["pending_inspirations"]
```

System prompt 防退化："搜索工具只是辅助。优先发散、联想、创造。"

## pending_saves 持久化

`pending_saves` 不存内存。存储为 `task.metadata["pending_inspirations"]`（JSON 字段），每次 Agent 调用 save_inspiration 后更新 task：

```python
task.metadata = {
    ...existing,
    "pending_inspirations": [
        ...existing,
        {"id": uuid, "type": "idea|setting|outline", "data": {...}, "created_at": "..."}
    ]
}
db.commit()
```

**事后确认**：用户可通过 Agent Task 历史页面查看 `status="completed"` 的 brainstorm task，其 metadata 中的 `pending_inspirations` 可继续确认（如果脑暴结束时未操作）。

## 确认流程

脑暴正常结束（`/done`）时：
- 展示 `pending_inspirations` 列表，每项带勾选框
- 用户选择性确认 → 确认的写入 `Idea(source="brainstorm")`
- 未勾选的丢弃
- `/cancel` → 保留已确认 Idea，丢弃 pending_inspirations

## Handoff

**触发**：用户脑暴中发送写作请求 → Agent 响应末尾 emit `action: handoff`

**信息传递**（防幻觉）：Writer 收到两份数据，不依赖 Agent 摘要：
1. 用户原始消息全文
2. `save_inspiration` 已提议/确认的灵感列表（结构化数据，来自 `pending_inspirations`）
3. 不传全量脑暴 AgentMessage 历史到 Writer（避免 token 爆炸）

```
handoff_context = {
    "user_message": "<原始消息>",
    "saved_inspirations": [...],   # 结构化灵感，非对话流水
}
```

**循环防护**：
- Handoff 目标 type 不能等于当前 type（brainstorm → brainstorm 禁止）
- `handoff_depth`（task.metadata 中）跨 task 传递，上限 3。超限 → 停止，提示用户
- 任何 task 的 handoff_depth ≥ 3 → 拒绝流转

## History Window

- 每轮 run_agent：注入最近 20 轮 AgentMessage
- 完整历史始终保留在 DB（AgentMessage 表），用户可通过历史页面查看
- Handoff 时不依赖 AgentMessage 历史 → 没有窗口截断与 handoff 的冲突

## Timeout

**检测**：每次用户发消息时被动检查。从最新 `AgentMessage.created_at` 计算距今时间。

**通知**：timeout 发生时，如果 SSE 连接仍在 → 推送系统事件告知用户。如果连接已断 → 用户下次进入 chat 时展示 banner。

**恢复**：用户下次发消息时检测到 timeout task：
```python
rule: type="brainstorm", status="timeout", updated_at DESC, LIMIT 1
```
提示 "X 分钟前的脑暴已超时，是否继续？" → 确认 → status="running"，加载历史。

**恢复语义**：`/brainstorm continue` 选择当前项目下 `type='brainstorm'` + `status IN ('completed','timeout')` 中 `updated_at` 最新的一个。提示 "恢复 X 分钟前的脑暴"。

## /brainstorm 语义

- `/brainstorm` → 新建 AgentTask(type="brainstorm")。每次都是新 session
- `/brainstorm continue` → 恢复最近的 completed/timeout task（按 updated_at DESC）
- 不自动合并旧 session

## Resource Quota

BrainstormConfig 内置（可在项目设置中覆盖）：

```python
max_steps: 50    # run_agent 每轮最多 50 个 tool-calling step
max_turns: 100   # 最多 100 轮用户-Agent 对话
token_budget: 100_000  # 累计 token 上限
```

触发上限 → Agent 友好提示用户 → 状态正常结束。

## Lock

Per-project `asyncio.Lock`，覆盖以下原子操作：
- 检测 active_task + 决定是否创建新 task
- task.status 转换（running → completed/cancelled/timeout）
- pending_inspirations 写入

**不覆盖** `run_agent()` 执行过程。并发请求到达时：
- 如果 active_task 存在 → 请求被路由到同一 task（正常行为，无需锁）
- 如果正在创建 task → 锁确保只有一个创建成功
- 如果正在修改 task.status → 锁确保不会并发 complete + cancel

## Frontend Changes

Brainstorm 模式需要前端配合：

1. **"结束脑暴" 按钮**：在 Brainstorm task 活跃时显示，发送 `/done`
2. **"取消脑暴" 按钮**：发送 `/cancel`
3. **灵感确认面板**：`/done` 后展示 `pending_inspirations` 列表，带勾选框，确认/丢弃
4. **超时恢复 Banner**：检测到 timeout task 时展示
5. **Task 状态指示**：chat 顶部显示当前模式（脑暴中 / 写作中）

## Migration

1. `app/routers/brainstorming.py` → 302 redirect 到 `/project/{project_id}/agent`（选择默认项目或让用户选择）
2. 旧模板保留一个版本
3. 全局搜索 `brainstorm` 引用，更新内部链接
4. 下一版本删除旧路由和模板

## Files

### New
- `app/agents/agents/brainstorm.py` — `build_brainstorm_config()`
- `app/agents/tools/brainstorm.py` — `save_inspiration` (写入 task.metadata)
- `app/agents/prompts/brainstorm_system.txt` — system prompt

### Modified
- `app/routers/agent.py` — 路由逻辑、handoff、timeout 检测与通知、lock、恢复
- `app/routers/__init__.py` — 302 redirect
- `app/static/js/agent-chat.js` — 前端按钮、确认面板、banner

### Deprecated (next version)
- `app/routers/brainstorming.py`
- `app/templates/brainstorm/`
