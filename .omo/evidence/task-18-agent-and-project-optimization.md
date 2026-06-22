# Task 18 Evidence — Wave 4-T1: structured SSE event routing + sliced agent store

## Commit
- SHA: `4c27665`
- Message: `feat(frontend): structured SSE event routing + sliced agent store`

## Files Changed
- `novel-frontend/src/hooks/use-sse.ts` — already done by previous worker (parses `event:` lines, routes by type into structured store, sends full ChatRequest body)
- `novel-frontend/src/stores/agent.ts` — already done by previous worker (structured slices: messages, toolCalls, reasoning, suggestions, orchestratorState, progress, taskId, isStreaming + actions)
- `novel-frontend/src/app/projects/[id]/agent/page.tsx` — rewritten (290 → 141 lines)
  - Imports extracted components from `@/components/features/agent/`
  - Uses structured store slices via `useAgentStore()`
  - Combines messages/toolCalls/reasoning/suggestions into a timeline sorted by `sequence`
  - Shows orchestrator state badge in header
  - Shows progress text in header
  - Keeps empty state (Sparkles icon + "开始你的创作对话")
  - Keeps input + send button
  - Removes inlined `ChatBubble`
  - Removes `messageType` label leak (C12 fix)
- **NEW** `novel-frontend/src/components/features/agent/chat-bubble.tsx` — extracted ChatBubble. Renders `AgentMessage` (user/assistant/system). Keeps glass bubbles + avatars.
- **NEW** `novel-frontend/src/components/features/agent/reasoning-panel.tsx` — collapsible panel for `ReasoningEvent`. Toggle button with label, expands to show reasoning text.
- **NEW** `novel-frontend/src/components/features/agent/tool-call-panel.tsx` — collapsible panel for `ToolCallEvent`. Status icon + tool name + args + result.
- **NEW** `novel-frontend/src/components/features/agent/suggestion-card.tsx` — renders `SuggestionEvent` as inline card with placeholder 批准/拒绝/修改 buttons (not wired yet — todo 4-T5).

## Verification
- `cd novel-frontend && npm run lint` — 0 errors (2 pre-existing warnings in use-sse.ts, unused eslint-disable directives)
- `cd novel-frontend && npm run build` — passes (Next.js 16.2.9, Turbopack, 8 static routes, 5 dynamic routes)
- `.venv/bin/python -m pytest tests/ -q --tb=no` — 220 passed
- `agent/page.tsx` line count: 141 lines (≤150 target met)
- `git log --oneline -1` — shows commit `ee1b92a`
- `git status --short` — clean (only unrelated `.omo/` untracked files from other tasks)

## Constraints Honored
- Did NOT rewrite `use-sse.ts` or `agent.ts`
- Did NOT add `react-markdown` (todo 4-T6)
- Did NOT add cancel button (todo 4-T3)
- Did NOT add mode selector (todo 4-T4)
- Did NOT touch any file outside the allowed scope
- Did NOT break backend tests
