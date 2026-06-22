# Todo 35 Evidence — Vitest frontend setup + agent store/SSE parser tests

## Commit
`fc98251` test(frontend): vitest setup + agent store/SSE parser tests

## Files changed
- `novel-frontend/package.json` — added vitest, @testing-library/react, @testing-library/jest-dom, jsdom to devDependencies; added `"test": "vitest run"` script
- `novel-frontend/vitest.config.ts` — created vitest config with jsdom environment, setup file, path aliases
- `novel-frontend/src/test-setup.ts` — imports @testing-library/jest-dom matchers
- `novel-frontend/src/stores/agent.test.ts` — 8 tests covering store reducer:
  - appendMessage
  - updateLastAssistantMessage (accumulation + creation)
  - appendToolCall
  - appendSuggestion
  - removeSuggestion
  - setOrchestratorState
  - reset
- `novel-frontend/src/hooks/use-sse.test.ts` — 9 tests covering:
  - parseSSEChunk with event: + data: lines
  - parseSSEChunk missing data → null
  - parseSSEChunk malformed JSON → null
  - parseSSEChunk missing event → defaults to "message"
  - text_delta accumulation via store
  - tool_call → toolCalls slice
  - confirm_request → suggestions slice
  - malformed data line → skipped without crash
  - full synthetic SSE transcript → store populated correctly
- `novel-frontend/src/hooks/use-sse.ts` — exported `parseSSEChunk` for testability

## Verification results

### Frontend tests
```
$ cd novel-frontend && npx vitest run
 RUN  v3.2.6
 ✓ src/stores/agent.test.ts (8 tests)
 ✓ src/hooks/use-sse.test.ts (9 tests)
 Test Files  2 passed (2)
      Tests  17 passed (17)
```

### Frontend lint
```
$ cd novel-frontend && npm run lint
> novel-frontend@0.1.0 lint
> eslint
(no errors)
```

### Frontend build
```
$ cd novel-frontend && npm run build
✓ Compiled successfully
✓ Generating static pages (8/8)
```

### Backend tests (regression)
```
$ .venv/bin/python -m pytest tests/ -q --tb=no
246 passed
```

## Adversarial classes probed
- **malformed input** — parseSSEChunk returns null for malformed JSON / missing data: ✓
- **stale state** — Zustand snapshot behavior verified (getState() re-fetched after mutations) ✓
- **flaky tests** — no async/timing-dependent tests; all synchronous ✓
- **misleading success output** — 17 tests all have concrete assertions (not just snapshot/mocking) ✓
- prompt injection — not applicable (no LLM calls in tests)
- cancel/resume — not applicable (no long-running flows)
- dirty worktree — commit staged only todo-35 files; `git status --short` shows remaining uncommitted changes from prior waves
- hung commands — not applicable (tests run in <1s)
- repeated interruptions — not applicable
