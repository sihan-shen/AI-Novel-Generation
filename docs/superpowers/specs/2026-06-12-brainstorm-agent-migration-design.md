# Brainstorm Agent Migration Design

## Summary

将现有独立头脑风暴页面（`/brainstorm`）迁移为 Agent Chat 内的脑暴模式。Brainstorm 不是新 Agent 类型，不是新 Session 类，只是 `AgentTask(task_type="brainstorm")` — 复用现有基础设施，仅 prompt + tools + 少量路由逻辑不同。

## No New Abstractions

```
新增: AgentTask.type = "brainstorm"
       BrainstormConfig (prompt + tools)
       路由规则（什么时候创建 brainstorm task）
       少量 UI（结束按钮、灵感确认）

不改: Orchestrator 状态机
      AgentTask / AgentMessage 模型
      Blackboard
      SSE 通道
      run_agent() 循环
```

## Architecture

所有路由经过 Orchestrator 的单一控制平面：

```
User Message → SSE endpoint
    ↓
active_task?
    ├── Yes → 根据 task.type 路由
    │           ├── "write_chapter" → Orchestrator state machine (_run_writer etc.)
    │           └── "brainstorm"    → _run_brainstorm_task(message)
    │
    └── No (IDLE) → Intent Detection
                      ├── "brainstorm" → 创建 AgentTask(type="brainstorm") → 路由到 brainstom
                      └── "writing"   → 创建 AgentTask(type="write_chapter") → 正常流程

_run_brainstorm_task(message):
    1. 构建 BrainstormConfig (system prompt + tools)
    2. 从 AgentMessage 加载当前 task 的历史轮次
    3. run_agent(config, blackboard, adapter)  # 复用现有 agent loop
    4. Agent 响应 → 持久化为 AgentMessage → SSE 推送
    5. state → WAITING_USER（复用现有状态）
    6. 下一条用户消息 → 回到步骤 1
```

**关键**：Brainstorm 不 bypass Orchestrator。Brainstorm task 的 WAITING_USER 和 Writing task 的 WAITING_USER 是同一个状态，通过 `active_task.type` 区分路由目标。单一控制平面。

## Brainstorm Task 生命周期

```
创建 AgentTask(type="brainstorm", status="running")
    ↓
每轮用户消息 → run_agent() → AgentMessage → SSE
    ↓
┌─ /done 或前端按钮 → status="completed" → 回到 IDLE
├─ /cancel          → status="cancelled" → 回到 IDLE
├─ 15min timeout    → status="timeout" → 回到 IDLE
└─ Agent 无权限主动结束（只允许用户结束）
```

恢复：用户下次发消息时，检测到 `status="timeout"` 且 `< 24h` → 提示 "是否继续上次脑暴？" → 用户确认 → status 改回 "running"，加载历史消息继续。

## Handoff（防信息损失、防幻觉）

当用户脑暴中说 "帮我写第一章"：

1. Brainstorm Agent 处理该消息
2. Agent 响应结尾 emit `action: handoff`
3. Orchestrator 收到 handoff：
   - 当前 brainstom task → status="completed"
   - 创建新 AgentTask(type="write_chapter")
   - Writer 的 context 包含：**用户原始消息全文** + 脑暴期间 AgentMessage 历史（作为附加上下文注入 blackboard，而非替换用户消息）
4. Writer 同时看到用户的原始措辞和脑暴上下文
5. 不依赖 Brainstorm Agent 生成的 summary → 消除幻觉传递

**Handoff 深度限制**：`task.metadata["handoff_count"]`，上限 3。每次 handoff +1，超限 → 停止流转，提示用户明确指令。

## Context Management

不预注入全部项目上下文。Agent 通过工具按需获取：

```
Brainstorm 工具集:
- lookup_settings(keywords)     # 按需查设定
- get_outline_context(node_id)  # 按需查大纲
- search_any(q, type, limit)    # 按需搜索
- save_inspiration(data)        # 提议保存灵感（累积到 pending_saves）
```

**防退化为检索助手**：System prompt 明确 "你是创意顾问，搜索工具只是辅助。优先发散、联想、创造新想法，只在需要确认已有内容时才查询。"

**历史窗口**：每轮 run_agent 时，加载最近 20 轮 AgentMessage 作为对话历史。超过部分不注入（用户可通过 `/history` 查看完整记录）。不做压缩（压缩引入语义断裂风险大于 token 节省收益）。

token 预算通过 `AgentConfig.token_budget` 控制（默认 50K），由 `run_agent()` 现有机制自动截断。

## save_inspiration：选择性批量确认

- Agent 可提议保存灵感 → 存入 `pending_saves`（不打断用户，仅在 Agent 回复末尾展示 "待保存灵感: N"）
- 脑暴正常结束时 → 展示所有 pending_saves 列表 → 用户可逐项勾选（非全量确认）
- 已确认的 → 写入 `Idea(source="brainstorm")`
- 未勾选的 → 丢弃
- `/cancel` → 保留已确认 Idea，丢弃 pending_saves
- 对话历史始终作为 AgentMessage 保留（不影响 Idea 库纯净度）

## Intent Detection

单一 LLM 调用（小模型，低 temp），仅在 IDLE 且无 active_task 时：

```
用户消息: "{user_message}"
判断意图：
- "brainstorm": 创意帮助、灵感拓展、方案探索。隐含表达包括
  "不知道怎么写"、"不够精彩"、"还能怎么玩"、"卡住了"、"没思路"等
- "writing": 明确的写作/修改/生成请求
- "other": 以上都不是
返回 JSON: {"intent": "brainstorm|writing|other"}
```

`/brainstorm` 命令直接创建 brainstom task，跳过检测。显式命令优先。

## Handoff：信息传递设计

handoff 时不依赖 Agent 总结。Writer 收到：
1. 用户原始消息（完整保留措辞、细节、风格要求）
2. 脑暴 AgentMessage 历史（作为 blackboard 附加上下文）

Writer 自行从原始消息 + 脑暴上下文中提取需要的信息，而非信任 Brainstorm Agent 的摘要。

## Lock

Per-project asyncio.Lock 保护 active_task 的创建和状态转换。Agent 执行期间（run_agent）释放锁，不阻塞其他 project 操作。只锁 "谁获得 active_task" 的决策，不锁 agent 执行过程。

## Timeout 机制

- 每次收到用户消息时，检查当前 active_task 的 `last_activity`（从最新 AgentMessage.created_at 获取）
- 超过 15 分钟 → task.status = "timeout"
- Timeout 检查随用户请求触发（被动），无需后台 cron
- 无人访问的 session 不产生额外成本

## /brainstorm 语义

- `/brainstorm` → 新建 AgentTask(type="brainstorm")
- `/brainstorm continue` → 恢复最近的 brainstom task（completed 或 timeout）
- 每次 `/brainstorm` 是新 session（新 AgentTask），不自动合并旧 session

## Resource Quota

BrainstormConfig 内置限制（在 AgentConfig 中配置）：
- `max_steps`: 50（最多 50 轮对话）
- `token_budget`: 100_000（累计 token 上限）
- 触发上限时 Agent 提示用户，状态正常结束

## Observability

追踪指标（实现阶段记录，不阻塞功能）：
- intent 分布（brainstorm/writing/other）
- brainstom task 平均轮数、完成率、timeout 率、取消率
- handoff 次数及目标
- save_inspiration 确认率
- per-task token 消耗

## Files

### New
- `app/agents/agents/brainstorm.py` — `build_brainstorm_config()`
- `app/agents/tools/brainstorm.py` — `save_inspiration`（累积 proposal，返回待确认列表）
- `app/agents/prompts/brainstorm_system.txt` — system prompt

### Modified
- `app/models/agent_task.py` — 无需改模型，task_type="brainstorm" 即用
- `app/routers/agent.py` — 路由逻辑、handoff 处理、timeout 检查、lock
- `app/routers/__init__.py` — 302 redirect `/brainstorm`

### Deprecated (next version)
- `app/routers/brainstorming.py` → 302 redirect
- `app/templates/brainstorm/`
