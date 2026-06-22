# Task 26 — Wave 5-T2: unify agent router under `/api` + `APIResponse` envelope

**Status:** complete (finish-commit by orchestrator after original worker hit session limit)

**Plan:** `.omo/plans/agent-and-project-optimization.md` — todo 26 (line 332)
**Branch:** `feat/agent-and-project-optimization`

## Commit

- **SHA:** `c7c1c303e376305d1c8a00fae53e3108c928e08a`
- **Message:** `refactor(api): unify agent router under /api + APIResponse envelope for JSON endpoints`
- **Author:** Hanss &lt;19850597655@163.com&gt;
- **Date:** 2026-06-21 16:52 +0800

## Files in the commit (6)

| File | Change |
| --- | --- |
| `app/routers/agent.py` | prefix `/project/...` → `/api/project/...` (line 213) + 5 `response_model=APIResponse[...]` + wrap return values |
| `novel-frontend/src/hooks/use-sse.ts` | remove direct `BACKEND` bypass; use relative `/api/project/${projectId}/agent/chat/stream` (line 28) |
| `tests/test_agent_router.py` | 4 path updates + 2 body assertions |
| `tests/test_confirm_flow.py` | 5 path updates + 2 body assertions |
| `tests/test_cancel.py` | 3 path updates + 2 body assertions |
| `tests/test_orchestrator_session_isolation.py` | 2 path updates |

`novel-frontend/next.config.ts` was inspected but not modified — the existing `/api/:path*` rewrite at lines 8-13 already covers the new path.

## Verification (re-run by finish-commit orchestrator)

- `.venv/bin/python -m pytest tests/ -q --tb=no` → **216 passed, 13572 warnings in 10.55s**
- `git diff --stat` (pre-commit) → only the 6 listed files modified (the 6 diff lines: 43 insertions, 44 deletions)
- `git show --stat c7c1c30` → exactly the 6 listed files committed, nothing else
- `git status --short` (post-commit) → clean of todo-26 files; only `.omo/` plan-state entries remain (intentionally not staged)

## Plan checkbox

`.omo/plans/agent-and-project-optimization.md` line 332: `- [x] 26. Wave 5-T2: unify API prefix ...`

(The checkbox was flipped from `[ ]` to `[x]` by the previous work session prior to this finish-commit; this orchestrator verified it and did not re-edit it.)

## Notes

- The original implementation worker for this todo completed all 6 file changes and ran the test suite to 216 passed, but its session ended before `git commit` and the plan/ledger/evidence writes could land. The commit was created by a follow-up orchestration step that produced SHA `c7c1c30`; this finish-commit orchestrator verified it, did not amend, and recorded the evidence.
- `novel-frontend` lint + build were run by the original worker: clean (see `.omo/evidence/task-26-agent-and-project-optimization.log`).
- Adversarial classes probed: `misleading_success_output` (grep confirmed no `/project/...` paths remain in `tests/`), `flaky_tests` (pytest deterministic, 216/216 on a single run), `dirty_worktree` (commit contains only the 6 intended files). Other classes: not applicable for this finish-commit step.
