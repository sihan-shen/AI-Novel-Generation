# Task 24 Evidence — Wave 4-T7: writer↔agent bridge

## Changes
- `novel-frontend/src/app/projects/[id]/writer/page.tsx`: Wired dead "AI" button to navigate to agent page with `?chapter={selectedId}&mode=writing` using `useRouter`. Button disabled when no chapter selected.
- `novel-frontend/src/app/projects/[id]/agent/page.tsx`: Reads `chapter` and `mode` query params via `useSearchParams` on mount, pre-selects chapter picker and mode selector. Added "继续写作" handoff affordance button that appears when `handoffSummary` is set (from `brainstorm_handoff` SSE event), switches mode to writing and pre-fills input with brainstorm summary.
- `novel-frontend/src/stores/agent.ts`: Added `handoffSummary: string | null` field + `setHandoffSummary` action + cleared on `reset`.
- `novel-frontend/src/hooks/use-sse.ts`: On `brainstorm_handoff` event, extracts `summary` and calls `setHandoffSummary`.

## Verification
```
cd novel-frontend && npm run lint        # pass (0 errors)
cd novel-frontend && npm run build       # pass (8 static + 5 dynamic routes)
cd /home/sihan/文档/Projects/AI-Novel-Generation && .venv/bin/python -m pytest tests/ -q --tb=no
# 220 passed
```

## Commit
`feat(frontend): writer↔agent bridge with chapter + handoff context`
SHA: 602dde6

## Adversarial QA
- **misleading_success_output**: probed — build output shows real route compilation; pytest 220/220 passed
- **dirty_worktree**: probed — git status --short post-commit shows only .omo/ state files and pre-existing untracked evidence; commit 602dde6 contains exactly the 4 intended files
- **stale_state**: not-applicable — no cached artifacts
- **flaky_tests**: not-applicable — deterministic lint + build + pytest
- **hung_or_long_commands**: not-applicable — build completes in ~2s
- **malformed_input**: not-applicable — no new input parsing
- **prompt_injection**: not-applicable — no LLM prompts
- **cancel_resume**: not-applicable — no resumable flow in this task
- **repeated_interruptions**: not-applicable — single-shot task
