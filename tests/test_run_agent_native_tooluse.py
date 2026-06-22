import asyncio
import json

import pytest

from app.agents.autonomy import AutonomyConfig
from app.agents.base import AgentConfig, Tool, run_agent
from app.agents.blackboard import Blackboard
from app.llm.adapter import ToolUseResponse
from app.llm.exceptions import LLMToolParseError


class FakeNativeAdapter:
    """Mock LLM adapter that supports native tool-use."""
    supports_native_tools = True

    def __init__(self, tool_responses: list[ToolUseResponse], fallback_generate_responses: list[dict] | None = None):
        self.tool_responses = tool_responses
        self.fallback_generate_responses = fallback_generate_responses or [{"action": "finish", "summary": "fallback"}]
        self.call_count = 0
        self.generate_call_count = 0
        self.streamed_chunks: list[str] = []

    async def generate_with_tools(self, messages, tools, *, temperature, max_tokens, stream_callback):
        resp = self.tool_responses[self.call_count % len(self.tool_responses)]
        self.call_count += 1
        # Simulate streaming if callback provided and content exists
        if stream_callback and resp.content:
            for chunk in resp.content.split():
                stream_callback(chunk + " ")
                self.streamed_chunks.append(chunk + " ")
        return resp

    async def generate(self, messages, **kwargs):
        resp = self.fallback_generate_responses[self.generate_call_count % len(self.fallback_generate_responses)]
        self.generate_call_count += 1
        from app.llm.adapter import LLMResponse
        return LLMResponse(
            content=json.dumps(resp),
            usage={"input_tokens": 100, "output_tokens": 50},
        )

    def count_tokens(self, text):
        return 100


def make_test_blackboard(autonomy_config=None):
    return Blackboard(
        project_id="p1",
        task={"type": "write_chapter", "chapter_outline_id": "o1", "target_words": 3000},
        autonomy_config=autonomy_config or AutonomyConfig(),
    )


# (a) FakeAdapter with supports_native_tools=True returns a ToolUseResponse with one tool_call
# → tool executed + finish → status="completed"
@pytest.mark.asyncio
async def test_run_agent_native_tool_use_happy_path():
    bb = make_test_blackboard()

    def lookup_handler(**kwargs):
        return json.dumps({"found": 2})

    adapter = FakeNativeAdapter([
        ToolUseResponse(
            content="Looking up settings",
            tool_calls=[{"name": "lookup_settings", "args": {"keywords": ["magic"]}}],
            finish_reason="tool_calls",
            usage={"input_tokens": 100, "output_tokens": 50},
        ),
        ToolUseResponse(
            content="Done",
            tool_calls=[],
            finish_reason="stop",
            usage={"input_tokens": 50, "output_tokens": 20},
        ),
    ])

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[
            Tool(name="lookup_settings", description="Look up settings", parameters={}, handler=lookup_handler),
        ],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, adapter)
    assert result.status == "completed"
    assert len(result.steps) == 1
    assert result.steps[0].tool_name == "lookup_settings"
    assert adapter.call_count == 2  # one tool call + one finish


# (b) confirm_before=True tool → confirm_request event emitted + _confirm_events has confirm_id
# + await event.wait() suspends (prove with asyncio.wait_for timeout)
@pytest.mark.asyncio
async def test_run_agent_native_confirm_before_suspends():
    bb = make_test_blackboard()

    def propose_handler(**kwargs):
        return json.dumps({"proposed": True})

    adapter = FakeNativeAdapter([
        ToolUseResponse(
            content="Proposing setting",
            tool_calls=[{"name": "propose_setting", "args": {"name": "Magic", "content": "..."}}],
            finish_reason="tool_calls",
            usage={"input_tokens": 100, "output_tokens": 50},
        ),
        ToolUseResponse(
            content="Done",
            tool_calls=[],
            finish_reason="stop",
            usage={"input_tokens": 50, "output_tokens": 20},
        ),
    ])

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[
            Tool(name="propose_setting", description="Propose a setting", parameters={}, handler=propose_handler, confirm_before=True),
        ],
        model="claude-sonnet-4-6",
    )

    # Prove suspension: run_agent should hang because confirm event is never set
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(run_agent(config, bb, adapter), timeout=0.1)

    # Check that confirm_request event was emitted
    events = []
    while not bb.events.empty():
        events.append(bb.events.get_nowait())

    confirm_events = [e for e in events if e.get("type") == "confirm_request"]
    assert len(confirm_events) == 1
    confirm_id = confirm_events[0]["id"]
    assert confirm_events[0]["tool"] == "propose_setting"
    assert confirm_id in bb._confirm_events

    bb._confirm_events.clear()
    bb._confirm_outcomes.clear()

    adapter.call_count = 0
    task = asyncio.create_task(run_agent(config, bb, adapter))

    while not bb._confirm_events:
        await asyncio.sleep(0.01)

    new_confirm_id = list(bb._confirm_events.keys())[0]
    bb._confirm_outcomes[new_confirm_id] = {"action": "approve"}
    bb._confirm_events[new_confirm_id].set()

    result = await task
    assert result.status == "completed"
    assert len(result.steps) == 1


# (c) confirm timeout + timeout_action="skip" → tool skipped, loop continues to finish
@pytest.mark.asyncio
async def test_run_agent_native_confirm_timeout_skip():
    autonomy = AutonomyConfig(confirm_timeout_s=0.01, timeout_action="skip")
    bb = make_test_blackboard(autonomy_config=autonomy)

    def propose_handler(**kwargs):
        return json.dumps({"proposed": True})

    adapter = FakeNativeAdapter([
        ToolUseResponse(
            content="Proposing setting",
            tool_calls=[{"name": "propose_setting", "args": {"name": "Magic", "content": "..."}}],
            finish_reason="tool_calls",
            usage={"input_tokens": 100, "output_tokens": 50},
        ),
        ToolUseResponse(
            content="Done",
            tool_calls=[],
            finish_reason="stop",
            usage={"input_tokens": 50, "output_tokens": 20},
        ),
    ])

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[
            Tool(name="propose_setting", description="Propose a setting", parameters={}, handler=propose_handler, confirm_before=True),
        ],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, adapter)
    assert result.status == "completed"
    # Tool was skipped due to timeout, so no steps
    assert len(result.steps) == 0


# (d) confirm timeout + timeout_action="abort_task" → status="cancelled"
@pytest.mark.asyncio
async def test_run_agent_native_confirm_timeout_abort():
    autonomy = AutonomyConfig(confirm_timeout_s=0.01, timeout_action="abort_task")
    bb = make_test_blackboard(autonomy_config=autonomy)

    def propose_handler(**kwargs):
        return json.dumps({"proposed": True})

    adapter = FakeNativeAdapter([
        ToolUseResponse(
            content="Proposing setting",
            tool_calls=[{"name": "propose_setting", "args": {"name": "Magic", "content": "..."}}],
            finish_reason="tool_calls",
            usage={"input_tokens": 100, "output_tokens": 50},
        ),
    ])

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[
            Tool(name="propose_setting", description="Propose a setting", parameters={}, handler=propose_handler, confirm_before=True),
        ],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, adapter)
    assert result.status == "cancelled"
    assert len(result.steps) == 0


# (e) streaming: stream_callback receives text_delta chunks and they land on blackboard.events
@pytest.mark.asyncio
async def test_run_agent_native_streaming_text_delta():
    bb = make_test_blackboard()

    def lookup_handler(**kwargs):
        return json.dumps({"found": 2})

    adapter = FakeNativeAdapter([
        ToolUseResponse(
            content="Looking up settings now",
            tool_calls=[{"name": "lookup_settings", "args": {"keywords": ["magic"]}}],
            finish_reason="tool_calls",
            usage={"input_tokens": 100, "output_tokens": 50},
        ),
        ToolUseResponse(
            content="All done",
            tool_calls=[],
            finish_reason="stop",
            usage={"input_tokens": 50, "output_tokens": 20},
        ),
    ])

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[
            Tool(name="lookup_settings", description="Look up settings", parameters={}, handler=lookup_handler),
        ],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, adapter)
    assert result.status == "completed"

    events = []
    while not bb.events.empty():
        events.append(bb.events.get_nowait())

    text_delta_events = [e for e in events if e.get("type") == "text_delta"]
    assert len(text_delta_events) > 0
    # The content "Looking up settings now" splits into 4 words, each with a trailing space
    assert any("Looking" in str(e.get("content", "")) for e in text_delta_events)


# (f) native path returns a tool name not in config.tools → corrective system message appended + retry
@pytest.mark.asyncio
async def test_run_agent_native_unknown_tool_name_retries():
    bb = make_test_blackboard()

    def real_handler(**kwargs):
        return json.dumps({"ok": True})

    adapter = FakeNativeAdapter([
        ToolUseResponse(
            content="Using bogus tool",
            tool_calls=[{"name": "nonexistent_tool", "args": {}}],
            finish_reason="tool_calls",
            usage={"input_tokens": 100, "output_tokens": 50},
        ),
        ToolUseResponse(
            content="Using real tool",
            tool_calls=[{"name": "real_tool", "args": {}}],
            finish_reason="tool_calls",
            usage={"input_tokens": 100, "output_tokens": 50},
        ),
        ToolUseResponse(
            content="Done",
            tool_calls=[],
            finish_reason="stop",
            usage={"input_tokens": 50, "output_tokens": 20},
        ),
    ])

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[
            Tool(name="real_tool", description="The only tool", parameters={}, handler=real_handler),
        ],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, adapter)
    assert result.status == "completed"
    assert adapter.call_count == 3
    assert len(result.steps) == 1
    assert result.steps[0].tool_name == "real_tool"


# (g) native path raises LLMToolParseError → falls back to JSON loop
@pytest.mark.asyncio
async def test_run_agent_native_llm_tool_parse_error_falls_back():
    bb = make_test_blackboard()

    class FlakyNativeAdapter:
        supports_native_tools = True

        def __init__(self):
            self.call_count = 0
            self.generate_call_count = 0

        async def generate_with_tools(self, messages, tools, *, temperature, max_tokens, stream_callback):
            self.call_count += 1
            raise LLMToolParseError("malformed tool block")

        async def generate(self, messages, **kwargs):
            self.generate_call_count += 1
            from app.llm.adapter import LLMResponse
            return LLMResponse(
                content=json.dumps({"action": "finish", "summary": "fallback done"}),
                usage={"input_tokens": 100, "output_tokens": 50},
            )

        def count_tokens(self, text):
            return 100

    adapter = FlakyNativeAdapter()

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, adapter)
    assert result.status == "completed"
    assert adapter.call_count == 1  # generate_with_tools called once
    assert adapter.generate_call_count == 1  # fallback to generate called once


# Verify blackboard has _confirm_events and _confirm_outcomes
def test_blackboard_has_confirm_events_and_outcomes():
    bb = make_test_blackboard()
    assert hasattr(bb, "_confirm_events")
    assert hasattr(bb, "_confirm_outcomes")
    assert isinstance(bb._confirm_events, dict)
    assert isinstance(bb._confirm_outcomes, dict)


# Verify to_snapshot / from_snapshot round-trip for confirm fields
@pytest.mark.asyncio
async def test_blackboard_snapshot_round_trip_confirm_fields():
    bb = make_test_blackboard()
    bb._confirm_events["test-id"] = asyncio.Event()
    bb._confirm_outcomes["test-id"] = {"action": "approve"}

    snapshot = bb.to_snapshot()
    assert "_confirm_events" in snapshot
    assert "_confirm_outcomes" in snapshot
    assert snapshot["_confirm_outcomes"] == {"test-id": {"action": "approve"}}

    restored = Blackboard.from_snapshot(snapshot)
    assert restored._confirm_outcomes == {"test-id": {"action": "approve"}}
    assert isinstance(restored._confirm_events, dict)
