# Todo 20 — Wave 4-T3: cancel/stop button + reconnect/resume

## Commit
SHA: a791915
Message: feat(frontend): stop button + reconnect/resume with AbortController

## Files changed
- novel-frontend/src/hooks/use-sse.ts
- novel-frontend/src/app/projects/[id]/agent/page.tsx

## What changed
1. `use-sse.ts`:
   - `cancel(projectId)` now calls `controller.abort()` AND POSTs to `/api/project/${projectId}/agent/chat/cancel`
   - Added `checkResume(projectId)` that probes `/tasks` for `waiting_user`/`running` tasks, then fetches `/pending-actions` and surfaces `taskId` via `setTaskId`
   - Hook now returns `{ send, cancel, reset, checkResume }`

2. `agent/page.tsx`:
   - Destructures `cancel` and `checkResume` from `useAgentSSE()`
   - Calls `checkResume(projectId)` on mount via `useEffect`
   - Adds a "停止" button (Square icon, red styling) in the header, visible only when `isStreaming`, `onClick={() => cancel(projectId)}`

## Verification
- `npm run lint`: 0 errors, 0 warnings
- `npm run build`: success (Next.js 16.2.9, 12 routes)
- `pytest tests/ -q --tb=no`: 220 passed
- `git status --short`: only the two intended files modified (+ pre-existing evidence/continuation files)

## Adversarial QA
- cancel without active stream: `controller.abort()` on null controller is a no-op; POST to cancel returns 200 with "No active task" (backend handles gracefully)
- checkResume with no tasks: `/tasks` returns empty list → no-op, no store mutation
- checkResume with network error: caught and ignored (`/* no-op */`)
- Backend orphaning: the cancel function ALWAYS calls the backend endpoint, so the orchestrator receives the cancellation token even if the fetch abort races.
