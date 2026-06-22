# Wave 0 Evidence — Task 1: dirty-worktree hygiene

## Commit
- **SHA:** `d9846af`
- **Message:** `chore(wave0): integrate in-flight dirty-worktree edits before agent overhaul`
- **Branch:** `feat/agent-and-project-optimization`

## File Dispositions

All 13 files were classified as **(a) SAFE TO COMMIT as-is** — they represent the user's in-flight token/semantic-consistency redesign and minor backend fixes. None conflict with any later plan wave.

| # | File | Disposition | Notes |
|---|------|-------------|-------|
| 1 | `app/llm/adapter.py` | **committed** in `d9846af` | Adds `.lower()` to provider string (safe normalization fix) |
| 2 | `app/llm/provider_registry.py` | **committed** in `d9846af` | Adds `.lower()` to provider string (safe normalization fix) |
| 3 | `app/main.py` | **committed** in `d9846af` | Comment update only (`# sync with pyproject.toml`) |
| 4 | `app/routers/config.py` | **committed** in `d9846af` | Adds new `GET /fetch-models` endpoint (additive, no breaking changes) |
| 5 | `novel-frontend/src/app/config/page.tsx` | **committed** in `d9846af` | Config page UI overhaul with provider selector, presets, model fetch |
| 6 | `novel-frontend/src/app/page.tsx` | **committed** in `d9846af` | Dashboard UI improvements (semantic tokens, project previews) |
| 7 | `novel-frontend/src/app/projects/[id]/outline/page.tsx` | **committed** in `d9846af` | Minor outline page adjustments |
| 8 | `novel-frontend/src/app/projects/[id]/page.tsx` | **committed** in `d9846af` | Project detail page UI improvements |
| 9 | `novel-frontend/src/app/projects/[id]/settings/page.tsx` | **committed** in `d9846af` | Minor settings page adjustment (1 line removed) |
| 10 | `novel-frontend/src/app/projects/page.tsx` | **committed** in `d9846af` | Projects list UI overhaul |
| 11 | `novel-frontend/src/hooks/use-sse.ts` | **committed** in `d9846af` | Removes unused `setTaskId` destructuring (cleanup) |
| 12 | `novel-frontend/src/lib/queries/config.ts` | **committed** in `d9846af` | Adds `useFetchModels` hook (additive) |
| 13 | `pyproject.toml` | **committed** in `d9846af` | Version bump 0.1.0→0.2.0, metadata, `python-dotenv`, dev deps |

## Stashes
- None created. No WIP files required stashing.

## Conflicts flagged
- None. All files are safe additive changes that do not interfere with later waves.

## Baseline Verification
- **Pre-commit pytest:** `108 passed, 266 warnings in 7.47s`
- **Post-commit pytest:** `108 passed, 266 warnings in 7.45s`
- **Frontend lint:** `eslint` clean (no errors)
- **Frontend build:** `Compiled successfully`, 12 routes generated

## Adversarial QA
- `dirty_worktree`: Probed — all 13 files enumerated, diff-reviewed, and dispositioned. No leftover user WIP remains.
- `misleading_success_output`: Probed — pytest baseline captured before (`108 passed`) and after (`108 passed`) commit. No regression.
- `stale_state`: Not applicable — no generated artifacts in this wave.
- `flaky_tests`: Not applicable — no new tests added in this wave.
