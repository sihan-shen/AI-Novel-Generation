# Brainstorm Agent Migration Design

## Summary

将现有独立头脑风暴页面（`/brainstorm`）迁移为 Agent 系统内的 Brainstorm Agent。用户在 Agent 聊天页面通过自然语言或显式命令触发脑暴，Brainstorm Agent 接管对话，结束后归还控制权给主 Orchestrator。

## Architecture

```
User Message → Agent SSE (/project/{id}/agent/chat/stream)
    ↓
Orchestrator state == IDLE?
    ↓
Keyword pre-filter → LLM Intent Detection (二分类)
    ↓                                       ↓
├─ Non-brainstorm → Normal Orchestrator flow
└─ Brainstorm (or /brainstorm) → OrchestratorState.BRAINSTORMING
                                      ↓
                                 Brainstorm Agent (multi-turn chat with tools)
                                      ↓
                          ┌─ User continues → WAITING_USER → next msg → BRAINSTORMING
                          ├─ /done or agent finish → save history → IDLE
                          ├─ /cancel → discard → IDLE
                          └─ 15min timeout → auto-save draft → IDLE
```

## State Machine Changes

```
                              ┌── /cancel / timeout ──→ IDLE (discard or draft saved)
                              │
IDLE ──(brainstorm intent)──→ BRAINSTORMING ──(/done / agent finish)──→ IDLE (save history)
  │                              │
  └──(writing request)──→ GATHERING_CONTEXT → WRITING → REVIEWING → ...
```

New states: `OrchestratorState.BRAINSTORMING`, `OrchestratorState.WAITING_USER` (already exists in enum).

## Files

### New
- `app/agents/agents/brainstorm.py` — `build_brainstorm_config()` factory
- `app/agents/tools/brainstorm.py` — `save_inspiration` tool
- `app/agents/prompts/brainstorm_system.txt` — system prompt (adapted from brainstorm_chat.txt)

### Modified
- `app/agents/orchestrator.py` — add BRAINSTORMING state, `_run_brainstormer()`, intent detection, cancel/timeout
- `app/routers/agent.py` — SSE endpoint supports brainstorm multi-turn routing, explicit commands
- `app/routers/__init__.py` — remove brainstorm router registration

### Deleted (after dependency check)
- `app/routers/brainstorming.py`
- `app/templates/brainstorm/` (7 files)
- Run global search for `brainstorm` references before deletion, ensure no residual imports

## Brainstorm Agent Tools

Read-only + controlled save:
- `lookup_settings` — query project settings
- `get_outline_context` — query outline tree
- `search_any` — cross-entity search
- `save_inspiration` — save brainstorm result to project DB. **Constraints**:
  - Bound to current project_id only
  - New ideas: auto-saved without confirmation
  - Modifying existing outlines/settings: agent must emit confirm_request and wait for user approval
  - Tool parameters: `type` ("idea"|"setting"|"outline"), `data` (dict), `confirm_required` (bool)

## Brainstorm Agent Flow

1. Orchestrator is IDLE, user sends message
2. **Intent detection** (two-stage):
   - Stage 1: Keyword/regex pre-filter. Patterns: `脑暴|头脑风暴|灵感|创意|拓展思路|有什么想法|帮我想想|构思|点子`. If no match → skip LLM call, proceed to normal flow.
   - Stage 2: Keyword match → lightweight LLM call: `{"is_brainstorm": true/false}`.
   - Explicit trigger: `/brainstorm` or command palette "Brainstorm" → skip detection, directly enter.
3. If true → state = BRAINSTORMING, blackboard initializes `brainstorm_history = []`
4. `_run_brainstormer(user_message)`:
   - Load `brainstorm_history` from blackboard (isolated from main conversation)
   - Build AgentConfig with brainstorm system prompt + tools
   - `run_agent()` with user message + history as context
   - Agent thinks, optionally calls tools, generates response
   - Append to `brainstorm_history`: `{role, content, tool_calls?}`
   - If agent emits `action: finish` → compress history → save as Idea → state = IDLE
   - Else → state = WAITING_USER
5. **SSE multi-turn routing**: When SSE endpoint receives next message:
   - If `previous_state == BRAINSTORMING` and `current_state == WAITING_USER` → route to `_run_brainstormer()` (no re-detection)
   - If message is `/done` or `/end` → force finish, save history → IDLE
   - If message is `/cancel` → discard brainstorm history → IDLE
   - If message is a writing task request → Brainstorm Agent handles it per prompt rules (see below)
6. **Frontend**: Show "结束脑暴" button during BRAINSTORMING state, sends `/done` system message
7. Repeat until end/cancel/timeout

## Intent Detection

Two-stage, only when state is IDLE:

**Stage 1 — Keyword pre-filter** (zero cost):
```
脑暴|头脑风暴|灵感|创意|拓展思路|有什么想法|帮我想想|构思|点子|想想办法|没思路|卡住了
```

**Stage 2 — LLM confirmation** (only if stage 1 matches):
```
用户消息: "{user_message}"
判断用户是否想要进行头脑风暴/寻找灵感/拓展创意。注意区分"什么是头脑风暴"等定义类问题（非脑暴意图）。
返回 JSON: {"is_brainstorm": true/false}
```

**Explicit bypass**: `/brainstorm` command skips both stages.

## Cancel, Timeout, and Finish

### Cancel
- User sends `/cancel` or "取消脑暴" → discard `brainstorm_history`, state → IDLE
- Frontend "取消" button sends `/cancel`

### Timeout
- 15 minutes without user interaction → auto-end
- Compress brainstorm history into summary, save as Idea draft
- State → IDLE, emit event notifying user

### Finish
- User: `/done`, `/end`, "好了", "就这样", "先到这", frontend "结束脑暴" button
- Agent: emits `action: finish` when it determines user has sufficient inspiration
- System prompt reinforces: "当用户明确表示结束或你判断已给出足够创意后，必须输出 FINISH 动作"

## State Priority During BRAINSTORMING

When state is BRAINSTORMING or WAITING_USER (post-brainstorm), ALL user messages route to Brainstorm Agent. Brainstorm Agent's system prompt includes:

> 你只负责头脑风暴和创意拓展。如果用户请求写章节、修改设定等非脑暴任务，请告知用户先结束脑暴（输入 /done）再发起写作请求。

This keeps responsibilities clear without needing complex intent switching mid-session.

## Brainstorm History Isolation

- `blackboard.brainstorm_history`: `list[dict]` — stores `{role, content, tool_calls?}` for current session only
- On session end (normal finish):
  - Full brainstorm conversation → compressed into single summary message + user's original messages
  - Saved as `Idea(source="brainstorm")` with raw messages in `content`
  - A brief summary appended to main conversation context (1 message, not full history)
- On cancel: discarded entirely

## Concurrency Lock

- Per-project `asyncio.Lock` in SSE endpoint
- Only one agent request processed per project at a time
- Subsequent requests receive "busy" response with current state info
- Timeout + error recovery: if agent call throws, catch → log → state → IDLE

## Observability (future iteration)

- Separate trace span for Brainstorm Agent: enter/exit timestamps, tool call count, token usage
- End reason tracking: user_finish / agent_finish / timeout / cancel
- Log to structured logger with `agent: "brainstorm"` tag

## Migration Checklist

1. Global search for `brainstorm` references (exclude new agent files)
2. Check all imports in `app/routers/__init__.py` and `app/main.py`
3. Check static files (JS/CSS) for `/brainstorm` URL references
4. Check templates for links to `/brainstorm`
5. Remove old router and templates only after confirming zero residual references
6. Keep `brainstorm_service.py` and `brainstorm_chat.txt` temporarily — Brainstorm Agent may reuse prompt content
