import pytest
from app.agents.base import AgentConfig, Tool, AgentStep, AgentRunResult


def test_agent_config_creation():
    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[],
        model="claude-sonnet-4-6",
    )
    assert config.max_steps == 15
    assert config.temperature == 0.7
    assert config.token_budget == 100_000


def test_tool_creation():
    def dummy_handler(**kwargs):
        return "ok"

    tool = Tool(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {}},
        handler=dummy_handler,
    )
    assert tool.confirm_before is False
    assert tool.idempotent is True


def test_agent_step_creation():
    step = AgentStep(
        thought="I should look up settings",
        tool_name="lookup_settings",
        tool_args={"keywords": ["magic"]},
        result="Found 2 settings",
        token_usage={"input_tokens": 100, "output_tokens": 50},
    )
    assert step.tool_name == "lookup_settings"


def test_agent_run_result_creation():
    result = AgentRunResult(
        steps=[],
        output="Chapter written",
        blackboard_changes={},
        status="completed",
        error_code=None,
        retry_count=0,
    )
    assert result.status == "completed"
    assert result.error_code is None


def test_agent_run_result_with_error():
    result = AgentRunResult(
        steps=[],
        output="",
        blackboard_changes={},
        status="error",
        error_code="llm_unavailable",
        retry_count=3,
    )
    assert result.status == "error"
    assert result.error_code == "llm_unavailable"


import json
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.base import AgentConfig, Tool, run_agent
from app.agents.blackboard import Blackboard
from app.agents.autonomy import AutonomyConfig


class FakeAdapter:
    """Mock LLM adapter that returns predetermined JSON responses."""
    def __init__(self, responses: list[dict]):
        self.responses = responses
        self.call_count = 0

    async def generate(self, messages, **kwargs):
        resp = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        from app.llm.adapter import LLMResponse
        return LLMResponse(
            content=json.dumps(resp),
            usage={"input_tokens": 100, "output_tokens": 50},
        )

    def count_tokens(self, text):
        return 100


def make_test_blackboard():
    return Blackboard(
        project_id="p1",
        task={"type": "write_chapter", "chapter_outline_id": "o1", "target_words": 3000},
        autonomy_config=AutonomyConfig(),
    )


@pytest.mark.asyncio
async def test_run_agent_finishes_and_calls_tools():
    bb = make_test_blackboard()
    adapter = FakeAdapter([
        {"thought": "I will look up settings", "tool": "lookup_settings", "args": {"keywords": ["magic"]}},
        {"thought": "Now I will write", "tool": "write_chapter", "args": {"title": "Ch3", "content": "Once upon a time..."}},
        {"action": "finish", "summary": "Chapter written"},
    ])

    def lookup_handler(**kwargs):
        return json.dumps({"found": 2, "settings": [{"name": "Magic System", "summary": "..."}]})

    def write_handler(**kwargs):
        bb.write_draft(kwargs.get("content", ""))
        return json.dumps({"chapter_id": "c3", "word_count": len(kwargs.get("content", ""))})

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[
            Tool(name="lookup_settings", description="Look up settings", parameters={}, handler=lookup_handler),
            Tool(name="write_chapter", description="Write chapter", parameters={}, handler=write_handler),
        ],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, adapter)
    assert result.status == "completed"
    assert len(result.steps) == 2
    assert result.steps[0].tool_name == "lookup_settings"
    assert result.steps[1].tool_name == "write_chapter"
    assert bb.current_draft == "Once upon a time..."
    assert adapter.call_count == 3  # 2 tools + 1 finish


@pytest.mark.asyncio
async def test_run_agent_malformed_json_retries():
    bb = make_test_blackboard()
    adapter = FakeAdapter([
        "not valid json at all",
        {"action": "finish", "summary": "done after retry"},
    ])

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, adapter)
    assert result.status == "completed"
    assert adapter.call_count == 2  # first failed, second succeeded


@pytest.mark.asyncio
async def test_run_agent_hallucinated_tool_name_retries():
    bb = make_test_blackboard()
    adapter = FakeAdapter([
        {"thought": "use bogus tool", "tool": "nonexistent_tool", "args": {}},
        {"thought": "ok let me finish", "action": "finish", "summary": "done"},
    ])

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[
            Tool(name="real_tool", description="The only tool", parameters={}, handler=lambda **kw: "ok"),
        ],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, adapter)
    assert result.status == "completed"
    assert adapter.call_count == 2


@pytest.mark.asyncio
async def test_run_agent_stops_at_max_steps():
    bb = make_test_blackboard()
    infinite_tool_calls = [
        {"thought": f"step {i}", "tool": "ping", "args": {}}
        for i in range(20)
    ]
    adapter = FakeAdapter(infinite_tool_calls)

    config = AgentConfig(
        system_prompt="You loop forever.",
        tools=[
            Tool(name="ping", description="ping", parameters={}, handler=lambda **kw: "pong"),
        ],
        model="claude-sonnet-4-6",
        max_steps=5,
    )

    result = await run_agent(config, bb, adapter)
    assert result.status == "max_steps_reached"
    assert len(result.steps) <= 5


@pytest.mark.asyncio
async def test_run_agent_budget_exceeded():
    bb = make_test_blackboard()
    adapter = FakeAdapter([
        {"thought": "step 1", "tool": "expensive", "args": {}},
        {"thought": "step 2", "tool": "expensive", "args": {}},
        {"action": "finish", "summary": "done"},
    ])

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[
            Tool(name="expensive", description="uses tokens", parameters={}, handler=lambda **kw: "big result " * 1000),
        ],
        model="claude-sonnet-4-6",
        token_budget=200,
    )

    result = await run_agent(config, bb, adapter)
    assert result.status == "budget_exceeded"


@pytest.mark.asyncio
async def test_run_agent_retry_policy_respected():
    bb = make_test_blackboard()
    call_count = [0]

    class FlakyAdapter:
        async def generate(self, messages, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise Exception("LLM API unavailable")
            from app.llm.adapter import LLMResponse
            return LLMResponse(
                content=json.dumps({"action": "finish", "summary": "finally works"}),
                usage={"input_tokens": 10, "output_tokens": 5},
            )

        def count_tokens(self, text):
            return 10

    config = AgentConfig(
        system_prompt="test",
        tools=[],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, FlakyAdapter())
    assert result.status == "completed"
    assert result.retry_count == 2
