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
