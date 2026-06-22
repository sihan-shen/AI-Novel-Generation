---
slug: agent-and-project-optimization
status: plan-complete-awaiting-start-work
intent: unclear
pending-action: present final brief to user; wait for explicit start-work (or scope-change). Plan is decision-complete + dual high-accuracy APPROVED.
approach: Agent-first multi-wave overhaul — 36 todos across 6 waves + final verification. Plan written, revised, and APPROVED by both high-accuracy passes (Codex gpt-5.5 xhigh R2 APPROVE 0 new issues; native Momus R2 APPROVE empty must-fix). Metis gap analysis folded silently.
---

# Draft: agent-and-project-optimization

## Routing call
UNCLEAR intent ("optimize the project from architecture/system-logic/UI-UX/functionality/interaction, emphasize Agent"). Outcome itself is fuzzy. Per UNCLEAR path: researched maximally, adopted announced best-practice defaults, NO user interview. Auto Metis + dual Momus after plan. If the user actually had a specific outcome in mind, they correct at the gate and I switch to asking.

## Components (topology ledger)
| id | outcome (one line) | status | evidence path |
| --- | --- | --- | --- |
| C1 | Agent core: native provider tool-use API + streaming token events + structured tool results; kill dead fields (confirm_before wired, model-from-config); per-task DB session | active | app/agents/base.py:53-208; app/llm/claude_adapter.py:15-23; app/llm/openai_adapter.py:17-26; app/routers/agent.py:335-358 |
| C2 | Orchestrator + blackboard logic: full context wiring (outline/style/review/draft/pending/round in blackboard), effective review→rewrite loop, real human-in-the-loop confirm, cancellation, mid-run persistence + resume, multi-chapter milestone | active | app/agents/orchestrator.py:67-126; app/agents/blackboard.py:84-110; app/agents/autonomy.py:11-14; app/routers/agent.py:390-431; app/main.py:78-110 |
| C3 | Tool substance: implement real consistency checks (setting/style/logic), conflict detect/resolve, project-scoped search, chapter snapshot rollback endpoint, AI call recording in agent loop | active | app/agents/tools/review.py:20-39; app/agents/tools/setting.py:86-91; app/agents/tools/shared.py:7-11; app/agents/tools/writing.py:96-104; app/llm/adapter.py:74-93 |
| C4 | Frontend Agent UI/UX: structured SSE event handling (parse event: lines, route by type), reasoning/toolcall panel per turn, streaming token render, cancel/stop, reconnect/resume, mode selector + chapter picker + autonomy preset, pending-suggestion cards, orchestrator state/progress viz, task history, markdown render, writer↔agent bridge | active | novel-frontend/src/hooks/use-sse.ts:34,65-86; novel-frontend/src/stores/agent.ts:34-42; novel-frontend/src/app/projects/[id]/agent/page.tsx:31-150,264-271; novel-frontend/src/app/projects/[id]/writer/page.tsx:128-131; package.json (no markdown/test libs) |
| C5 | Cross-cutting architecture cleanup: delete dead code (routers/brainstorming.py + services/brainstorm_service.py + templates/brainstorm/ + middleware/auth.py unregistered), unify API prefix (/api) + response envelope, lifespan context manager, config-driven model selection wired through | active | app/main.py:8-11,66-74; app/routers/brainstorming.py:1-123; app/middleware/auth.py:1-13; app/routers/agent.py:209 vs config.py:8; app/agents/agents/writer.py:81 |
| C6 | Test + quality hardening: tests for native tool-use loop / streaming / confirm flow / cancel / resume / real consistency tools; Vitest for frontend agent reducer+SSE; CI workflow + ruff + biome | active | tests/test_agent_base.py:102-248; tests/test_orchestrator.py:88-171; conftest.py:1-57; no .github/workflows; pyproject.toml:39-47 |

## Open assumptions (announced defaults)
| assumption | adopted default | rationale | reversible? |
| --- | --- | --- | --- |
| Tool-calling mechanism | Switch run_agent to provider-native tool-use (Claude tools=+tool_use blocks; OpenAI tools=+tool_calls); keep JSON-fallback shim for providers without tool-use (ollama/local) via per-adapter capability flag | Native tool-use is the supported, robust path; JSON-in-text is fragile (malformed retries, no parallel calls, fights model training). Fallback preserves local-model support. | YES — keep old path behind flag during migration |
| Streaming in agent loop | Stream tokens to client as SSE text_delta during each LLM turn; emit tool_call/tool_result when tool_use blocks arrive | README promises 流式 SSE; current agent loop is batch (no realtime). Streaming is expected UX. | YES |
| DB session ownership | Give orchestrator its own Session from SessionLocal (separate from the request's SSE-generator session); add SQLite busy_timeout + pool args | Current shared sync Session across asyncio task + generator = "database is locked" races. Best practice: session per concurrency boundary. | YES |
| Per-agent model | Derive model from ConfigService/adapter; remove dead AgentConfig.model or wire it through as optional override | AgentConfig.model is hardcoded + never passed to adapter (dead/misleading). Model must follow user config. | YES |
| Scope/phasing | Plan all 6 components; sequence Agent (C1-C3) + Agent frontend (C4) in earlier waves; cleanup (C5) + broad tests (C6) in later waves | User emphasized Agent but asked for whole-project optimization. Agent-first sequencing delivers value early. | YES — user can ask for everything-at-once |
| Dead code | Delete routers/brainstorming.py, services/brainstorm_service.py, templates/brainstorm/, and register-or-remove middleware/auth.py | Unregistered router = dead; two brainstorm impls = confusion. Consolidate on agent-based path. | YES (git) |
| API surface | Move agent router under /api prefix; use APIResponse for JSON endpoints; SSE stays raw stream | Consistency with README + other routers. | YES |
| Real confirm flow | Implement confirm_before in run_agent: emit confirm_request event, suspend on asyncio.Event, resume via /chat/confirm | Current confirm flow is disconnected (B5); WAITING_USER is a dead-end. | YES |
| Cancellation | Add /chat/cancel + CancellationToken in orchestrator; expose stop button | No interrupt today; orphan tasks consume tokens. | YES |
| Mid-run persistence | Snapshot blackboard to AgentTask on state transitions + every N steps; real resume from snapshot on restart | Crash = total loss today. | YES |
| Frontend event model | Parse event: lines; structured store (messages/toolCalls/reasoning/suggestions/state); react-markdown for assistant content | Flat bubbles + plaintext today; poor UX. | YES |
| Markdown | Add react-markdown (+ remark-gfm) dep | Brainstorm prompt emits Markdown; not rendered today. | YES |
| Frontend tests | Add Vitest + Testing Library; test agent reducer + SSE parser + store | No frontend tests today. | YES |
| Consistency tools | Implement with LLM-assisted handlers (pass chapter+settings+style to LLM, return structured findings) — not pure stubs | 4-dim review is partly theatrical today. | YES |
| Milestone multi-chapter | Implement loop over outline nodes by milestone_granularity (chapter/volume/act) | AutonomyConfig field exists but unused. | YES |

No irreversible / destructive / safety-critical fork surfaced → ZERO user questions. All defaults reversible; user vetoes at gate.

## Findings (cited - path:lines)

### Architecture
- A1 Agent tool-calling = text-JSON parsing, not native tool-use. base.py:66-73,106-117; claude_adapter.py:15-21 (no tools=); openai_adapter.py:17-22.
- A2 No streaming in agent loop (generate, not generate_stream). base.py:89.
- A3 Shared sync Session across asyncio task + SSE generator → SQLite lock risk. agent.py:227,335-358; database.py:6-12.
- A4 Hardcoded dead model in agent configs; run_agent never passes config.model. writer.py:81,reviewer.py:51,settings_mgr.py:50,brainstorm.py:53; base.py:89.
- A5 Dead code: routers/brainstorming.py (unregistered), services/brainstorm_service.py, templates/brainstorm/, middleware/auth.py (unregistered); base.py:23 confirm_before unused; autonomy.py:11-14 timeout_action/confirm_timeout_s unused; shared.py:14 report_progress dup.
- A6 Inconsistent URL prefix: agent=/project/{id}/agent, search=/api/search, config=/api/config. agent.py:209,search.py:8,config.py:8.
- A7 Response envelope mixed: config uses APIResponse; agent returns raw dicts. config.py:11-14 vs agent.py:416,431,438.
- A8 Tools commit inside handlers (transaction leak). writing.py:110,120; setting.py:75,82; review.py:62; brainstorm.py:41.
- A9 No mid-run persistence; recovery marks failed. main.py:78-110; agent.py:367-380.
- A10 main.py uses deprecated @app.on_event("startup"). main.py:66.
- A11 API key stored plaintext in Config table + returned by GET /api/config. config_service.py:29-35; config.py:11-14. (security note)

### System logic (Agent)
- B1 Orchestrator sets outline/style context to "" — writer blackboard has no outline/style. orchestrator.py:67-70.
- B2 Rewriter calls _run_writer with no review feedback; last_review not in get_context_for → rewrite loop ineffective. orchestrator.py:125-126; blackboard.py:84-110.
- B3 Blackboard get_context_for omits last_review/current_draft/pending_setting_changes/rewrite_round/current_chapter_id → no cross-agent handoff visibility. blackboard.py:84-110.
- B4 Stub tools: check_setting_consistency/check_style_consistency/check_logic_structure return canned "ready"; detect_conflicts empty; resolve_conflict no-op. review.py:20-39; setting.py:86-91.
- B5 Confirm flow disconnected: confirm_before never checked in run_agent; no confirm_request event emitted; confirm_action writes unconsumed msg; WAITING_USER unreachable to resume. base.py (no check); agent.py:390-431; orchestrator.py:112.
- B6 Intent detection = extra LLM call per first message (latency/cost, fragile JSON). agent.py:33-55,287.
- B7 Brainstorm turn monkey-patches blackboard.get_context_for. agent.py:129-139.
- B8 sequence collisions: confirm=999, recovery=9999, frontend=Date.now(). agent.py:412; main.py:105; use-sse.ts:25.
- B9 Token count crude: count_tokens=len//4 (wrong for CJK); blackboard _rough_token_count different. claude_adapter.py:40-41; blackboard.py:34-37.
- B10 search_any in agent tools omits project_id → global search leaks other projects. writer.py:69-73; search_service.py:27.
- B11 Agent loop never calls record_usage → AI call cost unrecorded for agents. base.py (no call); adapter.py:74-93.

### UI/UX
- C1 No mode selector / chapter picker / autonomy config UI. agent/page.tsx:31-150.
- C2 Frontend drops chapter_outline_id + target_words (sends only {message}). use-sse.ts:34; agent.py:210-213.
- C3 SSE hook ignores event: lines; flattens all events to bubbles. use-sse.ts:65-86.
- C4 No streaming token render; updateLastMessage unused. agent.ts:34-42; use-sse.ts:74-82.
- C5 No cancel/stop; "新对话" leaves orphan backend tasks. use-sse.ts (no AbortController); agent/page.tsx:29.
- C6 No reconnect/resume (backend supports resume_from). agent.py:226,231-247; use-sse.ts.
- C7 No pending-suggestion/inspirations UI (endpoints exist). agent.py:445-505; use-sse.ts.
- C8 No orchestrator state/progress viz. agent/page.tsx.
- C9 No task history UI (/tasks exists). agent.py:434-438.
- C10 No markdown rendering (whitespace-pre-wrap plaintext). agent/page.tsx:272-274; package.json.
- C11 Writer "AI" button has no onClick → writer siloed from agent. writer/page.tsx:128-131.
- C12 Internal messageType leaked as uppercase label. agent/page.tsx:264-271.
- C13 No retry UI for failed LLM calls. agent/page.tsx:171-181.

### Functionality
- D1 4-dim review tools are stubs (B4).
- D2 Conflict detect/resolve are stubs (B4).
- D3 Confirm/approve HITL broken (B5).
- D4 Suggest-mode output invisible (C7).
- D5 No multi-chapter/volume/act milestone loop. orchestrator.py; autonomy.py:8.
- D6 No chapter snapshot rollback endpoint. writing.py:96-104.
- D7 No AI cost dashboard; agent calls unrecorded (B11).

### Interaction
- E1 Intent routing invisible/uncontrollable (B6,C1).
- E2 No mid-run interrupt/refine (B5).
- E3 "新对话" orphans tasks (C5).
- E4 Review→rewrite feedback missing (B2).
- E5 Brainstorm→writing handoff abrupt, no context carry-over. agent.py:267-272.
- E6 Brainstorm turn limit 100, /done /cancel commands exist but no UI buttons. agent.py:89-99,200.

### Tests
- T1 Agent base loop tested (happy/malformed/hallucinated-tool/max-steps/budget/retry) with FakeAdapter. test_agent_base.py:102-248.
- T2 Orchestrator state transitions tested (gather/done/reviewer/rewrite/settings_mgr). test_orchestrator.py:88-171.
- T3 NO tests for: native tool-use (doesn't exist yet), streaming, confirm flow, cancel, resume, real consistency tools, SSE end-to-end, frontend.
- T4 No frontend tests (no vitest/jest). package.json.
- T5 No CI (.github/workflows absent), no ruff/mypy config, pre-commit in dev deps but no config. pyproject.toml:39-47.

## Decisions (with rationale)
- Agent-first sequencing: deliver C1-C4 (the user's emphasis) before C5-C6.
- Native tool-use with fallback: robustness + local-model support.
- Keep changes behind the existing test suite green at every wave (pytest tests/ must pass).
- Dirty worktree: 13 modified files exist (app/llm/adapter.py, provider_registry.py, main.py, routers/config.py, several frontend pages, use-sse.ts, queries/config.ts, pyproject.toml). Plan must NOT clobber these; worker must review/stash/commit them first. Record as dirty_worktree risk.

## Scope IN
- app/agents/** (base, orchestrator, blackboard, autonomy, agents/*, tools/*, prompts/*)
- app/llm/** (adapter, claude/openai adapters, provider_registry)
- app/routers/agent.py (+ move to /api), app/routers/config.py, app/main.py, app/database.py, app/middleware
- app/services/{search,config,brainstorm}_service.py, app/services/review_service.py (consistency), app/agents/tools/*
- novel-frontend/src/{hooks/use-sse.ts, stores/agent.ts, app/projects/[id]/agent/page.tsx, app/projects/[id]/writer/page.tsx, components/features/agent/*, lib/queries/agent.ts, package.json, tsconfig}
- tests/** (new agent + frontend tests), .github/workflows/ci.yml, pyproject ruff config, biome.json

## Scope OUT (Must NOT have)
- No new auth system (middleware/auth stays placeholder or removed; no real auth implementation).
- No database migration to Postgres/other DB (stay SQLite; just fix session usage).
- No rewrite of the non-agent feature pages (projects/outline/settings/styles/ideas/config) beyond token/semantic consistency already in flight — only touch if C5 envelope/prefix requires.
- No new LLM providers beyond wiring existing registry.
- No i18n / no real user accounts.
- No changes to the 13 dirty-worktree files beyond integrating/committing them safely.

## Explorer corroboration (bg_89abfd13 backend / bg_ae6a0463 tests / bg_daf807a6 frontend — all completed)

All three explorers CONFIRMED my findings. Material ADDITIONS they surfaced (folded in below; do not re-explore):

### Backend additions (bg_89abfd13)
- A12 **use-after-close bug**: `asyncio.create_task(orch.run())` in agent.py:336 continues after FastAPI closes the request-scoped `db` at end of StreamingResponse — orchestrator writes to a closed Session. (Upgrades A3 from "risk" to "active bug".)
- A13 SQLite engine has **no WAL pragma, no busy_timeout, no pool_pre_ping**. database.py:6-10. (Upgrades A3.)
- A14 **`RETRY_POLICY` table partially wired**: only `llm_unavailable` + `malformed_response` honored; `tool_timeout`/`rate_limited`/`db_error`/`budget_exceeded` declared but never consulted. base.py:201-208.
- A15 **Two parallel prompt registries**: YAML templates (`ContextBuilder._load_template`) + .txt files (`prompts/loader.load`) — not unified. llm/templates/ (5 yaml, only review+brainstorm used; writing/style_analysis/cleaning dead scenarios) + llm/prompts/ (9 txt).
- A16 **No `relationship()` declarations anywhere**; all joins stringly-typed via `db.query().filter().first()` → N+1 in cleaning_service.consistency_check:38-54.
- A17 **`datetime.utcnow` deprecated in 3.12+**; used in 12+ models. (Cross-cuts with test warnings.)
- A18 **Pydantic v1 `class Config` in config.py:10-11** likely breaks `.env` loading on pydantic-settings 2.x (project pins >=2.2.0). 266 deprecation warnings during pytest confirm.
- A19 **`review_service.run_review` is a deeper stub than B4**: only 2 of 4 dimensions populated, hardcodes `overall_score=3.5`. review_service.py:47-50.
- A20 **Broader accounting gap**: `record_usage` called only in brainstorm_service:38,58 + review_service:45. Streaming paths, style_service.analyze_text/smart_slice, cleaning_service.consistency_check, outline_gen_service.* all skip it. Streams never surface usage (no get_final_message awaited).
- A21 **`list_pending_inspirations` (tools/brainstorm.py:51) declared but never registered as a tool** — dead code.
- A22 **`_recover_agent_tasks` no try/except around db.commit()** — single failure aborts startup recovery of every subsequent task. main.py:78-110.
- A23 **`ErrorResponse` declared (schemas/response.py:12-14) but never used**; all errors are HTTPException.
- A24 **Local response schemas inline in routers** (settings/chapters/styles/reviews/ideas) instead of schemas/ — `schemas/__init__.py` empty.
- A25 **`outline.py` schema forward-ref `children` requires `model_rebuild()` never called**; tree shape not actually populated (frontend builds tree from flat list).
- A26 **No Field validators / no Literal enums** for status fields (e.g. ProjectUpdate.status is `str|None`).
- A27 **Logging effectively absent**: 8 logger.* calls in 2 files (agents/ only); no `logging.basicConfig` in main.py; services/routers/adapters silent.

### Test additions (bg_ae6a0463)
- T6 **run_agent loop: 6 of ~14 branches covered.** Missing: malformed 3-strike cap (base.py:109-114), hallucinated 3-strike cap (142-146), retry 3-strike cap (92-97), exponential backoff verification, tool-handler-raises (155-156), non-string tool result coercion, event emission verification (171-175), message-history growth, _build_tool_schema_description (192-197).
- T7 **Orchestrator: 8 of ~14 transitions.** Missing: WRITING→REVIEWING (run_writer never called directly), WAITING_USER break, CANCELLED entirely (no test references it), run() dispatch loop (tests call private methods directly), GATHERING_CONTEXT success path.
- T8 **No tests for**: outline_gen router (5 endpoints), brainstorming router (7 endpoints, only redirect hit), middleware/auth, migrations m002+m003, database.init_db, config.py, all LLM adapters (claude/openai/context_builder/provider_registry.fetch_models), writer/reviewer/settings_mgr config builders, tools/review (5 tools), tools/setting (7 tools), tools/shared.report_progress, services/ (most: brainstorm/outline_gen/review/setting/chapter/style/idea/config/project/outline/cleaning).
- T9 **266 deprecation warnings** during pytest: Pydantic class Config (9), datetime.utcnow (extensive), FastAPI on_event (main.py:66).
- T10 No coverage measurement (no pytest-cov); no markers; pre-commit in dev deps but no config.

### Frontend additions (bg_daf807a6)
- C14 **`src/types/api.d.ts` is 4858 lines, committed, and NEVER IMPORTED anywhere** — the openapi-typescript pipeline is dead weight. All query files hand-type their own interfaces → drift risk with no compile error.
- C15 **`formatRelative` duplicated 3×** (app/page.tsx:264-277, projects/page.tsx:298-311, projects/[id]/page.tsx:241-254); `toneStyles` 2×; `STATUS_BADGE`/`STATUS_LABEL` 2×.
- C16 **ChatMessage interface re-declared in agent/page.tsx:155-162** with looser types (`role: string` vs store's union) — type drift between store and page.
- C17 **Accessibility**: no `aria-live` on message list (screen readers won't announce streaming), no `aria-expanded` on reasoning toggle, no `aria-label` on input/send button.
- C18 **Responsive**: sidebar `position: fixed` with no mobile drawer; `pl-[var(--layout-sidebar-expanded)]` unconditional → on mobile the sidebar covers the viewport. `Sheet` component exists but unused for this.
- C19 **Triple theme application**: inline `<Script>` in layout.tsx:36-42 + store init in theme.ts:65 + useEffect in theme-provider.tsx:9-13 — over-engineered, harmless but redundant.
- C20 **SSE path bypasses `/api` rewrite** (use-sse.ts:30 hits `BACKEND/project/{id}/agent/chat/stream` directly) → CORS + NEXT_PUBLIC_BACKEND_URL mandatory in prod; inconsistent with other queries that go through ky+rewrite.
- C21 **api-client dead auth plumbing**: NoAuthProvider/ApiKeyProvider/setAuthProvider/useApiKey defined, never called. api-client.ts:9-36.
- C22 **`/projects/[id]/review` page referenced in nav (projects/[id]/page.tsx:53-58) + README but DOES NOT EXIST on disk** → 404 link. (Functionality gap + broken nav.)
- C23 **All pages `"use client"`** even where RSC better (dashboard, project detail) → forfeits RSC streaming, larger JS bundle.
- C24 **gen:types output response shape is `unknown`** for SSE (api.d.ts:4654-4663) → even if wired, types don't help the stream consumer.
- C25 **No request timeout configured in ky** (default 10s applies invisibly).
- C26 **Settings DialogTrigger imported but not used** (plain `<button>` styled manually instead). settings/page.tsx:101-105.
- C27 **Agent page ~30+ inline `style={{}}`** usages for tokens — style drift vs Tailwind classes used elsewhere.
- C28 **Message list grows unbounded** — no virtualisation, no message limit; long sessions = many DOM nodes.
- C29 **@base-ui/react (not Radix)** is the primitive lib; shadcn `style: "base-nova"`. (Noted for component work.)
- C30 **lucide-react v1.18.0 is legitimate** (post-v1 line) — not a fork. (Dispels suspicion.)

## Open questions
None (UNCLEAR path; all defaults adopted). User vetoes at gate.

## Approval gate
status: awaiting-approval
pending-action: write .omo/plans/agent-and-project-optimization.md (append ~30-40 todos across 5-6 waves, fill TL;DR), then AUTO-run Metis gap analysis + dual Momus (native momus + Codex gpt-5.5 xhigh) per UNCLEAR path; fix all cited issues; resubmit until both approve; then present final.
approach: Agent-first multi-wave overhaul (6 components C1-C6 above).
dirty_worktree risk: 13 modified files; worker commits/stashes before Wave 1.
