# Brainstorm Agent Migration Design

## Summary

将现有独立头脑风暴页面（`/brainstorm`）迁移为 Agent 系统内的 Brainstorm Agent。用户在 Agent 聊天页面通过自然语言触发脑暴，Brainstorm Agent 接管对话，结束后归还控制权给主 Orchestrator。

## Architecture

```
User Message → Agent SSE (/project/{id}/agent/chat/stream)
    ↓
Orchestrator state == IDLE?
    ↓
Intent Detection (LLM判断是否脑暴意图)
    ↓
├─ Non-brainstorm → Normal Orchestrator flow
└─ Brainstorm → OrchestratorState.BRAINSTORMING
                  ↓
             Brainstorm Agent (multi-turn chat with tools)
                  ↓
             Agent responds → stays BRAINSTORMING, waits for next message
                  ↓
             User says done / Agent finishes → IDLE
```

## State Machine Changes

```
IDLE ──(brainstorm intent)──→ BRAINSTORMING ──(finish)──→ IDLE
  │                                   │
  └──(writing request)──→ GATHERING_CONTEXT → WRITING → ...
```

New state: `OrchestratorState.BRAINSTORMING`

## Files

### New
- `app/agents/agents/brainstorm.py` — `build_brainstorm_config()` factory
- `app/agents/tools/brainstorm.py` — `save_inspiration` tool
- `app/agents/prompts/brainstorm_system.txt` — system prompt (adapted from brainstorm_chat.txt)

### Modified
- `app/agents/orchestrator.py` — add BRAINSTORMING state, `_run_brainstormer()`, intent detection
- `app/routers/agent.py` — SSE endpoint supports brainstorm multi-turn
- `app/routers/__init__.py` — remove brainstorm router registration

### Deleted
- `app/routers/brainstorming.py`
- `app/templates/brainstorm/` (7 files)

## Brainstorm Agent Tools

Read-only + save:
- `lookup_settings` — query project settings
- `get_outline_context` — query outline tree
- `search_any` — cross-entity search
- `save_inspiration` — save brainstom result (settings/outlines/ideas) to project DB

## Brainstorm Agent Flow

1. Orchestrator is IDLE, user sends message
2. Intent detection: lightweight LLM call judges `{"is_brainstorm": true/false}`
3. If true → state = BRAINSTORMING
4. `_run_brainstormer(user_message)`:
   - Load conversation history from blackboard (current brainstorm session turns)
   - Build AgentConfig with brainstorm system prompt + tools
   - `run_agent()` with user message as input
   - Agent thinks, optionally calls tools, generates response
   - If agent emits `action: finish` → state = IDLE
   - Else → state = WAITING_USER (wait for next user message)
5. Next user message arrives → SSE endpoint sees WAITING_USER + previous state was BRAINSTORMING → routes back to `_run_brainstormer()`
6. Repeat until user or agent ends session

## Intent Detection

Lightweight prompt for intent classification when orchestrator is IDLE:

```
用户消息: "{user_message}"
判断用户是否想要进行头脑风暴/寻找灵感/拓展创意。
返回 JSON: {"is_brainstorm": true/false}
```

Only triggers when state is IDLE. Writing tasks proceed through normal flow.

## Brainstorm Session Lifecycle

- **Start**: Intent detected, state → BRAINSTORMING, blackboard initializes brainstorm history
- **During**: Each user message → agent responds. Tools available for context lookup and saving
- **End**: User says "好了/就这样/先到这" OR agent emits finish action
- **After end**: State → IDLE, brainstom history saved as Idea (source="brainstorm"), control returned to orchestrator
