import json
import pytest
from app.agents.blackboard import Blackboard
from app.agents.autonomy import AutonomyConfig


def make_task(chapter_outline_id="o1", target_words=3000):
    return {
        "type": "write_chapter",
        "chapter_outline_id": chapter_outline_id,
        "target_words": target_words,
    }


@pytest.fixture
def blackboard():
    return Blackboard(
        project_id="p1",
        task=make_task(),
        autonomy_config=AutonomyConfig(),
    )


def test_blackboard_initial_state(blackboard):
    assert blackboard.project_id == "p1"
    assert blackboard.orchestrator_state == "IDLE"
    assert blackboard.current_draft is None
    assert blackboard.last_review is None
    assert blackboard.rewrite_round == 0
    assert blackboard.cumulative_tokens == 0


def test_blackboard_write_draft(blackboard):
    blackboard.write_draft("Chapter 3 content")
    assert blackboard.current_draft == "Chapter 3 content"


def test_blackboard_record_step(blackboard):
    from app.agents.base import AgentStep
    step = AgentStep(
        thought="looking up",
        tool_name="lookup_settings",
        tool_args={"keywords": ["magic"]},
        result="Found 2 settings",
        token_usage={"input_tokens": 100, "output_tokens": 50},
    )
    blackboard.record_step(step)
    assert len(blackboard.agent_steps) == 1
    assert blackboard.cumulative_tokens == 150


def test_blackboard_get_context_for_writer(blackboard):
    ctx = blackboard.get_context_for("writer")
    assert "p1" in ctx
    assert "IDLE" in ctx


def test_blackboard_to_snapshot_and_back(blackboard):
    blackboard.write_draft("test draft")
    blackboard.orchestrator_state = "WRITING"
    blackboard.rewrite_round = 1
    blackboard.cumulative_tokens = 500

    snapshot = blackboard.to_snapshot()
    assert "project_id" in snapshot
    assert snapshot["current_draft"] == "test draft"
    assert snapshot["orchestrator_state"] == "WRITING"

    restored = Blackboard.from_snapshot(snapshot)
    assert restored.project_id == "p1"
    assert restored.current_draft == "test draft"
    assert restored.orchestrator_state == "WRITING"
    assert restored.rewrite_round == 1
    assert restored.events is not None  # new empty queue


def test_blackboard_context_compression_trigger():
    bb = Blackboard(
        project_id="p1",
        task=make_task(),
        autonomy_config=AutonomyConfig(),
    )
    from app.agents.base import AgentStep
    fake_text = "x" * 4000  # ~1K tokens
    for i in range(15):
        step = AgentStep(
            thought=f"step {i}",
            tool_name="lookup_settings",
            tool_args={},
            result=fake_text,
            token_usage={"input_tokens": 1000, "output_tokens": 1000},
        )
        bb.record_step(step)

    ctx = bb.get_context_for("writer")
    assert len(ctx) < len(fake_text) * 15  # should be compressed
    assert "compressed" in ctx.lower() or "摘要" in ctx
