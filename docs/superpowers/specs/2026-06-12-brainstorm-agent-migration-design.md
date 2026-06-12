# Brainstorm Agent Migration Design

## Summary

将现有独立头脑风暴页面（`/brainstorm`）迁移为 Agent 系统内的 Brainstorm Agent。用户在 Agent 聊天页面通过自然语言触发脑暴，Brainstorm Agent 接管对话，结束后归还控制权给主 Orchestrator。

## Architecture

```
User Message → Agent SSE (/project/{id}/agent/chat/stream)
    ↓
Orchestrator state == IDLE?
    ↓
LLM Intent Detection → {intent: "brainstorm" | "writing" | "other"}
    ↓
├─ "writing" → Normal Orchestrator flow (GATHERING_CONTEXT → WRITING → ...)
├─ "other" → General agent response
└─ "brainstorm" → state = BRAINSTORMING, active_agent = "brainstorm"
                        ↓
                   Brainstorm Agent handles message
                   (always has project context + brainstorm_history)
                        ↓
            ┌─ User continues → WAITING_USER, active_agent = "brainstorm"
            ├─ /done or frontend button → save full history → IDLE, active_agent = None
            ├─ User sends writing request → agent wraps up → handoff → normal flow
            └─ 15min timeout → save draft (full history) → IDLE
```

## State Machine: `active_agent` Field

Avoid state explosion. Instead of per-agent states, use a generic `active_agent` field:

```python
# orchestrator or blackboard
state: OrchestratorState  # IDLE | GATHERING_CONTEXT | WRITING | REVIEWING |
                           # FIXING_SETTINGS | REWRITING | BRAINSTORMING |
                           # WAITING_USER | DONE | CANCELLED
active_agent: str | None  # "writer" | "reviewer" | "settings_mgr" | "brainstorm" | None
```

**Routing rule**: When `state == WAITING_USER`, check `active_agent` to determine who handles the next message. No `previous_state` inference needed.

```
IDLE ──(intent: brainstorm)──→ BRAINSTORMING (active_agent="brainstorm")
  │                                      │
  │                          ┌─ user continues ──→ WAITING_USER (active_agent="brainstorm")
  │                          │                          │
  │                          │              ┌─ next msg ──→ BRAINSTORMING
  │                          │              └─ /done ──→ IDLE (active_agent=None)
  │                          │
  │                          ├─ /done ──→ save full history → IDLE
  │                          └─ writing request ──→ agent wraps up → IDLE → normal flow
  │
  └──(intent: writing)──→ GATHERING_CONTEXT (active_agent="writer") → WRITING → ...
```

## Brainstorm as Mode, Not Isolation

Brainstorm Agent 是一个 **模式**，不是强隔离会话。

**规则**：
- BRAINSTORMING 状态下，消息默认由 Brainstorm Agent 处理
- 如果用户发出明确的写作请求（"帮我写第一章"），Brainstorm Agent 的 prompt 引导它：
  1. 简洁总结脑暴成果
  2. Emit `action: handoff` + 用户原始消息
  3. Orchestrator 收到 handoff → 保存脑暴历史 → state = IDLE → 将用户消息重新路由到写作流程
- 用户无需先 `/done` 再发写作请求

**Brainstorm Agent prompt 片段**：
> 你是创意顾问，只负责头脑风暴。如果用户给出了明确的写作/修改请求（如"写第一章"），请简要总结当前脑暴成果，然后输出 handoff 动作让系统切换回写作模式。不要拒绝用户或要求用户手动切换。

**禁止 Agent 自动 finish**：
- Agent 不会自己判断"用户得到足够灵感"然后结束
- 结束只能由用户触发：`/done`、前端按钮、或 timeout
- Agent 只能在 prompt 中温和提示"如果你觉得差不多了，可以点结束按钮"

## Intent Detection

单一 LLM 调用，高召回 prompt，覆盖隐含创意需求：

```
用户消息: "{user_message}"

判断用户的意图类别：
- "brainstorm": 需要创意帮助、灵感拓展、方案探索、设定讨论、剧情构思。
  包括隐含表达："不知道怎么写"、"不够精彩"、"有什么推荐"、"给我几个方案"、
  "还能怎么玩"、"主角职业推荐"、"后面怎么发展"、"卡住了"、"没思路"
- "writing": 明确的写作/修改/生成请求（如"写第一章"、"修改这段"）
- "other": 以上都不是（闲聊、一般问题、定义询问等）

返回 JSON: {"intent": "brainstorm|writing|other"}
```

- 只在 `state == IDLE` 时调用
- 使用小模型 + 低 temperature，降低延迟和成本
- 显式命令 `/brainstorm` 跳过检测，直接进入 BRAINSTORMING

## Brainstorm Agent Tools

- `lookup_settings` — 查询项目设定
- `get_outline_context` — 查询大纲树
- `search_any` — 跨实体搜索
- `save_inspiration` — 保存脑暴产物。**用户确认后才写入**：
  - Agent 调用时 emit `confirm_request`，附保存内容预览
  - 用户在 SSE 流中看到确认请求，点击确认后才实际写入 DB
  - 防止试探性内容、假设、胡思乱想污染 Idea 库

## Brainstorm History & Context

**始终包含项目上下文**：Brainstorm Agent 每次运行时，除了 `brainstorm_history`（当前会话轮次），还注入完整的项目上下文：

```python
context = {
    "project_meta": {...},        # 项目元信息
    "settings_context": "...",    # 完整设定集
    "outline_context": "...",     # 大纲树
    "style_context": "...",       # 文风指南
    "recent_chapters": "...",     # 最近N章摘要
    "brainstorm_history": [...],  # 当前脑暴会话的对话轮次
}
```

**不压缩历史**：脑暴结束时，完整对话历史（含已否决方案、分支思路）保存为 `Idea(source="brainstorm")`。不压缩，不做摘要丢失细节。用户后续可通过 Idea 引用恢复完整上下文。

**timeout 后恢复**：超时存档包含完整 `brainstorm_history`。用户下次进入脑暴时，检测到未完成的存档 → 询问是否继续。

## Explicit Commands

| 命令 | 作用 | 可用状态 |
|------|------|----------|
| `/brainstorm` | 强制进入脑暴模式 | IDLE |
| `/done` | 正常结束脑暴，保存历史 | BRAINSTORMING, WAITING_USER |
| `/cancel` | 取消脑暴，丢弃历史 | BRAINSTORMING, WAITING_USER |

**禁止自然语言结束检测**。不再尝试从用户消息中匹配 "好了"、"就这样" 等关键词。结束只能通过命令或前端按钮触发。

## SSE Multi-Turn Routing

```python
# In agent.py SSE endpoint, when receiving a new message:
if state == IDLE:
    intent = await detect_intent(message)
    if intent == "brainstorm":
        state = BRAINSTORMING
        active_agent = "brainstorm"
    elif intent == "writing":
        # normal orchestrator flow
    else:
        # general response

elif state == WAITING_USER and active_agent == "brainstorm":
    if message is "/done":
        save_full_brainstorm_history()
        state = IDLE
        active_agent = None
    elif message is "/cancel":
        discard_brainstorm_history()
        state = IDLE
        active_agent = None
    else:
        state = BRAINSTORMING
        await _run_brainstormer(message)

elif state == BRAINSTORMING and active_agent == "brainstorm":
    result = await _run_brainstormer(message)
    if result.action == "handoff":
        save_full_brainstorm_history()
        state = IDLE
        active_agent = None
        # Re-route user's original message through intent detection
        # (this time it will match "writing" and go through normal flow)
```

## Concurrency

- Per-project `asyncio.Lock` 仅保护 orchestrator **状态转换**，不锁整个 agent 调用
- 同一项目同一时刻只允许一个活跃的 agent 任务
- 并发请求返回 `{"status": "busy", "current_state": "...", "active_agent": "..."}`

## Old `/brainstorm` Page Migration

分步执行：
1. `/brainstorm` → 302 重定向到 `/project/{default_id}/agent`（或让用户选择项目）
2. 旧模板保留，但不再有入口链接
3. 观察一个版本周期
4. 下一版本删除 `app/routers/brainstorming.py` 和 `app/templates/brainstorm/`

## Files

### New
- `app/agents/agents/brainstorm.py` — `build_brainstorm_config()` factory
- `app/agents/tools/brainstorm.py` — `save_inspiration` tool (confirm-before-write)
- `app/agents/prompts/brainstorm_system.txt` — system prompt

### Modified
- `app/agents/orchestrator.py` — add BRAINSTORMING state, `active_agent` field, `_run_brainstormer()`, intent detection, timeout
- `app/agents/blackboard.py` — add `active_agent`, `brainstorm_history` fields
- `app/routers/agent.py` — SSE multi-turn routing, explicit command handling, lock
- `app/routers/__init__.py` — register brainstorm redirect route

### Deprecated (remove in next version)
- `app/routers/brainstorming.py` → 302 redirect
- `app/templates/brainstorm/` — keep for one version

## Observability (future iteration)

- Trace span per Brainstorm Agent session: enter/exit time, tool calls, tokens
- End reason tracking: user_done / handoff / timeout / cancel
- Structured logging with `agent: "brainstorm"` tag
