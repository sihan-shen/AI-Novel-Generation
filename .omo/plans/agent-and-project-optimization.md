# agent-and-project-optimization - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** 一个全面翻新后的 AI 小说创作工具，Agent 模块是重点：写作助手会用 LLM 原生的工具调用能力（更稳、支持流式逐字输出）、能真正在"建议→人工确认→继续"和"中途取消/刷新续跑"上闭环；审阅的四维检查不再是固定返回而是真跑 LLM；脑暴与写作、写作编辑器与 Agent 之间打通。前后端架构清理（删死代码、统一接口、配置驱动模型、日志）、测试与 CI 补齐。

**Why this approach:** 你说要"从架构/系统逻辑/UI/UX/功能/交互优化，着重 Agent"但没给具体目标，所以我按业界最佳实践定了默认方案：原生 tool-use + 流式（README 已承诺但当前是假的）、按任务独立数据库会话 + WAL（修一个现役的 use-after-close bug）、真·人在环确认与取消、黑板模式名副其实（agent 间能看到彼此输出）。Agent 核心先做（波 1-3），前端 Agent UI 跟上（波 4），跨切面清理（波 5）和测试/CI（波 6）收尾——这样按你的重点排程，每波都自带测试保绿现有 108 个用例。

**What it will NOT do:** 不加真实鉴权/账号体系；不换数据库（保持 SQLite，只修会话用法+开 WAL）；不重写非 Agent 功能页的 UX；不加新 LLM provider；不做 i18n/Docker/部署；不改动你当前 13 个未提交的 WIP 文件（先在波 0 安全提交/暂存）；不引入向量搜索/RAG。

**Effort:** XL（6 个组件，36 个实现 todo + 4 个最终验证，6 波 + 最终验证；实际执行顺序按依赖矩阵：波 0→1→2→3→(5-T1,5-T2,5-T6)→4→波 5 余下→6→最终验证）
**Risk:** 中 — 主因是 Agent 核心从 JSON 解析改原生 tool-use 的迁移 + SQLite 并发修复，必须全程保绿现有测试。脏工作区已在波 0 处理。注意：前端 Agent UI（波 4）依赖波 5 的 API 前缀统一（5-T2），故 5-T1/5-T2 须先于 4-T1 执行。
**Decisions I made for you:** 我把请求判定为"目标模糊"，自己采纳了这些最佳实践默认（你都可以在这里否决）：① Agent 用原生 tool-use API，local 模型保留 JSON 回退；② agent 循环流式逐字；③ 按任务独立 DB Session + SQLite WAL；④ 模型走配置（4 个 builder 删掉写死的 `claude-sonnet-4-6`）；⑤ 全 6 组件都做但 Agent 优先排程；⑥ 删死代码（旧脑暴路由/服务/模板、`main.py` 的 `/brainstorm` 重定向、未注册的 auth 中间件、未接的 retry 表项、死场景、死类型、死 store 字段）；⑦ agent 路由移到 `/api`；⑧ 实现 cancel + 中途持久化 + 续跑（不自动续跑，需用户点"继续"）；⑨ 前端结构化事件 + react-markdown；⑩ 一致性检查用 LLM 辅助而非纯桩；⑪ 多章/卷/幕 milestone 实现。全部可逆；无不可逆/安全关键项，故零提问。如果你其实有具体目标，说"我其实是想要 X"，我切换到提问模式。

> 路由判断：UNCLEAR（目标模糊）→ 我做了大量调研 + 采纳最佳实践默认 + 自动高精度评审（Metis + 双 Momus），不采访你。
> 注：删死代码中的 `middleware/auth.py` 是删除"未注册的空鉴权占位"，不是改动真实鉴权（项目本就没有鉴权）——与"不加真实鉴权"一致。

Your next move: 看完下面的完整计划后回复"开始 / start-work"让我交给 worker 执行；或指出要改的默认值/范围。完整执行细节见下文。

---

> TL;DR (machine): <1 line - effort, risk, deliverables>

## Scope
### Must have
- **Agent core (C1):** native provider tool-use API (Claude `tools=`+`tool_use` blocks; OpenAI `tools=`+`tool_calls`) with a per-adapter capability flag and a JSON-text fallback shim for tool-use-incapable providers (ollama/local); streaming token events (`text_delta`) during each LLM turn; structured `tool_call`/`tool_result` SSE events with real result objects; `confirm_before` actually suspends the loop on an `asyncio.Event` until `/chat/confirm` resumes it; per-task DB `Session` owned by the orchestrator (separate from the request SSE-generator session); SQLite WAL + `busy_timeout` + `pool_pre_ping`; model derived from `ConfigService`/adapter (not hardcoded); `record_usage` called for every agent LLM turn with `scenario` + `duration_ms`; fix the use-after-close bug (`asyncio.create_task(orch.run())` writing to a closed request-scoped Session).
- **Orchestrator/blackboard logic (C2):** `Blackboard.get_context_for` exposes `last_review`/`current_draft`/`pending_setting_changes`/`rewrite_round`/`current_chapter_id`; `_gathering_context` actually populates outline+style context (not `""`); rewriter feeds the review findings back into the writer context; real human-in-the-loop confirm (`confirm_request` event → suspend → resume via `/chat/confirm`); `/chat/cancel` + `CancellationToken` checked between orchestrator states; mid-run blackboard snapshot to `AgentTask` on state transitions + every N steps + real resume-from-snapshot on restart (replace the always-fail `_recover_agent_tasks`); multi-chapter/volume/act milestone loop driven by `milestone_granularity`.
- **Tool substance (C3):** `check_setting_consistency`/`check_style_consistency`/`check_logic_structure` implemented as LLM-assisted handlers (pass chapter+settings+style, return structured findings, not canned "ready"); `detect_conflicts`/`resolve_conflict` implemented (persist resolution); `search_any` in agent tools is project-scoped (no cross-project leak); `list_pending_inspirations` registered as a tool; chapter snapshot rollback endpoint; `record_usage` wired across all LLM call sites (`style_service`, `cleaning_service`, `outline_gen_service`, `review_service.run_review`).
- **Frontend Agent UI/UX (C4):** SSE hook parses `event:` lines and routes by type into a structured store (messages / toolCalls / reasoning / suggestions / state / progress); streaming token render (in-place append via `updateLastMessage`); per-turn collapsible reasoning + tool-call panels; cancel/stop button via `AbortController`; reconnect/resume (pass `resume_from` / `Last-Event-ID`); mode selector (brainstorm/writing) + chapter picker + autonomy preset UI that sends the full `ChatRequest` (not just `{message}`); pending-suggestion cards + inspirations confirm UI + orchestrator state/progress visualization + task history panel; `react-markdown` (+ `remark-gfm`) rendering for assistant content; remove the internal `messageType` label leak; `aria-live`/`aria-expanded`/`aria-label` accessibility; writer↔agent bridge (wire the dead "AI" button to open agent with chapter context; carry brainstorm handoff context).
- **Cross-cutting architecture cleanup (C5):** delete dead code (`routers/brainstorming.py`, `services/brainstorm_service.py`, `templates/brainstorm/` if present, register-or-remove `middleware/auth.py`, dead `RETRY_POLICY` entries, dead `ContextBuilder` scenarios `writing`/`style_analysis`/`cleaning`, dead `list_pending_inspirations` if not registered in C3, dead `api-client` auth plumbing, dead agent-store fields, dead `ErrorResponse`); unify API prefix (move agent router under `/api`; `APIResponse` for JSON endpoints; SSE stays raw stream); `lifespan` context manager (replace deprecated `@app.on_event`); robust `_recover_agent_tasks` (per-task `try/except`); `logging.basicConfig` + structured logging across services/routers/adapters; config-driven model fully wired; `GET /api/config` no longer returns plaintext `api_key` (mask); frontend dedup (`formatRelative`/`toneStyles`/`STATUS_BADGE` → `lib/utils`); `config.ts` uses `unwrap<T>()`; SSE routed through `/api` rewrite; remove or wire in the dead 4858-line `api.d.ts`; implement-or-remove the missing `/projects/[id]/review` page link; Pydantic v2 `ConfigDict` in `config.py`; `datetime.utcnow()` → `datetime.now(UTC)` across models; `model_rebuild()` for the outline schema forward-ref.
- **Test + quality hardening (C6):** `run_agent` loop missing branches (3-strike caps for malformed/hallucinated/retry, tool-handler-raises, non-string coercion, event emission, message-history growth, `_build_tool_schema_description`); orchestrator missing transitions (`WRITING→REVIEWING`, `WAITING_USER` break, `CANCELLED`, `run()` dispatch loop, `GATHERING_CONTEXT` success); SSE end-to-end tests (full event sequence, headers, brainstorm flow, reconnect with active task, 100-turn end); service + tool unit tests (review/setting tools, writer/reviewer/settings_mgr config builders, `brainstorm_service`/`outline_gen_service`/`review_service`/`setting_service`); Vitest frontend setup + agent reducer/SSE parser/store tests; CI workflow (`.github/workflows/ci.yml`: `pytest` + `npm run lint` + `npm run build`) + `ruff` config + `mypy` config + `biome.json` + `pre-commit` config + `pytest-cov` with `--cov-fail-under`.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- **No new auth system.** `middleware/auth.py` is either removed or stays a documented no-op placeholder. Do NOT implement real authentication, sessions, JWT, or user accounts.
- **No database migration.** Stay on SQLite. Do NOT introduce Postgres/MySQL/async-SQLAlchemy/`aiosqlite`. Only fix session usage + enable WAL.
- **No rewrite of the non-agent feature pages** (`projects`/`outline`/`settings`/`styles`/`ideas`/`config`/`writer`) beyond: dedup extraction, token/semantic consistency already in flight, envelope/prefix changes required by C5, and the missing `/review` page decision. Do NOT redesign their UX.
- **No new LLM providers.** Wire existing registry only. Do NOT add Azure/Bedrock/Mistral/etc.
- **No i18n / no real user accounts / no deployment infra** (Docker/k8s/CD).
- **No changes to the 13 dirty-worktree files beyond integrating/committing them safely** (Wave 0). Do NOT silently overwrite the user's in-flight edits.
- **No behavior change to the 108 existing tests' assertions** unless a test asserts the buggy behavior being fixed (then update the test with a clear commit message). Keep `pytest tests/` green at every wave.
- **No scope creep into vector search / RAG / embeddings** — `search_any` stays ILIKE, just project-scoped.
- **No prompt-content rewrite of the 4 agent system prompts** beyond what C1/C2/C3 strictly require (e.g. adding review-findings to the rewriter context). Do NOT "improve the writing" of prompts.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- **Test decision:** TDD where a clean unit boundary exists (agent loop, blackboard, SSE parser, store reducer, consistency tools); tests-after for integration/wiring changes (router prefix moves, lifespan, dead-code deletion). Frameworks: `pytest`+`pytest-asyncio` (backend, already in `pyproject.toml`); `vitest`+`@testing-library/react` (frontend, added in C6).
- **Backend gate (every wave):** `cd /home/sihan/文档/Projects/AI-Novel-Generation && .venv/bin/python -m pytest tests/ -x -q` MUST be green. After C6 adds coverage: `pytest tests/ --cov=app --cov-fail-under=70`.
- **Frontend gate (every wave that touches `novel-frontend/`):** `cd /home/sihan/文档/Projects/AI-Novel-Generation/novel-frontend && npm run lint && npm run build` MUST pass. After C6: `npm run test -- --run` (vitest) green.
- **Lint gates (after C6 config lands):** `ruff check app tests` and `mypy app` and `npx biome check novel-frontend/src` clean (warnings allowed, errors blocked).
- **Type gate:** `cd novel-frontend && npx tsc --noEmit` clean after any TS change.
- **Manual QA gate (F3):** spin both servers via `./dev.sh`, drive the agent chat through: (a) brainstorm turn with `/brainstorm`, (b) writing request with a chapter selected + autonomy preset, (c) confirm a `propose_setting` suggestion, (d) cancel mid-run, (e) refresh mid-stream → resume. Capture screenshots under `.omo/evidence/`.
- **Evidence:** every todo writes its proof to `.omo/evidence/task-<N>-agent-and-project-optimization.<ext>` (pytest log, vitest log, screenshot, curl SSE transcript, or `git diff --stat`).
- **No human-intervention verification at any todo.** Every acceptance criterion is a command or assertion an agent runs.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means under-splitting.

Agent-first sequencing per user emphasis. **Wave 0** is a prerequisite hygiene step. **Waves 1-3** are the Agent core (C1-C3) and MUST complete before Wave 4 (frontend) touches the agent UI, because the frontend restructure depends on the new SSE event schema from C1/C2. **Wave 5** (cross-cutting cleanup) can start in parallel with Wave 4 on backend-only todos. **Wave 6** (tests + CI) runs last but each earlier wave ships its own tests (Implementation + Test = ONE todo).

- **Wave 0 — Prerequisite (1 todo):** dirty-worktree hygiene.
- **Wave 1 — C1 Agent core (5 todos):** native tool-use adapters, run_agent rewrite, per-task session + SQLite, model-from-config + record_usage, agent-loop tests.
- **Wave 2 — C2 Orchestrator/blackboard (6 todos):** blackboard context, effective rewrite loop, real confirm, cancel, mid-run persistence+resume, multi-chapter milestone.
- **Wave 3 — C3 Tool substance (5 todos):** consistency checks, conflict detect/resolve, project-scoped search + register list_pending, snapshot rollback endpoint, record_usage across all sites.
- **Wave 4 — C4 Frontend Agent UI/UX (7 todos):** structured SSE, streaming render + panels, cancel/reconnect, mode/chapter/autonomy selector, suggestions/state/history, markdown+a11y, writer↔agent bridge.
- **Wave 5 — C5 Cross-cutting cleanup (6 todos):** delete dead code, unify API prefix+envelope, lifespan+logging, config-driven model+mask key, frontend dedup+route SSE+review-page, pydantic/datetime/schema fixes.
- **Wave 6 — C6 Test + quality hardening (6 todos):** run_agent missing branches, orchestrator missing transitions, SSE e2e, service+tool unit tests, vitest frontend, CI+ruff+mypy+biome+pre-commit+cov.
- **Final verification wave (4 todos):** F1-F4 in parallel.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 0-T1 dirty worktree | — | W1 all | — |
| 1-T1 native tool-use adapters | 0-T1 | 1-T2 | — |
| 1-T2 run_agent rewrite (native+fallback+stream+confirm) | 1-T1 | 2-T1..2-T6, 3-T1, 4-T1 | — |
| 1-T3 per-task session + SQLite WAL | 0-T1 | 2-T5, 3-T4 | 1-T1 |
| 1-T4 model-from-config + record_usage in agent loop | 1-T1 | 5-T4 | 1-T3 |
| 1-T5 agent-loop tests (new branches) | 1-T2 | 6-T1 (refines) | 1-T4 |
| 2-T1 blackboard context completeness | 1-T2 | 2-T2 | 2-T4, 2-T6 |
| 2-T2 effective review→rewrite loop | 2-T1 | 6-T2 | 2-T3, 2-T4 |
| 2-T3 real human-in-the-loop confirm | 1-T2 | 4-T5 | 2-T1, 2-T2 |
| 2-T4 cancellation | 1-T2 | 4-T3 | 2-T1, 2-T2, 2-T3 |
| 2-T5 mid-run persistence + resume | 1-T3, 2-T1 | 4-T3 | 2-T4 |
| 2-T6 multi-chapter milestone loop | 2-T1 | 6-T2 | 2-T5 |
| 3-T1 consistency checks (LLM-assisted) | 1-T2 | 6-T4 | 3-T2, 3-T3 |
| 3-T2 conflict detect/resolve | 1-T2 | 6-T4 | 3-T1, 3-T3 |
| 3-T3 project-scoped search + register list_pending | 1-T2 | — | 3-T1, 3-T2, 3-T4 |
| 3-T4 snapshot rollback endpoint + record_usage agent | 1-T3, 1-T4 | — | 3-T3 |
| 3-T5 record_usage across all LLM sites | 1-T4 | 5-T4 | 3-T4 |
| 4-T1 structured SSE event handling (frontend) | 1-T2, 2-T1, **5-T2** | 4-T2..4-T7 | — |
| 4-T2 streaming render + reasoning/toolcall panels | 4-T1 | — | 4-T3, 4-T6 |
| 4-T3 cancel + reconnect/resume | 2-T4, 2-T5, 4-T1 | — | 4-T2, 4-T6 |
| 4-T4 mode/chapter/autonomy selector | 4-T1 | — | 4-T2, 4-T3, 4-T5 |
| 4-T5 suggestions/state/history UI | 2-T3, 4-T1 | — | 4-T4, 4-T6 |
| 4-T6 markdown + a11y | 4-T1 | — | 4-T2..4-T5 |
| 4-T7 writer↔agent bridge | 4-T4 | — | 4-T5, 4-T6 |
| 5-T1 delete dead code | 0-T1 | 5-T2, 5-T3 | 4-T1, W3 |
| 5-T2 unify API prefix + envelope | 5-T1 | 4-T1 (frontend SSE route) | 5-T3 |
| 5-T3 lifespan + logging | 5-T1 | — | 5-T2, 5-T4 |
| 5-T4 config-driven model + mask key | 1-T4, 3-T5, 5-T1 | — | 5-T3 |
| 5-T5 frontend dedup + route SSE + review-page | 5-T2 | — | 5-T3, 5-T4 |
| 5-T6 pydantic v2 + datetime UTC + model_rebuild | 0-T1 | — | 5-T1..5-T5 |
| 6-T1 run_agent missing branches (refine/expansion) | 1-T5 | F1-F4 | 6-T2..6-T6 |
| 6-T2 orchestrator missing transitions | 1-T5, 2-T6 | F1-F4 | 6-T1, 6-T3..6-T6 |
| 6-T3 SSE e2e tests | 2-T5, 5-T2 | F1-F4 | 6-T1, 6-T2, 6-T4..6-T6 |
| 6-T4 service + tool unit tests | 3-T1, 3-T2 | F1-F4 | 6-T1..6-T3, 6-T5, 6-T6 |
| 6-T5 vitest frontend | 4-T1, 4-T2 | F1-F4 | 6-T1..6-T4, 6-T6 |
| 6-T6 CI + ruff + mypy + biome + pre-commit + cov | 5-T1..5-T6 | F1-F4 | 6-T1..6-T5 |
| F1 plan compliance audit | ALL todos | — | F2, F3, F4 |
| F2 code quality review | ALL todos | — | F1, F3, F4 |
| F3 real manual QA | ALL todos | — | F1, F2, F4 |
| F4 scope fidelity | ALL todos | — | F1, F2, F3 |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->

### Wave 0 — Prerequisite

- [x] 1. Wave 0: dirty-worktree hygiene — review, integrate, and safely commit/stash the 13 modified files before any Wave 1 work
  What to do / Must NOT do: Run `git -C /home/sihan/文档/Projects/AI-Novel-Generation status --short` and `git diff` to enumerate the 13 modified files (`app/llm/adapter.py`, `app/llm/provider_registry.py`, `app/main.py`, `app/routers/config.py`, `novel-frontend/src/app/config/page.tsx`, `novel-frontend/src/app/page.tsx`, `novel-frontend/src/app/projects/[id]/outline/page.tsx`, `novel-frontend/src/app/projects/[id]/page.tsx`, `novel-frontend/src/app/projects/[id]/settings/page.tsx`, `novel-frontend/src/app/projects/page.tsx`, `novel-frontend/src/hooks/use-sse.ts`, `novel-frontend/src/lib/queries/config.ts`, `pyproject.toml`). Read each diff; classify each as (a) safe to commit as-is (then stage + commit with a clear message), (b) WIP to stash on a named branch for later, or (c) conflicts with this plan's later waves (stash + flag in `.omo/evidence/task-1-...md`). Must NOT silently overwrite, `git checkout` away, or `--reset` any user edit. Must NOT amend or force-push.
  Parallelization: Wave 0 | Blocked by: — | Blocks: ALL Wave 1+
  References (executor has NO interview context): `git status --short` output captured at plan time (13 files listed above); ulw-plan skill `dirty_worktree` invariant; `.omo/drafts/agent-and-project-optimization.md` "dirty_worktree risk" line.
  Acceptance criteria (agent-executable): `git -C /home/sihan/文档/Projects/AI-Novel-Generation status --short` shows ONLY files this plan's waves create (no leftover user WIP); `.venv/bin/python -m pytest tests/ -x -q` green; a file `.omo/evidence/task-1-agent-and-project-optimization.md` exists listing each of the 13 files and its disposition (committed/stashed/flagged) with the commit SHA or stash@{N}.
  QA scenarios (name the exact tool + invocation): happy — `pytest tests/ -x -q` returns 108 passed; failure — simulate by `git status` still showing a user file → the todo is NOT complete until disposition recorded. Evidence `.omo/evidence/task-1-agent-and-project-optimization.md`.
  Commit: Y | chore(wave0): integrate in-flight dirty-worktree edits before agent overhaul

### Wave 1 — C1 Agent core

- [x] 2. Wave 1-T1: native tool-use API in LLM adapters (Claude `tools=`+`tool_use` blocks; OpenAI `tools=`+`tool_calls`) + capability flag + JSON-fallback shim + stream usage capture
  What to do / Must NOT do: **Define `LLMToolParseError(Exception)` in a new `app/llm/exceptions.py`** (raised when a `tool_use` block is malformed — missing `input`/`name`). Add `supports_native_tools: bool` (default `False`; `True` only on `ClaudeAdapter` and `OpenAIAdapter`) and `async def generate_with_tools(messages, tools: list[dict], *, temperature, max_tokens, stream_callback: Callable[[str], None] | None) -> ToolUseResponse` to `LLMAdapter` ABC (`app/llm/adapter.py:11-22`). `ToolUseResponse` (dataclass in `adapter.py`) carries `content: str`, `tool_calls: list[dict]` (each `{"name":str,"args":dict}`), `finish_reason: str`, `usage: dict`. Implement in `ClaudeAdapter` (`app/llm/claude_adapter.py`) using `client.messages.create(tools=[...], tool_choice="auto")` and parsing `block.type=="tool_use"` blocks (raise `LLMToolParseError` if `block.input`/`block.name` missing); in `OpenAIAdapter` (`app/llm/openai_adapter.py`) using `chat.completions.create(tools=[...])` and `response.choices[0].message.tool_calls`. For stream usage capture: in `generate_stream`, **Claude** — after the `async with` stream, call `await stream.get_final_message()` and read `.usage`; **OpenAI** — pass `stream_options={"include_usage": True}` to the create call and aggregate `chunk.usage` from the final chunk. `ollama`/`gemini`/`deepseek`/`custom` aliases reuse `OpenAIAdapter`'s capability flag (set `supports_native_tools=True` since they're OpenAI-compat, but document that local models may fall back to JSON mode if the model doesn't support tools — the `run_agent` fallback in todo 3 handles this by catching `LLMToolParseError`/`NotImplementedError`). `count_tokens` left as-is (out of scope per Must NOT have: no new tokenizer dep). Must NOT remove the existing `generate`/`generate_stream` text methods (`outline_gen_service` still uses `generate_stream`; `brainstorm_service` is deleted in 5-T1 but that's after Wave 1). Must NOT change `get_adapter` factory signature. **Add a regression test in this todo** asserting `generate(messages)` and `generate_stream(messages)` still work unchanged on both adapters (mock the SDK clients).
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 3 (run_agent rewrite) | Can parallelize with: 4 (per-task session)
  References (executor has NO interview context): A1 (`base.py:66-73,106-117`; `claude_adapter.py:15-23` no `tools=`; `openai_adapter.py:17-26` no `tools=`); A14 (`base.py:201-208`); A20 (streaming never surfaces usage); `app/llm/provider_registry.py:20-59` (6 providers); `pyproject.toml:26-27` (`anthropic>=0.39.0`, `openai>=1.30.0` — both support `tools=`); Anthropic SDK `tools`/`tool_use` block docs; OpenAI SDK `tools`/`tool_calls` + `stream_options.include_usage` docs.
  Acceptance criteria (agent-executable): `.venv/bin/python -m pytest tests/test_agent_base.py tests/test_adapter_records.py -x -q` green (existing); **new `tests/test_llm_adapter_tooluse.py` in THIS todo** with: (a) mock `AsyncAnthropic` returns `[{type:"tool_use", name:"lookup_settings", input:{keywords:["x"]}}]` → `generate_with_tools` returns `tool_calls=[{"name":"lookup_settings","args":{"keywords":["x"]}}]`; (b) mock returns `tool_use` block missing `input` → raises `LLMToolParseError`; (c) mock `AsyncOpenAI` returns `message.tool_calls=[{function:{name:"f",arguments:'{"a":1}'}}]` → parsed; (d) **regression**: `generate(messages)` + `generate_stream(messages)` still return text (mock both SDK clients); (e) stream usage: mock `AsyncAnthropic` stream's `get_final_message()` returns `.usage` → `generate_stream` surfaces it (assert via a `usage_callback` or by having `generate_stream` return a final usage dict — pick one and document). `ruff check app/llm` clean.
  QA scenarios (name the exact tool + invocation): happy — mock Anthropic returns valid `tool_use` → `tool_calls` parsed; failure — mock returns `tool_use` missing `input` → `LLMToolParseError` raised (not a generic Exception). Evidence `.omo/evidence/task-2-agent-and-project-optimization.log`.
  Commit: Y | feat(llm): native tool-use API + LLMToolParseError + stream usage capture with capability flag

- [x] 3. Wave 1-T2: rewrite `run_agent` to use native tool-use (capable) or JSON-fallback shim (incapable); stream `text_delta` events; structured `tool_call`/`tool_result`; wire `confirm_before` via `asyncio.Event`
  What to do / Must NOT do: In `app/agents/base.py:run_agent` (line 53-189), branch on `adapter.supports_native_tools`. If true: call `generate_with_tools(messages, tools=[{"name":t.name,"description":t.description,"parameters":t.parameters} for t in config.tools], temperature=..., max_tokens=..., stream_callback=lambda chunk: blackboard.emit_event({"type":"text_delta","content":chunk,"sequence":step_num}))`, then for each `tool_call` in the response: look up the tool by name, execute `tool.handler(**tool_call["args"])`. If false (or if `generate_with_tools` raises `LLMToolParseError`/`NotImplementedError`): fall back to the current JSON-parsing loop (unchanged). For `confirm_before`: **store `_confirm_events: dict[str, asyncio.Event]` as a Blackboard attribute** (add to `app/agents/blackboard.py` `__init__`); before executing a tool with `tool.confirm_before=True`, generate a `confirm_id=f"{tool.name}-{step_num}-{uuid4().hex[:8]}"`, create `event = asyncio.Event()`, store `blackboard._confirm_events[confirm_id] = event`, emit `{"type":"confirm_request","id":confirm_id,"tool":tool.name,"args":args,"summary":t.description}`, then `await event.wait()` (the router's `/chat/confirm` sets the event — see 2-T3). On timeout (use `asyncio.wait_for(event.wait(), timeout=autonomy_config.confirm_timeout_s)`), apply `autonomy_config.timeout_action`: `skip`→continue without the tool, `abort_task`→return `AgentRunResult(status="cancelled")`, `downgrade_and_continue`→execute the tool anyway in suggest mode. Keep `handoff`/`finish` actions. Keep `max_steps`/`token_budget`/`llm_unavailable`/`malformed_response` retry (lines 80-117 unchanged for the fallback path). Must NOT break the 6 existing `test_agent_base.py` happy-path tests — they use `FakeAdapter` without `supports_native_tools`, so they exercise the JSON fallback (keep that path). Must NOT change `AgentRunResult` shape. Must NOT remove the `text_delta` event for the fallback path (the fallback doesn't stream tokens — that's acceptable; only the native path streams).
  Parallelization: Wave 1 | Blocked by: 2 | Blocks: 2-T1..2-T6, 3-T1, 4-T1
  References (executor has NO interview context): A1, B5 (`base.py` no `confirm_before` check), `base.py:53-208` (full loop — `run_agent` starts L53, tool execution at L137-169, max-steps post-loop at L177-189, RETRY_POLICY at L201-208), `base.py:23` (`Tool.confirm_before: bool = False`), `autonomy.py:11-14` (`confirm_timeout_s: int = 300`, `timeout_action: str = "downgrade_and_continue"` — both currently unused), `blackboard.py:49-76` (`__init__` — add `_confirm_events` here).
  Acceptance criteria (agent-executable): `pytest tests/test_agent_base.py tests/test_orchestrator.py tests/test_brainstorm_agent.py -x -q` green (existing 6+14+7 tests — they exercise the JSON fallback); new `tests/test_run_agent_native_tooluse.py` added in THIS todo: (a) FakeAdapter with `supports_native_tools=True` returns a `ToolUseResponse` with one `tool_call` → tool executed + `finish` → `status="completed"`; (b) `confirm_before=True` tool → `confirm_request` event emitted to `blackboard.events` + `blackboard._confirm_events` has the `confirm_id` + `await event.wait()` suspends (prove suspension: in the test, use `asyncio.wait_for(run_agent(...), timeout=0.1)` which raises `TimeoutError` because the event is never set — then set the event and re-run to completion); (c) confirm timeout + `timeout_action="skip"` → tool skipped, loop continues to `finish`; (d) confirm timeout + `timeout_action="abort_task"` → `status="cancelled"`; (e) streaming: `stream_callback` receives `text_delta` chunks and they land on `blackboard.events` as `{"type":"text_delta",...}`; (f) native path returns a tool name not in `config.tools` → corrective system message appended + retry (mirror JSON-path behavior); (g) native path raises `LLMToolParseError` → falls back to JSON loop.
  QA scenarios (name the exact tool + invocation): happy — native tool-use path completes 2 tools + finish, `text_delta` events emitted; failure — `LLMToolParseError` → fallback to JSON loop (assert the fallback path ran via a mock counter). Evidence `.omo/evidence/task-3-agent-and-project-optimization.log`.
  Commit: Y | feat(agent): native tool-use loop + streaming + real confirm_before suspension with asyncio.Event

- [x] 4. Wave 1-T3: per-task DB `Session` for orchestrator + SQLite WAL/busy_timeout/pool_pre_ping (fix use-after-close)
  What to do / Must NOT do: In `app/routers/agent.py:chat_stream`, give the orchestrator its own `SessionLocal()` (owned by `Orchestrator`, closed in a `finally`), NOT the request-scoped `db` from `Depends(get_db)`. The SSE generator keeps the request `db` for `AgentMessage` persistence only. In `app/database.py:6-10`, add `connect_args={"check_same_thread": False, "timeout": 30}`, and run `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=30000;` via a `@event.listens_for(engine, "connect")` listener. Add `pool_pre_ping=True` to `create_engine`. Must NOT switch to async engine (Must NOT have: no async-SQLAlchemy). Must NOT change `get_db` (routers keep using it).
  Parallelization: Wave 1 | Blocked by: 1 | Blocks: 2-T5, 3-T4 | Can parallelize with: 2, 5
  References: A3, A12 (`agent.py:336` use-after-close), A13 (no WAL/busy_timeout), `database.py:6-10`, `agent.py:227,335-358`.
  Acceptance criteria: `pytest tests/ -x -q` green (108 tests); new `tests/test_orchestrator_session_isolation.py`: two orchestrators run concurrently on the same project via `asyncio.gather` → no `OperationalError: database is locked`; a test that closes the request `db` mid-orchestrator-run and asserts the orchestrator still writes (proving independent session). `PRAGMA journal_mode` query returns `wal`.
  QA scenarios: happy — concurrent orchestrators complete; failure — remove the WAL listener → test fails with `database is locked` (proves the fix is load-bearing). Evidence `.omo/evidence/task-4-agent-and-project-optimization.log`.
  Commit: Y | fix(db): per-task orchestrator session + SQLite WAL/busy_timeout (fix use-after-close)

- [x] 5. Wave 1-T4: model-from-config in agent configs + `record_usage` in agent loop (scenario + duration_ms)
  What to do / Must NOT do: In `app/agents/agents/{writer,reviewer,settings_mgr,brainstorm}.py`, **drop the `model=` argument entirely** from all 4 `build_*_config` calls (`writer.py:81`, `reviewer.py:51`, `settings_mgr.py:50`, `brainstorm.py:53`) — `AgentConfig.model` becomes a dead field; leave it on the dataclass with a default `""` for backward compat but do NOT set it in the builders. `run_agent` does NOT pass `config.model` to the adapter — the adapter's model comes from `get_adapter`/`ConfigService` (single source of truth). In `run_agent`, after each `adapter.generate`/`generate_with_tools`, call `record_usage(db, adapter.model, response.usage, scenario=f"agent_{agent_type}", duration_ms=measured, project_id=blackboard.project_id)` — requires `db` and `agent_type` accessible in `run_agent` (add `agent_type: str` param to `run_agent` and thread it through the orchestrator's `_run_*` calls; `db` comes from the per-task session established in todo 4). Wrap the `record_usage` call in `try/except Exception as e: logger.warning(...)` so an accounting failure never crashes the agent loop. Must NOT introduce a new `ConfigService` call per turn (read once via `get_adapter` at orchestrator construction). Must NOT remove `AgentConfig.model` from the dataclass (keep default `""` for backward compat with tests that construct `AgentConfig` directly).
  Parallelization: Wave 1 | Blocked by: 2 | Blocks: 5-T4 | Can parallelize with: 4
  References: A4 (`writer.py:81` etc + `base.py:89` drops model), B11 (agent loop never records), A20 (`record_usage` only at 3 sites), `adapter.py:74-93`.
  Acceptance criteria: `pytest tests/test_agent_base.py tests/test_adapter_records.py -x -q` green; new `tests/test_agent_record_usage.py`: (a) run a FakeAdapter agent loop → an `AICall` row exists with `scenario="agent_writer"`, `project_id` set, `duration_ms > 0`, `input_tokens + output_tokens > 0`; (b) **failure**: monkeypatch `record_usage` to raise → loop continues to `finish` (`status="completed"`) and `caplog` captures a WARNING. `grep -n "model=" app/agents/agents/*.py` returns 0 matches in the 4 `build_*_config` bodies.
  QA scenarios: happy — `AICall` row written per turn; failure — `record_usage` raises (e.g. `db` is None) → loop must NOT crash, must log warning + continue (agent result unaffected). Evidence `.omo/evidence/task-5-agent-and-project-optimization.log`.
  Commit: Y | feat(agent): config-driven model + per-turn AI call recording

- [x] 6. Wave 1-T5: agent-loop tests for new branches (native tool-use, confirm suspend/resume/timeout, streaming) — expansion of `test_agent_base.py`
  What to do / Must NOT do: Add to `tests/test_agent_base.py` (or a new `test_run_agent_native_tooluse.py`): native-tool-use happy path, native-tool-use unknown-tool-name corrective path, `confirm_before` suspend→resume, `confirm_before` timeout with `timeout_action="skip"`, `confirm_before` timeout with `timeout_action="abort_task"`, `text_delta` event emission assertion. Use `FakeAdapter` subclass with `supports_native_tools=True` returning canned `ToolUseResponse`. Must NOT delete the existing 6 JSON-fallback tests (they lock the shim behavior for ollama/local).
  Parallelization: Wave 1 | Blocked by: 3 | Blocks: 6-T1 (refines) | Can parallelize with: 5
  References: T6 (6 of ~14 branches covered — add the new native branches), `test_agent_base.py:102-248`.
  Acceptance criteria: `pytest tests/test_agent_base.py -x -q` green with ≥6 new tests; `pytest --collect-only tests/test_agent_base.py` shows the new test ids.
  QA scenarios: happy — all new tests pass; failure — flip `supports_native_tools` default to True without implementing → new tests fail (proves they're load-bearing). Evidence `.omo/evidence/task-6-agent-and-project-optimization.log`.
  Commit: Y | test(agent): cover native tool-use, confirm suspend/resume/timeout, streaming branches

### Wave 2 — C2 Orchestrator/blackboard logic

- [x] 7. Wave 2-T1: blackboard context completeness + wire outline/style/review/draft/round into `get_context_for`
  What to do / Must NOT do: In `app/agents/blackboard.py:get_context_for` (lines 84-110), append sections for `last_review` (overall_score + findings summary), `current_draft` (last N chars), `pending_setting_changes` (list), `rewrite_round` ("第N轮重写"), `current_chapter_id`. In `app/agents/orchestrator.py:_gathering_context` (lines 57-75), actually populate `_outline_context` and `_style_context` (currently set to `""` at line 67) by calling `OutlineService.get_tree` serialized and `StyleService`/`ProjectStyleLink` (mirror `tools/writing.py:get_outline_context` and `get_style_guide`). Must NOT change `to_snapshot`/`from_snapshot` shape without a migration note (the snapshot is Text JSON, additive fields are safe).
  Parallelization: Wave 2 | Blocked by: 3 | Blocks: 2-T2 | Can parallelize with: 2-T3, 2-T4, 2-T6
  References: B1 (`orchestrator.py:67-70` outline/style = `""`), B3 (`blackboard.py:84-110` omits last_review/draft/pending/round), `blackboard.py:78-82` `set_project_context`.
  Acceptance criteria: `pytest tests/test_blackboard.py -x -q` green + new test asserting `get_context_for("writer")` contains `last_review`, `current_draft`, `pending_setting_changes`, `rewrite_round` substrings when those fields are set; new test asserting `_gathering_context` with a real (in-memory) project+outline+style populates `_outline_context` non-empty.
  QA scenarios: happy — writer agent's system context shows the outline + style + review; failure — empty project → sections simply absent (no crash). Evidence `.omo/evidence/task-7-agent-and-project-optimization.log`.
  Commit: Y | feat(blackboard): complete cross-agent context + wire outline/style in gathering

- [x] 8. Wave 2-T2: effective review→rewrite loop (feed review findings into rewriter context; distinct rewriter mode)
  What to do / Must NOT do: In `app/agents/orchestrator.py:_run_rewriter` (line 125-126, currently just `return await self._run_writer()`), call a distinct `build_writer_config(..., rewrite_mode=True, review_findings=self.blackboard.last_review)` OR set a `blackboard.is_rewrite=True` flag that `get_context_for` surfaces so the writer prompt sees the review. Update `app/agents/prompts/writer_system.txt` ONLY to add a conditional instruction block for the rewrite case (e.g. "如果是重写，请针对审阅发现的问题重点修正"). Must NOT rewrite the whole prompt (Must NOT have: no prompt-content rewrite beyond what C2 requires).
  Parallelization: Wave 2 | Blocked by: 7 | Blocks: 6-T2 | Can parallelize with: 2-T3, 2-T4
  References: B2 (`orchestrator.py:125-126` rewriter calls writer with no review feedback; `blackboard.py:84-110` last_review not in context).
  Acceptance criteria: `pytest tests/test_orchestrator.py -x -q` green; new test: `test_rewriter_includes_review_findings` — set `blackboard.last_review={"overall_score":2.0,"findings":["x"]}`, run `_run_rewriter` with a FakeAdapter that echoes its messages → assert the assistant message contains the findings text.
  QA scenarios: happy — rewriter's LLM input includes the review; failure — `last_review=None` → rewrite proceeds without the section (no crash). Evidence `.omo/evidence/task-8-agent-and-project-optimization.log`.
  Commit: Y | feat(orchestrator): feed review findings into rewrite loop

- [x] 9. Wave 2-T3: real human-in-the-loop confirm (`confirm_request` event → suspend → `/chat/confirm` resumes)
  What to do / Must NOT do: The `confirm_before` suspension lands in `run_agent` (todo 3). In `app/routers/agent.py`, store pending `asyncio.Event`s on the blackboard (or a router-level `_pending_confirms: dict[str, asyncio.Event]`). `/chat/confirm` (`agent.py:390-416`) must look up the event by `confirm_id`, apply the action (`approve`→set event; `reject`→set a `cancelled` flag then set event; `modify`→store modification in blackboard then set event), and persist a `confirm_response` `AgentMessage` with a real `sequence` (not 999). Add `GET /api/agent/pending-confirms` (or extend `/pending-actions`) to list active confirms. Must NOT leave `WAITING_USER` as a dead-end — the orchestrator must be resumable.
  Parallelization: Wave 2 | Blocked by: 3 | Blocks: 4-T5 | Can parallelize with: 2-T1, 2-T2
  References: B5 (`base.py` no confirm check; `agent.py:390-431` confirm writes unconsumed msg; `orchestrator.py:112` WAITING_USER), B8 (sequence=999 collision).
  Acceptance criteria: `pytest tests/test_agent_router.py -x -q` green + new `tests/test_confirm_flow.py`: POST `/chat/stream` triggers a `confirm_before` tool → SSE emits `event: confirm_request` → POST `/chat/confirm` with `approve` → stream resumes and emits `tool_result` then `done`; `reject` → stream emits `cancelled` then `done`.
  QA scenarios: happy — approve path completes the tool; failure — confirm with unknown `confirm_id` → 404 + the original stream unaffected. Evidence `.omo/evidence/task-9-agent-and-project-optimization.log`.
  Commit: Y | feat(agent): real human-in-the-loop confirm with resumable suspension

- [x] 10. Wave 2-T4: cancellation (`/chat/cancel` + `CancellationToken` in orchestrator)
  What to do / Must NOT do: Add `POST /api/project/{project_id}/agent/chat/cancel` to `app/routers/agent.py` that sets a `CancellationToken` (stored alongside the per-project lock / blackboard). `Orchestrator.run` checks the token between states (and `run_agent` checks between steps); on cancel, emit `{"type":"cancelled"}`, set `AgentTask.status="cancelled"`, `completed_at`, `orchestrator_state="CANCELLED"`, and exit cleanly. Must NOT kill the asyncio task abruptly (orphaned DB writes); must drain the event queue first.
  Parallelization: Wave 2 | Blocked by: 3 | Blocks: 4-T3 | Can parallelize with: 2-T1, 2-T2, 2-T3
  References: C5 (no cancel/stop), `orchestrator.py:35-55` loop, `agent.py:17-22` per-project lock map (reuse for token map).
  Acceptance criteria: `pytest tests/test_agent_router.py -x -q` green + new `tests/test_cancel.py`: start a stream, POST `/chat/cancel` mid-run → stream emits `event: cancelled` + `event: done`; `AgentTask.status=="cancelled"` in DB.
  QA scenarios: happy — cancel mid-writing; failure — cancel a non-running task → 404 or 200 with `status:"no_active_task"`. Evidence `.omo/evidence/task-10-agent-and-project-optimization.log`.
  Commit: Y | feat(agent): cancellation endpoint + orchestrator cancellation token

- [x] 11. Wave 2-T5: mid-run persistence + real resume-from-snapshot (replace always-fail `_recover_agent_tasks`)
  What to do / Must NOT do: In `app/routers/agent.py` SSE loop, snapshot `blackboard.to_snapshot()` to `AgentTask.blackboard_snapshot` on every orchestrator state transition and every 5 events (not just at the end, `agent.py:367-380`). **Extend `Blackboard.from_snapshot` (`blackboard.py:141-159`) to also restore `_project_meta`, `_settings_context`, `_outline_context`, `_style_context`** — add these 4 fields to `to_snapshot()` output (lines 123-139) and rehydrate them in `from_snapshot()` via a `set_project_context(meta=..., settings=..., outline=..., style=...)` call (so a resumed blackboard has valid context without re-running `_gathering_context`). In `app/main.py:_recover_agent_tasks` (lines 78-110), for `running` tasks with a valid snapshot: if resumable (state not DONE/CANCELLED), mark `waiting_user` and emit a `resume_available` event on next connect; else mark `failed`. Add per-task `try/except` so one bad row doesn't abort recovery. On the frontend reconnect path (`resume_from`), reconstruct the blackboard from the snapshot and offer resume — **must NOT auto-resume without user consent** (token cost): the recovered task stays `waiting_user` until the user explicitly clicks "继续". Must NOT change the `to_snapshot`/`from_snapshot` public signature (additive fields only).
  Parallelization: Wave 2 | Blocked by: 4, 7 | Blocks: 4-T3 | Can parallelize with: 2-T4, 2-T6
  References: A9 (no mid-run persistence), A22 (`_recover_agent_tasks` no try/except), `blackboard.py:123-159` (to_snapshot/from_snapshot already exist), `agent.py:367-380`.
  Acceptance criteria: `pytest tests/ -x -q` green + new `tests/test_resume.py`: (a) seed `AgentTask(status="running", blackboard_snapshot=<json with _settings_context/_outline_context/_style_context>, orchestrator_state="WRITING")`, call `_recover_agent_tasks`, assert `status=="waiting_user"` (resumable, NOT auto-resumed); (b) **negative**: assert no task transitions to `status="running"` on restart (auto-resume forbidden); (c) `orchestrator_state="DONE"` + snapshot → `failed`; (d) `blackboard_snapshot="{invalid"` → row skipped (try/except), `caplog` WARNING; (e) `Blackboard.to_snapshot()` includes `_project_meta`/`_settings_context`/`_outline_context`/`_style_context`; (f) `Blackboard.from_snapshot(snapshot)` rehydrates `_settings_context` non-empty.
  QA scenarios: happy — resumable snapshot → `waiting_user`; failure — `blackboard_snapshot` is invalid JSON → row skipped, recovery continues, log entry written. Evidence `.omo/evidence/task-11-agent-and-project-optimization.log`.
  Commit: Y | feat(agent): mid-run blackboard persistence + resumable recovery

- [x] 12. Wave 2-T6: multi-chapter/volume/act milestone loop driven by `milestone_granularity`
  What to do / Must NOT do: In `app/agents/orchestrator.py:run` (or a new `_run_milestone_loop`), after a chapter completes (DONE), if `autonomy_config.milestone_granularity in ("volume","act")`, advance to the next outline node at the configured level and loop `WRITING→REVIEWING→...` until the milestone's nodes are done. Track `blackboard.milestone_progress`. Must NOT run unbounded — respect `max_rewrite_rounds` per chapter and the token budget. Must NOT change the single-chapter default behavior when `milestone_granularity=="chapter"`.
  Parallelization: Wave 2 | Blocked by: 7 | Blocks: 6-T2 | Can parallelize with: 2-T5
  References: D5 (milestone unused), `autonomy.py:8` (`milestone_granularity`), `orchestrator.py:32-55`.
  Acceptance criteria: `pytest tests/test_orchestrator.py -x -q` green + new `tests/test_milestone_loop.py`: a FakeDB with 3 chapter outlines + `milestone_granularity="volume"` → orchestrator's `_run_milestone_loop` iterates 3 chapters (assert `milestone_progress` advances 1→2→3); `milestone_granularity="chapter"` → only 1 chapter.
  QA scenarios: happy — volume milestone runs 3 chapters sequentially; failure — outline tree empty → loop exits cleanly after the first DONE (no crash). Evidence `.omo/evidence/task-12-agent-and-project-optimization.log`.
  Commit: Y | feat(orchestrator): multi-chapter milestone loop (volume/act granularity)

### Wave 3 — C3 Tool substance

- [x] 13. Wave 3-T1: real consistency checks (setting/style/logic) as LLM-assisted handlers returning structured findings
  What to do / Must NOT do: Replace the canned returns in `app/agents/tools/review.py:check_setting_consistency` (line 20-31), `check_style_consistency` (34-35), `check_logic_structure` (38-39) with handlers that assemble the chapter content + active settings + style guide + recent chapters, call `adapter.generate` (or `generate_with_tools`) with a focused review prompt (reuse `app/llm/prompts/` or add a structured one), parse the JSON findings, and return `{"dimension":"setting|style|logic","score":float,"findings":[...],"summary":str}`. Must NOT make these blocking human-review steps — they are agent-internal. Must NOT bypass `record_usage` (call it per check). Keep the existing `submit_review` aggregation.
  Parallelization: Wave 3 | Blocked by: 3 | Blocks: 6-T4 | Can parallelize with: 3-T2, 3-T3
  References: B4 (`review.py:20-39` stubs), D1 (4-dim review theatrical), A19 (`review_service.run_review` only 2/4 dims, hardcoded 3.5), `tools/review.py:42-65` `submit_review`.
  Acceptance criteria: `pytest tests/test_agent_tools.py -x -q` green + new `tests/test_consistency_tools.py`: with a FakeAdapter returning `{"score":3.5,"findings":["f1"]}`, `check_setting_consistency` returns a dict with `score` and `findings` (not "preview_ready"); an `AICall` row written per check.
  QA scenarios: happy — returns structured findings; failure — LLM returns non-JSON → handler returns `{"score":0,"findings":[],"summary":"LLM parse error"}` (no crash, no exception to the agent). Evidence `.omo/evidence/task-13-agent-and-project-optimization.log`.
  Commit: Y | feat(tools): LLM-assisted setting/style/logic consistency checks

- [x] 14. Wave 3-T2: implement `detect_conflicts` + `resolve_conflict` (persist resolution)
  What to do / Must NOT do: In `app/agents/tools/setting.py:detect_conflicts` (line 86-87, returns empty) — implement by passing the `new_setting_ids` + their content + existing settings to the LLM (or a rule-based dup-key/contradiction scan) and return `{"conflicts":[{"id","desc","severity","setting_ids"}]}`. `resolve_conflict` (line 90-91) — persist the resolution: store in `AgentTask.task_metadata["resolved_conflicts"]` (or a `SettingConflict` model if you add one — but Must NOT have: no DB migration unless additive; prefer metadata). Must NOT auto-delete settings.
  Parallelization: Wave 3 | Blocked by: 3 | Blocks: 6-T4 | Can parallelize with: 3-T1, 3-T3
  References: B4 (`setting.py:86-91` stubs), D2.
  Acceptance criteria: `pytest tests/ -x -q` green + new `tests/test_setting_conflicts.py`: `detect_conflicts` with two settings that share a `key` returns ≥1 conflict; `resolve_conflict` persists a resolution row/metadata and returns a confirmation.
  QA scenarios: happy — conflict detected + resolved; failure — no conflicts → `{"conflicts":[]}` (current behavior preserved). Evidence `.omo/evidence/task-14-agent-and-project-optimization.log`.
  Commit: Y | feat(tools): setting conflict detection + resolution persistence

- [x] 15. Wave 3-T3: project-scoped `search_any` in agent tools + register `list_pending_inspirations` as a brainstorm tool
  What to do / Must NOT do: In `app/agents/agents/{writer,reviewer,settings_mgr,brainstorm}.py`, change the `search_any` tool handlers to pass `project_id` (currently `writer.py:69-73` calls `search_any(db, q=..., type=..., limit=...)` with no `project_id` → `search_service.py:27` defaults to global). Update the handler signatures to forward `project_id`. In `app/agents/agents/brainstorm.py:build_brainstorm_config`, add a `Tool(name="list_pending_inspirations", ...)` wired to `tools/brainstorm.py:list_pending_inspirations` (currently dead, A21). Must NOT change the `SearchService.search` signature (it already accepts `project_id`).
  Parallelization: Wave 3 | Blocked by: 3 | Blocks: — | Can parallelize with: 3-T1, 3-T2, 3-T4
  References: B10 (search_any omits project_id → cross-project leak), A21 (`list_pending_inspirations` dead), `search_service.py:27,62-120`, `tools/shared.py:7-11`.
  Acceptance criteria: `pytest tests/test_agent_tools.py tests/test_brainstorm_agent.py -x -q` green + new test: two projects with distinct settings, writer agent's `search_any` only returns the current project's rows; `build_brainstorm_config` tools list includes `list_pending_inspirations`.
  QA scenarios: happy — search is project-scoped; failure — `project_id=None` (legacy) → falls back to global (backward compat, no crash). Evidence `.omo/evidence/task-15-agent-and-project-optimization.log`.
  Commit: Y | fix(tools): project-scoped search_any + register list_pending_inspirations

- [x] 16. Wave 3-T4: chapter snapshot rollback endpoint + record_usage in agent loop (final wiring)
  What to do / Must NOT do: Add `POST /api/projects/{project_id}/chapters/{chapter_id}/rollback?task_id=...` to `app/routers/chapters.py` that restores `Chapter.content`/`title` from the most recent `ChapterSnapshot` for that task (`tools/writing.py:96-104` already writes snapshots). Delete the snapshot after restore (or mark it consumed). The agent-loop `record_usage` wiring is todo 5; this todo ensures the snapshot is reachable. Must NOT expose snapshots cross-project.
  Parallelization: Wave 3 | Blocked by: 4, 5 | Blocks: — | Can parallelize with: 3-T3
  References: D6 (no rollback endpoint), `tools/writing.py:96-104`, `models/chapter_snapshot.py`.
  Acceptance criteria: `pytest tests/test_api_chapters.py -x -q` green + new `tests/test_rollback.py`: seed a chapter + snapshot, POST rollback → content reverts to snapshot; rollback with no snapshot → 404.
  QA scenarios: happy — rollback restores prior content; failure — rollback a chapter with snapshots from a different project → 404. Evidence `.omo/evidence/task-16-agent-and-project-optimization.log`.
  Commit: Y | feat(api): chapter snapshot rollback endpoint

- [x] 17. Wave 3-T5: `record_usage` across all remaining LLM call sites (style/cleaning/outline_gen/review_service)
  What to do / Must NOT do: Add `record_usage(db, adapter.model, response.usage, scenario="...", project_id=...)` to: `style_service.analyze_text` + `smart_slice` (`style_service.py:45-67`), `cleaning_service.consistency_check` (`cleaning_service.py:36-67`), `outline_gen_service` 4 stream methods (`outline_gen_service.py`), `review_service.run_review` (`review_service.py` — also fix the 2/4-dimension stub, A19, while you're there: populate all 4 dims via the LLM). For streaming methods, capture usage via the stream-final usage from todo 2. Must NOT double-record (brainstorm_service already records).
  Parallelization: Wave 3 | Blocked by: 5 | Blocks: 5-T4 | Can parallelize with: 3-T4
  References: A20 (record_usage only at 3 sites), A19 (review_service 2/4 dims + hardcoded 3.5), B11.
  Acceptance criteria: `pytest tests/ -x -q` green + new `tests/test_record_usage_all_sites.py`: drive each LLM-using service with a FakeAdapter → an `AICall` row exists per scenario (`style_analyze`, `style_slice`, `cleaning_check`, `outline_gen_*`, `review_run`); `review_service.run_review` returns 4 dimension scores (not 2 + hardcoded).
  QA scenarios: happy — every LLM call site records; failure — a service raises before `record_usage` → no row (acceptable, but log it). Evidence `.omo/evidence/task-17-agent-and-project-optimization.log`.
  Commit: Y | feat(services): record AI usage across all LLM sites + complete 4-dim review

### Wave 4 — C4 Frontend Agent UI/UX

- [x] 18. Wave 4-T1: structured SSE event handling — parse `event:` lines, structured agent store, route by type
  What to do / Must NOT do: Rewrite `novel-frontend/src/hooks/use-sse.ts` to parse both `event:` and `data:` lines (currently only `data:`, lines 65-86). Redesign `novel-frontend/src/stores/agent.ts` from a flat `messages[]` into structured slices: `messages[]` (chat bubbles only), `toolCalls[]` (per-turn, with status), `reasoning[]` (per-turn, collapsible), `suggestions[]` (pending confirm/suggestion cards), `orchestratorState`, `progress`, `taskId`. Route each event type to the right slice. Remove the dead `isConnected`/`taskId`(unused)/`updateLastMessage`(unused) fields or wire them (taskId should be set from the `agent_start` event). Must NOT lose the existing empty-state and bubble rendering.
  Parallelization: Wave 4 | Blocked by: 3, 7 | Blocks: 4-T2..4-T7 | Can parallelize with: 5-T1, 5-T5
  References: C3 (`use-sse.ts:65-86` ignores event:), C1 (flat bubbles), C2 (drops chapter_outline_id), C16 (ChatMessage redeclared), `use-sse.ts:1-117`, `stores/agent.ts:1-49`, `agent.py` event types (`agent_start`,`orchestrator_thought`,`tool_call`,`tool_result`,`text_delta`,`checkpoint`,`progress`,`confirm_request`,`pending_suggestion`,`brainstorm_response`,`task_complete`,`done`,`cancelled`).
  Acceptance criteria: `cd novel-frontend && npm run lint && npm run build` pass; `npx tsc --noEmit` clean; new `tests/agent-store.test.ts` (todo 6-T5 or here as a stub) — feed a synthetic SSE transcript (with `event:` lines) → store slices populated correctly.
  QA scenarios: happy — a 5-event transcript produces 1 message + 1 toolCall + 1 reasoning + 1 suggestion; failure — malformed `data:` line → skipped with a console.warn, no crash. Evidence `.omo/evidence/task-18-agent-and-project-optimization.png` (screenshot) + `.log`.
  Commit: Y | feat(frontend): structured SSE event routing + sliced agent store

- [x] 19. Wave 4-T2: streaming token render (in-place append) + per-turn collapsible reasoning/tool-call panels
  What to do / Must NOT do: In `use-sse.ts`, on `text_delta` events, call `updateLastAssistantMessage(chunk)` (accumulate into the current assistant bubble, not append a new bubble). In `agent/page.tsx`, render each assistant turn as: an optional collapsible "推理" panel (reasoning), a list of collapsible "工具调用" panels (toolCalls with status icon + args + result), then the markdown assistant bubble. Extract `ChatBubble` + the new panels to `novel-frontend/src/components/features/agent/{chat-bubble,reasoning-panel,tool-call-panel}.tsx` (create the `features/agent` dir). Must NOT keep the inlined 290-line page (extract).
  Parallelization: Wave 4 | Blocked by: 18 | Blocks: — | Can parallelize with: 4-T3, 4-T6
  References: C4 (no streaming render), C13 (ChatBubble inlined), C28 (unbounded messages), `agent/page.tsx:164-289`, `stores/agent.ts:34-42` `updateLastMessage`.
  Acceptance criteria: `npm run lint && npm run build` pass; manual QA (F3) shows tokens appearing in-place as they stream; `agent/page.tsx` is ≤120 lines after extraction.
  QA scenarios: happy — streaming text accumulates in one bubble; failure — `text_delta` arrives with no prior assistant message → create a new assistant bubble first (no crash). Evidence `.omo/evidence/task-19-agent-and-project-optimization.png`.
  Commit: Y | feat(frontend): streaming token render + extracted reasoning/tool-call panels

- [x] 20. Wave 4-T3: cancel/stop button via `AbortController` + reconnect/resume (pass `resume_from` / `Last-Event-ID`)
  What to do / Must NOT do: In `use-sse.ts`, add an `AbortController` per `send()`; expose a `cancel()` that calls `controller.abort()` AND POSTs to `/api/project/{id}/agent/chat/cancel` (todo 10). On reconnect (page load with an active task), GET `/api/project/{id}/agent/tasks` → if a `waiting_user`/`running` task exists, fetch `resume_from` and replay. Add a "停止" button to `agent/page.tsx` header (visible when `isStreaming`). Must NOT leave the backend task orphaned on abort (always call cancel).
  Parallelization: Wave 4 | Blocked by: 10, 11, 18 | Blocks: — | Can parallelize with: 4-T2, 4-T6
  References: C5 (no cancel), C6 (no reconnect — backend supports `resume_from`), `use-sse.ts:29-36` (no signal), `agent.py:226,231-247` (resume path), `agent.py:434-438` (`/tasks`).
  Acceptance criteria: `npm run lint && npm run build` pass; manual QA: start a stream, click 停止 → backend task `status="cancelled"`, stream closes cleanly; refresh mid-stream → history replays + a "继续" affordance appears.
  QA scenarios: happy — cancel + resume both work; failure — cancel a non-running task → 200 `no_active_task` (no UI crash). Evidence `.omo/evidence/task-20-agent-and-project-optimization.png`.
  Commit: Y | feat(frontend): stop button + reconnect/resume with AbortController

- [x] 21. Wave 4-T4: mode selector (brainstorm/writing) + chapter picker + autonomy preset UI; send full `ChatRequest`
  What to do / Must NOT do: Add a top toolbar to `agent/page.tsx` with: a mode `Select` (脑暴/写作, default auto-detect — but allow forcing), a chapter `Select` (populated from `useChapters(projectId)`, only relevant in writing mode), an autonomy popover (write_mode suggest/draft/direct, max_rewrite_rounds, milestone_granularity). Update `use-sse.ts` `send()` to accept and serialize the full `ChatRequest` (`{message, chapter_outline_id, target_words, mode, autonomy_config}`) — currently only `{message}` (C2). Must NOT remove auto-detect (keep it as a mode option).
  Parallelization: Wave 4 | Blocked by: 18 | Blocks: — | Can parallelize with: 4-T2, 4-T3, 4-T5
  References: C1 (no mode selector), C2 (drops chapter_outline_id/target_words), `agent.py:210-213` `ChatRequest`, `autonomy.py:6-19` `AutonomyConfig`, `lib/queries/chapters.ts`.
  Acceptance criteria: `npm run lint && npm run build` pass; manual QA: select chapter + draft mode + 2 rewrite rounds → POST body includes all fields; backend `_detect_intent` is skipped when `mode` is explicit.
  QA scenarios: happy — full request sent; failure — no chapters in project → chapter Select shows "（暂无章节）" disabled, send still works in brainstorm mode. Evidence `.omo/evidence/task-21-agent-and-project-optimization.png`.
  Commit: Y | feat(frontend): mode/chapter/autonomy selector + full ChatRequest

- [x] 22. Wave 4-T5: pending-suggestion cards + inspirations confirm UI + orchestrator state/progress viz + task history panel
  What to do / Must NOT do: Render `confirm_request` events as inline cards with 批准/拒绝/修改 buttons → **POST `/api/project/{project_id}/agent/chat/confirm`** with `{confirm_id, action: "approve"|"reject"|"modify", modification?}` (this resumes the suspended `asyncio.Event` from todo 3/9). Render `pending_suggestion` events (from suggest-mode `write_chapter`/`propose_setting`, `tools/writing.py:80-86` + `tools/setting.py:62-68`) as inline cards with 保存/丢弃 buttons → **POST `/api/project/{project_id}/agent/inspirations/confirm`** with `{inspiration_ids: [...]}` (`agent.py:445-506`) for inspirations, OR a new `POST /api/project/{project_id}/agent/suggestions/confirm` for write-mode suggestions (if the suggestion is a chapter draft, not an inspiration — add this endpoint if needed; otherwise reuse `/inspirations/confirm`). Add a slim orchestrator-state badge + progress bar (from `orchestratorState`/`progress` store slices). Add a collapsible "历史任务" panel (fetch `GET /api/project/{project_id}/agent/tasks`). Must NOT auto-open the history panel (default collapsed). Must NOT send a confirm POST for a card whose task is no longer `waiting_user` (guard with a stale-check).
  Parallelization: Wave 4 | Blocked by: 9, 18 | Blocks: — | Can parallelize with: 4-T4, 4-T6
  References: C7 (no suggestions UI), C8 (no state/progress viz), C9 (no task history), D4 (suggest-mode invisible), `agent.py:419-431` (`/pending-actions`), `agent.py:434-438` (`/tasks`), `agent.py:445-506` (`/inspirations/confirm`).
  Acceptance criteria: `npm run lint && npm run build` pass; manual QA: trigger a `propose_setting` in suggest mode → card appears → 批准 → setting created; orchestrator badge transitions IDLE→WRITING→REVIEWING→DONE; history panel lists past tasks.
  QA scenarios: happy — card flow + state viz + history; failure — `/inspirations/confirm` with empty selection → 200 `saved_count:0` (no crash). Evidence `.omo/evidence/task-22-agent-and-project-optimization.png`.
  Commit: Y | feat(frontend): suggestion cards + orchestrator state viz + task history

- [x] 23. Wave 4-T6: `react-markdown` + `remark-gfm` rendering for assistant content; a11y (aria-live/aria-expanded/aria-label); remove `messageType` label leak
  What to do / Must NOT do: Add `react-markdown` + `remark-gfm` to `novel-frontend/package.json` deps. Render assistant bubble content via `<ReactMarkdown remarkPlugins={[remarkGfm]} components={...}>` (the brainstorm prompt emits Markdown, `brainstorm_system.txt:27`). Remove the raw `messageType` uppercase label at `agent/page.tsx:264-271` (C12). Add `aria-live="polite"` to the message `ScrollArea`, `aria-expanded` to the reasoning/tool-call toggles, `aria-label` to the input + send + stop buttons. Must NOT allow raw HTML in markdown (no `rehype-raw` — XSS).
  Parallelization: Wave 4 | Blocked by: 18 | Blocks: — | Can parallelize with: 4-T2..4-T5
  References: C10 (no markdown), C12 (messageType leak), C17 (a11y), `agent/page.tsx:264-271,216-226`, `brainstorm_system.txt:27`.
  Acceptance criteria: `npm run lint && npm run build` pass; `npx tsc --noEmit` clean; manual QA: assistant Markdown (**bold**, lists, tables) renders correctly; axe-core (or manual) audit shows no critical a11y violations on the agent page.
  QA scenarios: happy — markdown renders + a11y clean; failure — markdown with a `<script>` tag → rendered as text (no HTML execution). Evidence `.omo/evidence/task-23-agent-and-project-optimization.png`.
  Commit: Y | feat(frontend): markdown rendering + a11y + remove messageType label leak

- [x] 24. Wave 4-T7: writer↔agent bridge — wire the dead "AI" button to open agent with chapter context; carry brainstorm handoff context
  What to do / Must NOT do: In `novel-frontend/src/app/projects/[id]/writer/page.tsx:128-131`, wire the "AI" button `onClick` to navigate to `/projects/[id]/agent?chapter={selectedId}&mode=writing` (and pre-fill the agent input with a "帮我写/改这一章" prompt). In `agent/page.tsx`, read the `chapter` + `mode` query params on mount and pre-select them in the selector (todo 21). On brainstorm→writing handoff (`brainstorm_handoff` event, `agent.py:267-272`), surface a "继续写作" affordance that switches mode to writing with the brainstorm summary as context. Must NOT auto-navigate without user click.
  Parallelization: Wave 4 | Blocked by: 21 | Blocks: — | Can parallelize with: 4-T5, 4-T6
  References: C11 (writer "AI" button no onClick), E5 (handoff abrupt), `writer/page.tsx:128-131`, `agent.py:267-272`.
  Acceptance criteria: `npm run lint && npm run build` pass; manual QA: writer "AI" click → agent page opens with chapter pre-selected; brainstorm handoff → "继续写作" button appears.
  QA scenarios: happy — bridge works both directions; failure — no chapter selected in writer → "AI" button disabled. Evidence `.omo/evidence/task-24-agent-and-project-optimization.png`.
  Commit: Y | feat(frontend): writer↔agent bridge with chapter + handoff context

### Wave 5 — C5 Cross-cutting cleanup

- [x] 25. Wave 5-T1: delete dead code (brainstorming router/service/templates, auth middleware, dead RETRY_POLICY entries, dead ContextBuilder scenarios, dead api-client auth plumbing, dead agent-store fields, dead ErrorResponse)
  What to do / Must NOT do: Delete `app/routers/brainstorming.py` (unregistered, Jinja templates path missing — A5, A11), `app/services/brainstorm_service.py` (only used by the dead router), `app/templates/brainstorm/` if present. **Verify `app/main.py:8-11` — `brainstorming` is NOT in the `from app.routers import (...)` tuple (it was never registered), so no import edit is needed; if a future edit added it, remove it.** **Remove the `@app.get("/brainstorm")` redirect at `app/main.py:58-63`** (it's a dead redirect to a removed UI; the agent page is now the entry point). Remove `app/middleware/auth.py` (decide: **remove** — Must NOT have says no real auth; a 13-line unregistered placeholder adds confusion). Remove dead `RETRY_POLICY` entries (`tool_timeout`/`rate_limited`/`db_error`/`budget_exceeded` that are never consulted — A14) — **remove** (the loop handles these inline). Remove dead `ContextBuilder` scenarios `writing`/`style_analysis`/`cleaning` (A15) from the `SCENARIOS` list (`context_builder.py:13`). Remove `api-client.ts` `NoAuthProvider`/`ApiKeyProvider`/`setAuthProvider`/`useApiKey` (C21). Remove dead agent-store fields if not wired by 4-T1 (`isConnected`/`updateLastMessage` if unused — C16). Remove `schemas/response.py:ErrorResponse` (A23). Must NOT delete `list_pending_inspirations` (wired in 3-T3). Must NOT delete `app/llm/templates/` YAML files (still used by `ContextBuilder` for `review`/`brainstorm` scenarios — only remove the dead scenario names from the `SCENARIOS` list, not the YAML files). Must NOT delete `generate_stream` (still used by `outline_gen_service`).
  Parallelization: Wave 5 | Blocked by: 1 | Blocks: 5-T2, 5-T3 | Can parallelize with: 4-T1, W3
  References: A5, A11, A14, A15, A21, A23, A25, C16, C21.
  Acceptance criteria: `pytest tests/ -x -q` green; `npm run lint && npm run build` pass; `grep -r "brainstorm_service\|routers.brainstorming\|NoAuthProvider\|ErrorResponse\|on_event" app novel-frontend/src` returns 0; `grep -n "brainstorm" app/main.py` returns 0 (the `@app.get("/brainstorm")` redirect L58-63 is gone; the import was never there); `git diff --stat` shows only deletions + the `SCENARIOS` list edit.
  QA scenarios: happy — nothing imports the deleted code; failure — an import still references a deleted symbol → test/import fails (caught before commit). Evidence `.omo/evidence/task-25-agent-and-project-optimization.log`.
  Commit: Y | chore: remove dead code (brainstorming router/service, auth placeholder, unused retry entries, dead scenarios)

- [x] 26. Wave 5-T2: unify API prefix (move agent router to `/api`) + `APIResponse` for JSON endpoints; SSE stays raw stream
  What to do / Must NOT do: Change `app/routers/agent.py:209` `prefix="/project/{project_id}/agent"` → `prefix="/api/project/{project_id}/agent"`. Wrap `confirm_action`/`pending-actions`/`tasks`/`inspirations/confirm`/`cancel` return values in `APIResponse[...]`. Leave `chat/stream` returning a raw `StreamingResponse` (SSE must not be enveloped). Update `novel-frontend/src/hooks/use-sse.ts` `BACKEND` usage to go through the Next.js `/api` rewrite (remove the direct `http://localhost:8000` bypass, C20) — add a `/api/project/:path*` rewrite to `next.config.ts` if needed (it already has `/api/:path*`). Update `novel-frontend/src/lib/queries/` if any hit these endpoints. Must NOT break the existing `test_agent_router.py` paths without updating them.
  Parallelization: Wave 5 | Blocked by: 25 | Blocks: 4-T1 (frontend SSE route) | Can parallelize with: 5-T3
  References: A6 (prefix inconsistent), A7 (envelope mixed), C20 (SSE bypasses rewrite), `agent.py:209`, `config.py:8`, `search.py:8`, `next.config.ts`.
  Acceptance criteria: `pytest tests/test_agent_router.py -x -q` green (update paths); `npm run build` pass; manual QA: agent chat works through the Next.js proxy (no `NEXT_PUBLIC_BACKEND_URL` needed).
  QA scenarios: happy — `/api/project/.../agent/chat/stream` works via proxy; failure — old `/project/.../agent/...` path → 404 (expected, documented in commit). Evidence `.omo/evidence/task-26-agent-and-project-optimization.log`.
  Commit: Y | refactor(api): unify agent router under /api + APIResponse envelope for JSON endpoints

- [x] 27. Wave 5-T3: `lifespan` context manager (replace deprecated `@app.on_event`) + structured logging across services/routers/adapters
  What to do / Must NOT do: In `app/main.py`, replace `@app.on_event("startup")` (line 66, deprecated) with `@asynccontextmanager async def lifespan(app): ...` passed to `FastAPI(lifespan=lifespan)`. Add `logging.basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")` + a `logging.getLogger("app")` used across services/routers/adapters (A27 — currently 8 log calls in 2 files). Add `logger = logging.getLogger(__name__)` + contextual logs to each service + router + adapter (at least: INFO on agent start/end, WARNING on LLM retry, ERROR on unrecoverable). Must NOT add a heavy logging framework (no structlog/loguru) — stdlib only.
  Parallelization: Wave 5 | Blocked by: 25 | Blocks: — | Can parallelize with: 5-T2, 5-T4
  References: A10 (`@app.on_event` deprecated), A22 (`_recover_agent_tasks` no try/except), A27 (logging absent), `main.py:66-75`.
  Acceptance criteria: `pytest tests/ -x -q` green; `grep -r "on_event" app` returns 0; **`grep -rn "logger\.\(info\|warning\|error\)" app | wc -l` ≥ 40** (meaningful log statements, not just `getLogger` imports — target: ≥2 log calls in each of `agents/base.py`, `agents/orchestrator.py`, `routers/agent.py`, `llm/adapter.py`, `llm/claude_adapter.py`, `llm/openai_adapter.py`, `main.py`, + ≥1 in each of the 11 services and 11 routers); manual QA: server logs show structured lines with timestamps (`logging.basicConfig` format).
  QA scenarios: happy — startup runs via lifespan, logs structured; failure — a migration raises in lifespan → lifespan aborts cleanly (app doesn't start half-initialized). Evidence `.omo/evidence/task-27-agent-and-project-optimization.log`.
  Commit: Y | refactor(app): lifespan context manager + structured stdlib logging

- [x] 28. Wave 5-T4: config-driven model fully wired + `GET /api/config` no longer returns plaintext `api_key` (mask)
  What to do / Must NOT do: Verify the model-from-config path (todo 5) is end-to-end: `ConfigService.get_all` → `get_adapter` → agent configs → `run_agent`. In `app/routers/config.py:get_config` (line 11-14), mask the `api_key` in the response (return `api_key_masked: "sk-...xxxx"` or omit it; the frontend only needs to know IF a key is set, not the value). Add a separate `GET /api/config/api-key-status` if the frontend needs a boolean. Must NOT store the key encrypted (out of scope) — just don't return it in cleartext over GET. Update `novel-frontend/src/app/config/page.tsx` to not display/rely on the returned key value.
  Parallelization: Wave 5 | Blocked by: 5, 17, 25 | Blocks: — | Can parallelize with: 5-T3
  References: A11 (key plaintext + returned by GET), `config_service.py:29-35`, `config.py:11-14`, `adapter.py:33-39`.
  Acceptance criteria: `pytest tests/test_api_config.py -x -q` green (update assertion: response `data` has no cleartext `api_key`, has `api_key_set: bool`); manual QA: config page shows "Key 已设置" not the key.
  QA scenarios: happy — key masked, model selectable; failure — `api_key` empty → `api_key_set:false`, adapter falls back to env. Evidence `.omo/evidence/task-28-agent-and-project-optimization.log`.
  Commit: Y | feat(config): mask api_key in GET + fully wire config-driven model

- [x] 29. Wave 5-T5: frontend dedup (`formatRelative`/`toneStyles`/`STATUS_BADGE` → `lib/utils`) + `config.ts` use `unwrap<T>()` + route SSE through `/api` rewrite + remove-or-wire dead `api.d.ts` + implement-or-remove `/projects/[id]/review` link
  What to do / Must NOT do: Extract `formatRelative` (duplicated in `app/page.tsx:264-277`, `projects/page.tsx:298-311`, `projects/[id]/page.tsx:241-254`) to `novel-frontend/src/lib/utils.ts` (or `lib/format.ts`). Extract `toneStyles` (2×) and `STATUS_BADGE`/`STATUS_LABEL` (2×) to shared modules. Make `lib/queries/config.ts` use `unwrap<ConfigMap>()` like the other 6 query files (C14 outlier). Remove the 4858-line `src/types/api.d.ts` OR wire it into the query hooks (preferred: remove + add a `gen:types:check` CI step that fails if regenerated types drift — todo 6-T6). Implement the `/projects/[id]/review` page OR remove its nav link (`projects/[id]/page.tsx:53-58`, C22 — decide: preferred = remove link + add a TODO issue, since review is via the agent now). Must NOT redesign the review UX (out of scope).
  Parallelization: Wave 5 | Blocked by: 26 | Blocks: — | Can parallelize with: 5-T3, 5-T4
  References: C14 (api.d.ts dead), C15 (formatRelative 3×), C20 (SSE bypass — partly 5-T2), C22 (review 404), `config.ts:14,22`.
  Acceptance criteria: `npm run lint && npm run build` pass; `grep -r "formatRelative" novel-frontend/src` returns 1 definition + N imports (not 3 definitions); `grep "from \"@/types/api\"" novel-frontend/src` returns 0 (if removed) or N (if wired); no 404 on `/projects/[id]` nav.
  QA scenarios: happy — dedup + no dead types + no 404; failure — `npm run gen:types` produces a file differing from the (removed) one → CI step (6-T6) catches. Evidence `.omo/evidence/task-29-agent-and-project-optimization.log`.
  Commit: Y | refactor(frontend): dedup helpers + unwrap envelope + remove dead types + fix review nav

- [x] 30. Wave 5-T6: Pydantic v2 `ConfigDict` in `config.py` + `datetime.now(UTC)` across models + `model_rebuild()` for outline schema forward-ref
  What to do / Must NOT do: In `app/config.py:10-11`, replace `class Config: env_file = ".env"` with `model_config = SettingsConfigDict(env_file=".env")` (A18 — fixes .env loading on pydantic-settings 2.x + removes 9 deprecation warnings). Replace `default=datetime.utcnow` with `default=lambda: datetime.now(timezone.utc)` across all 12+ models (A17 — `datetime.utcnow` deprecated in 3.12+). Call `OutlineResponse.model_rebuild()` after the forward-ref `children` declaration (`schemas/outline.py:40-41`, A25) OR restructure to avoid the forward ref. Must NOT change column types (DateTime stays). Must NOT introduce a migration (values are still datetimes).
  Parallelization: Wave 5 | Blocked by: 1 | Blocks: — | Can parallelize with: 5-T1..5-T5
  References: A17, A18, A25, T9 (266 deprecation warnings), `config.py:10-11`, `schemas/outline.py:40-41`.
  Acceptance criteria: `pytest tests/ -x -q` green with **0** Pydantic `class Config` warnings and **0** `datetime.utcnow` warnings (down from 266); `OutlineResponse` tree shape populates correctly (new test).
  QA scenarios: happy — warnings eliminated; failure — a model still uses `utcnow` → grep catches. Evidence `.omo/evidence/task-30-agent-and-project-optimization.log`.
  Commit: Y | chore: pydantic v2 ConfigDict + timezone-aware datetimes + outline schema rebuild

### Wave 6 — C6 Test + quality hardening

- [x] 31. Wave 6-T1: `run_agent` loop missing branches — 3-strike caps (malformed/hallucinated/retry), tool-handler-raises, non-string coercion, event emission, message-history growth, `_build_tool_schema_description`
  What to do / Must NOT do: Add to `tests/test_agent_base.py`: (a) 3× malformed JSON → `status="error" error_code="malformed_response"` (base.py:109-114); (b) 3× hallucinated tool → error (142-146); (c) 3× LLM raise → `error_code="llm_unavailable"` (92-97); (d) tool handler raises → `tool_result` contains "Tool execution error" + loop continues (155-156); (e) tool returns `None` → `str(None)` coerced; (f) assert `blackboard.events` queue received `tool_call`+`tool_result`+`checkpoint` (step%5) (171-175); (g) `messages` grows by 2 per tool turn; (h) `_build_tool_schema_description` renders tool name + params JSON. Must NOT weaken existing assertions.
  Parallelization: Wave 6 | Blocked by: 6 | Blocks: F1-F4 | Can parallelize with: 6-T2..6-T6
  References: T6 (6 of ~14 branches), `test_agent_base.py:102-248`, `base.py:53-208`.
  Acceptance criteria: `pytest tests/test_agent_base.py -x -q` green with ≥8 new tests; `pytest --collect-only tests/test_agent_base.py` shows them.
  QA scenarios: happy — all new tests pass; failure — flip a cap from 3→2 → cap test fails (proves load-bearing). Evidence `.omo/evidence/task-31-agent-and-project-optimization.log`.
  Commit: Y | test(agent): cover run_agent failure caps, tool-error recovery, event emission

- [x] 32. Wave 6-T2: orchestrator missing transitions — `WRITING→REVIEWING`, `WAITING_USER` break, `CANCELLED`, `run()` dispatch loop, `GATHERING_CONTEXT` success
  What to do / Must NOT do: Add to `tests/test_orchestrator.py`: (a) `_run_writer` with a FakeAdapter that writes a draft → `REVIEWING` (T7 missing); (b) `run()` enters `WAITING_USER` → loop breaks + state stays `WAITING_USER`; (c) cancel token set → `run()` exits with `CANCELLED`; (d) `run()` dispatch loop driven end-to-end (GATHERING→WRITING→REVIEWING→DONE) with a FakeAdapter + real in-memory DB; (e) `_gathering_context` success path (real project) → `WRITING` with non-empty `_outline_context`/`_style_context`. Must NOT test via private-method-only bypass (the point is to cover `run()`).
  Parallelization: Wave 6 | Blocked by: 6, 12 | Blocks: F1-F4 | Can parallelize with: 6-T1, 6-T3..6-T6
  References: T7 (8 of ~14 transitions), `test_orchestrator.py:88-171`, `orchestrator.py:32-131`.
  Acceptance criteria: `pytest tests/test_orchestrator.py -x -q` green with ≥5 new tests.
  QA scenarios: happy — full `run()` dispatch covered; failure — remove the cancel-token check → cancel test fails. Evidence `.omo/evidence/task-32-agent-and-project-optimization.log`.
  Commit: Y | test(orchestrator): cover run() dispatch, WAITING_USER break, CANCELLED, gathering success

- [x] 33. Wave 6-T3: SSE end-to-end tests — full event sequence (parse `event:`/`data:`, assert types + ordering + headers), brainstorm flow, reconnect with active task, 100-turn end
  What to do / Must NOT do: Add `tests/test_sse_e2e.py`: (a) drive `/api/project/.../agent/chat/stream` with a FakeAdapter, parse the full SSE stream (split on `\n\n`, parse `event:` + `data:`), assert the sequence `[agent_start, orchestrator_thought, tool_call, tool_result, agent_output, done]` in order; (b) brainstorm flow events (`brainstorm_response`, `brainstorm_end` on `/done`); (c) reconnect with an active task + `resume_from` → `reconnect` event; (d) 100-turn brainstorm auto-end; (e) assert headers `Cache-Control:no-cache`, `Connection:keep-alive`, `X-Accel-Buffering:no`. Must NOT use a real LLM. Must NOT break the existing 2 smoke tests.
  Parallelization: Wave 6 | Blocked by: 11, 26 | Blocks: F1-F4 | Can parallelize with: 6-T1, 6-T2, 6-T4..6-T6
  References: T8 (SSE smoke only), `test_agent_router.py:13-68`, `agent.py:222-387`.
  Acceptance criteria: `pytest tests/test_sse_e2e.py -x -q` green with ≥5 tests.
  QA scenarios: happy — full sequence + headers; failure — reorder an event in the router → ordering test fails. Evidence `.omo/evidence/task-33-agent-and-project-optimization.log`.
  Commit: Y | test(sse): end-to-end event sequence, brainstorm flow, reconnect, headers

- [x] 34. Wave 6-T4: service + tool unit tests — review/setting tools, writer/reviewer/settings_mgr config builders, brainstorm_service (if not deleted)/outline_gen_service/review_service/setting_service
  What to do / Must NOT do: Add unit tests for: `tools/review.py` (5 tools — `get_chapter_content`/`check_*`/`submit_review`), `tools/setting.py` (7 tools — `search_settings`/`get_setting_detail`/`get_related_settings`/`propose_setting`/`detect_conflicts`/`resolve_conflict`/`link_settings`), `agents/agents/{writer,reviewer,settings_mgr}.py` `build_*_config` (assert tool set + model-from-config + temperature), `outline_gen_service` (4 stream methods with FakeAdapter), `review_service.run_review` (4-dim, post-3-T5), `setting_service.build_llm_context`. If `brainstorm_service` was deleted in 5-T1, skip it. Must NOT test real LLM.
  Parallelization: Wave 6 | Blocked by: 13, 14 | Blocks: F1-F4 | Can parallelize with: 6-T1..6-T3, 6-T5, 6-T6
  References: T8 (0 tests for these), `test_brainstorm_agent.py:10-25` (reference for config-builder test pattern).
  Acceptance criteria: `pytest tests/ -x -q` green with ≥25 new tests; `pytest --cov=app/agents/tools --cov=app/services --cov-report=term-missing` shows tools ≥80%, services ≥60%.
  QA scenarios: happy — new tests pass; failure — `propose_setting` with dup key → test asserts update-not-create. Evidence `.omo/evidence/task-34-agent-and-project-optimization.log`.
  Commit: Y | test(services,tools): unit tests for review/setting tools, config builders, services

- [x] 35. Wave 6-T5: Vitest frontend setup + agent reducer/SSE parser/store tests + a11y assertions
  What to do / Must NOT do: Add `vitest` + `@testing-library/react` + `@testing-library/jest-dom` + `jsdom` to `novel-frontend/package.json` devDeps. Add `vitest.config.ts` (jsdom env, setup file). Add `novel-frontend/src/hooks/use-sse.test.ts` (feed a synthetic SSE chunk → structured store populated correctly — tests the parser from 4-T1). Add `src/stores/agent.test.ts` (reducer transitions: append message, accumulate text_delta, add toolCall, add suggestion, cancel, reset). Add `src/app/projects/[id]/agent/agent-page.test.tsx` (render with a seeded store → assert `aria-live` region exists, reasoning toggle has `aria-expanded`, markdown renders). Add a `test` script to `package.json`. Must NOT add Playwright (heavyweight; e2e covered by F3 manual).
  Parallelization: Wave 6 | Blocked by: 18, 19 | Blocks: F1-F4 | Can parallelize with: 6-T1..6-T4, 6-T6
  References: T4 (0 frontend tests), C17 (a11y), `use-sse.ts`, `stores/agent.ts`.
  Acceptance criteria: `cd novel-frontend && npm run test -- --run` green with ≥10 tests; `npm run build` still passes.
  QA scenarios: happy — vitest green; failure — parser drops an event type → test fails. Evidence `.omo/evidence/task-35-agent-and-project-optimization.log`.
  Commit: Y | test(frontend): vitest setup + agent store/SSE parser/a11y tests

- [x] 36. Wave 6-T6: CI workflow (`.github/workflows/ci.yml`) + `ruff` + `mypy` + `biome.json` + `pre-commit` + `pytest-cov` with `--cov-fail-under`
  What to do / Must NOT do: Add `.github/workflows/ci.yml` with jobs: `backend` (install `.venv`, `ruff check app tests`, `mypy app`, `pytest tests/ --cov=app --cov-fail-under=70`), `frontend` (`npm ci`, `npm run lint`, `npm run build`, `npm run test -- --run`). Add `[tool.ruff]` (line-length 100, select E/F/I/UP/B/SIM) + `[tool.mypy]` (`strict_optional`, ignore missing imports for `anthropic`/`openai` if needed) to `pyproject.toml`. Add `novel-frontend/biome.json` (or extend eslint). Add `.pre-commit-config.yaml` (ruff, mypy, biome, end-of-file-fixer). Wire pre-commit to run on commit. Must NOT make CI fail on warnings (errors only). Must NOT pin versions too tightly (use `>=`).
  Parallelization: Wave 6 | Blocked by: 25-30 | Blocks: F1-F4 | Can parallelize with: 6-T1..6-T5
  References: T5 (no CI/ruff/mypy/pre-commit/cov), `pyproject.toml:39-51`.
  Acceptance criteria: `.github/workflows/ci.yml` exists + validates via `actionlint`; `ruff check app tests` clean; `mypy app` clean (or documented ignores); `pytest tests/ --cov=app --cov-fail-under=70` passes; `npm run test -- --run` passes; `pre-commit run --all-files` clean.
  QA scenarios: happy — CI green locally; failure — drop coverage below 70 → CI fails (proves the gate). Evidence `.omo/evidence/task-36-agent-and-project-optimization.log`.
  Commit: Y | ci: add GitHub Actions + ruff + mypy + biome + pre-commit + coverage gate

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [x] F1. Plan compliance audit — verify every todo's acceptance criteria was met. **Exact check:** on the feature branch `feat/agent-and-project-optimization`, `git log --oneline main..HEAD` shows ≥36 commits (one per implementation todo) + 1..N verification commits; each commit message matches the `type(scope): summary` pattern from the per-todo `Commit:` line; `ls .omo/evidence/task-{1..36}-agent-and-project-optimization.*` shows a non-empty evidence file per todo (assert `test -s` for each). APPROVE iff every todo has a conforming commit + non-empty evidence.
- [x] F2. Code quality review — `ruff check app tests` clean (0 errors; warnings allowed); `mypy app` clean (0 errors; **scoped to files this plan touched** — pre-existing errors in untouched files are out of scope, document them in `.omo/evidence/f2-preexisting-mypy.txt`); `cd novel-frontend && npm run lint && npx tsc --noEmit` clean (scoped: errors in untouched files documented as pre-existing); `npx biome check novel-frontend/src` clean. APPROVE iff zero new errors vs the pre-plan baseline (capture baseline with `mypy app 2>&1 | tee .omo/evidence/f2-mypy-baseline.txt` at Wave 0).
- [ ] F3. Real manual QA — `./dev.sh` → drive the agent chat through the **9 scenarios in `.omo/evidence/f3-manual-qa-check.md`** (a checklist file the worker creates at the start of F3): (1) brainstorm `/brainstorm` turn, (2) writing request with chapter + autonomy preset, (3) confirm a `propose_setting` suggestion card, (4) cancel mid-run via 停止, (5) refresh mid-stream → resume affordance appears, (6) writer "AI" button → agent opens with chapter, (7) brainstorm handoff → 继续写作, (8) markdown renders (bold/list/table), (9) dark + sepia themes. Capture a screenshot per scenario to `.omo/evidence/f3-manual-qa-{1..9}.png`. The worker marks each checklist item ✓/✗; **a human reviews the checklist + screenshots before APPROVE** (F3 is the one explicitly-human gate; the other F's are agent-executed). APPROVE iff all 9 items ✓.
- [x] F4. Scope fidelity — verify no Must-NOT-have item was introduced: `grep -rE "aiosqlite|structlog|loguru|JWT|azure_openai|bedrock|/brainstorm/" app novel-frontend/src` returns 0 (the `/brainstorm/` grep now also catches the removed `main.py:58` redirect — assert it's gone); `git diff --stat main..HEAD -- novel-frontend/src/app/projects/[id]/outline/page.tsx novel-frontend/src/app/projects/[id]/settings/page.tsx novel-frontend/src/app/projects/page.tsx novel-frontend/src/app/page.tsx novel-frontend/src/app/ideas/page.tsx novel-frontend/src/app/styles/page.tsx novel-frontend/src/app/config/page.tsx` shows **only**: token/semantic `var(--...)` consistency changes already in flight (Wave 0 committed), the `formatRelative`/`toneStyles`/`STATUS_BADGE` dedup (5-T5), and the `/review` nav link removal (5-T5) — no UX redesign (no layout/structure changes to those pages). APPROVE iff scope held.

## Commit strategy
- **One commit per todo** (36 implementation todos → 36 commits) + **1..N verification commits** at the end (F1-F4 evidence). Total ≥37 commits on the feature branch.
- Each commit message follows the repo's `type(scope): summary` convention (see `git log --oneline` examples: `feat(agent):`, `fix(db):`, `test(sse):`, `chore:`, `refactor(api):`) — the exact `Commit:` line per todo specifies the message.
- **Wave boundaries are NOT merge boundaries** — commits are atomic per todo; waves are execution-scheduling units only (see Execution strategy for the 5-T1/5-T2-before-4-T1 ordering note).
- **Branch:** work on a feature branch `feat/agent-and-project-optimization` (worker creates via `using-git-worktrees` skill or native branch). Do NOT commit directly to `main`.
- **Never commit a red test.** Every commit must leave `pytest tests/ -x -q` AND (for frontend-touching todos) `npm run lint && npm run build` green.
- **Dirty-worktree (todo 1) is committed first** as `chore(wave0): integrate in-flight dirty-worktree edits` — separate from the agent overhaul commits.
- **Final verification wave** produces evidence files + a final `docs: add f1-f4 verification evidence` commit only after all 4 pass.
- **No squash unless the user requests it.** Atomic commits preserve bisect-ability across this large change.
- **No force-push, no amend of shared commits.** Rebase on `main` is allowed only to resolve conflicts before the final PR.

## Success criteria
- **Agent core (C1):** agent tool-calling uses native provider tool-use (Claude/OpenAI) with JSON fallback for local models; tokens stream in realtime; `confirm_before` actually suspends + resumes; per-task DB session + WAL eliminates the use-after-close bug; model follows user config; every agent turn records an `AICall` row.
- **Orchestrator (C2):** blackboard carries review/draft/pending/round across agents; rewrite loop sees the review; human-in-the-loop confirm is resumable (not a dead-end); cancel works; mid-run crash → resumable snapshot (not silent `failed`); multi-chapter/volume/act milestones run.
- **Tools (C3):** 4-dim review returns real LLM findings (not "ready"); conflict detect/resolve persist; agent search is project-scoped; chapter rollback endpoint works; AI usage recorded at every LLM site.
- **Frontend (C4):** SSE events route into structured panels (chat / reasoning / tool-calls / suggestions / state / progress); tokens stream in-place; stop button + reconnect/resume; mode + chapter + autonomy selector sends full request; suggestion cards + state viz + task history; markdown renders; a11y clean; writer↔agent bridge works.
- **Cleanup (C5):** dead code deleted; API unified under `/api` + envelope; lifespan + structured logging; config-driven model end-to-end; `api_key` masked; frontend dedup; dead 4858-line types removed; review 404 fixed; pydantic v2 + UTC datetimes + schema rebuild.
- **Quality (C6):** `run_agent` 14/14 branches covered; orchestrator 14/14 transitions; SSE e2e verified; services + tools unit-tested; vitest frontend green; CI gate (ruff + mypy + biome + pytest-cov 70% + npm) green on every push.
- **Gates:** `pytest tests/ -x -q` green (≥108 + ≥60 new tests); `cd novel-frontend && npm run lint && npm run build && npm run test -- --run` green; `ruff check app tests && mypy app` clean; F1-F4 all APPROVE.
