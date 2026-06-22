# Task 19 — Wave 4-T2: streaming token render + extracted reasoning/tool-call panels

## Commit
SHA: 80dbfd5
Message: feat(frontend): streaming token render + extracted reasoning/tool-call panels

## What was verified vs fixed

### Verified (already correct from 4-T1)
1. **use-sse.ts** — `text_delta` events correctly route to `updateLastAssistantMessage(chunk)` (lines 133-143). In-place append, NOT a new message bubble.
2. **use-sse.ts** — `tool_call` events correctly call `appendToolCall({... status: "running"})` (lines 161-176).
3. **use-sse.ts** — `tool_result` events correctly call `updateToolCallStatus(tcId, success ? "success" : "failed", resultText)` (lines 179-193).
4. **agent/page.tsx** — Streaming indicator (3-bounce-dot + "等待响应...") renders when `isStreaming && !isEmpty` (lines 105-114).
5. **reasoning-panel.tsx** — Collapsible with `useState(false)` for `open`. Toggle button with ▼/▶ icons.
6. **tool-call-panel.tsx** — Collapsible with `useState(false)`. Status icons mapped correctly: running→🔄, success→✓, failed→✗, cancelled→—, default→⏳.

### Fixed
1. **stores/agent.ts** — `updateLastAssistantMessage` previously returned unchanged state when no assistant message existed (e.g., first `text_delta` arrives before any `agent_output`). Fixed to create a new assistant message with `crypto.randomUUID()` when `msgs.length === 0` or last message is not from assistant. This ensures `text_delta` events ALWAYS render visible text, even as the first event of a turn.

## Verification commands & results

```
cd novel-frontend && npm run lint
# 0 errors, 2 pre-existing warnings (unused eslint-disable in use-sse.ts:264,313)

cd novel-frontend && npm run build
# Compiled successfully in 2.4s, TypeScript clean, 8 static pages generated

cd /home/sihan/文档/Projects/AI-Novel-Generation && .venv/bin/python -m pytest tests/ -q --tb=no
# 220 passed
```

## Files changed
- `novel-frontend/src/stores/agent.ts` (+13/-2)
