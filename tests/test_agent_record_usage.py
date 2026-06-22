import json
import logging
from unittest.mock import patch

import pytest

from app.agents.autonomy import AutonomyConfig
from app.agents.base import AgentConfig, run_agent
from app.agents.blackboard import Blackboard
from app.models.ai_call import AICall


class FakeAdapter:
    """Mock LLM adapter that returns predetermined JSON responses."""
    def __init__(self, responses: list[dict]):
        self.responses = responses
        self.call_count = 0
        self.model = "test-model"

    async def generate(self, messages, **kwargs):
        import asyncio
        await asyncio.sleep(0.001)  # Ensure non-zero duration_ms
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
async def test_run_agent_records_ai_call(db_session, caplog):
    """Given a FakeAdapter that returns usage, when run_agent completes,
    then an AICall row is recorded with correct scenario, project_id, tokens, and duration_ms."""
    caplog.set_level(logging.WARNING)
    bb = make_test_blackboard()
    adapter = FakeAdapter([
        {"thought": "I will finish", "action": "finish", "summary": "Done"},
    ])

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[],
        model="",
    )

    result = await run_agent(config, bb, adapter, db=db_session, agent_type="writer")

    assert result.status == "completed"

    # Verify AICall row was written
    calls = db_session.query(AICall).all()
    assert len(calls) == 1
    call = calls[0]
    assert call.scenario == "agent_writer"
    assert call.project_id == "p1"
    assert call.model == "test-model"
    assert call.input_tokens == 100
    assert call.output_tokens == 50
    assert call.duration_ms is not None
    assert call.duration_ms > 0


@pytest.mark.asyncio
async def test_run_agent_record_usage_failure_continues(db_session, caplog):
    """Given record_usage raises an exception, when run_agent runs,
    then the loop continues, result is completed, and a WARNING is logged."""
    caplog.set_level(logging.WARNING)
    bb = make_test_blackboard()
    adapter = FakeAdapter([
        {"thought": "I will finish", "action": "finish", "summary": "Done"},
    ])

    config = AgentConfig(
        system_prompt="You are a writer.",
        tools=[],
        model="",
    )

    with patch("app.agents.base.record_usage", side_effect=RuntimeError("db boom")):
        result = await run_agent(config, bb, adapter, db=db_session, agent_type="writer")

    assert result.status == "completed"
    assert any("record_usage failed" in r.message for r in caplog.records)
