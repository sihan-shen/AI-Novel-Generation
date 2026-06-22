# Wave 6-T1 Evidence — run_agent missing branch tests

## Verification

### Test collection
```
pytest tests/test_agent_base.py --collect-only -q
```

Result: 20 tests collected (11 original + 9 added in Wave 1-T5, commit ad21b08).

### Full test suite
```
pytest tests/ -q --tb=no
```

Result: **220 passed** in ~11s.

### Tests added
1. `test_run_agent_malformed_json_3_strikes_error` — 3× invalid JSON → `status="error"`, `error_code="malformed_response"`
2. `test_run_agent_hallucinated_tool_3_strikes_error` — 3× unknown tool → `status="error"`, `error_code="malformed_response"`
3. `test_run_agent_llm_unavailable_3_strikes_error` — 4× LLM raise → `status="error"`, `error_code="llm_unavailable"` (retry_count=4)
4. `test_run_agent_tool_handler_raises_continues` — handler raises → "Tool execution error: boom" in result, loop continues to finish
5. `test_run_agent_tool_returns_none_coerced` — handler returns None → "None" in step result
6. `test_run_agent_emits_tool_call_and_tool_result_events` — blackboard.events contains `tool_call` + `tool_result`
7. `test_run_agent_emits_checkpoint_every_5_steps` — 5-tool loop emits `checkpoint` event at step 5
8. `test_run_agent_message_history_grows` — message history grows by 2 per tool turn (assistant + system)
9. `test_build_tool_schema_description_renders_name_and_params` — schema description contains tool name, description, and "properties"

### Commit
```
ad21b08 test(agent): cover run_agent failure caps, tool-error recovery, event emission
```

### No production code changes
- `git diff --stat` shows only `.omo/` files modified (plan checkbox, evidence, ledger)
- `tests/test_agent_base.py` was already committed in ad21b08

## QA scenarios exercised
- **happy**: all 220 tests pass
- **failure**: N/A (tests only, no behavior change)

## Cleanup
- N/A
