import pytest

from app.agents.autonomy import AutonomyConfig
from app.agents.blackboard import Blackboard


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


def test_blackboard_get_context_for_last_review(blackboard):
    blackboard.last_review = {"overall_score": 3.5, "findings": ["plot hole in chapter 2"]}
    ctx = blackboard.get_context_for("writer")
    assert "上次审阅" in ctx
    assert "3.5" in ctx
    assert "plot hole in chapter 2" in ctx


def test_blackboard_get_context_for_current_draft(blackboard):
    blackboard.current_draft = "This is a long draft text that should appear in context." * 20
    ctx = blackboard.get_context_for("writer")
    assert "当前草稿" in ctx
    assert "This is a long draft" in ctx


def test_blackboard_get_context_for_pending_setting_changes(blackboard):
    blackboard.pending_setting_changes = [{"key": "magic_system", "value": "updated"}]
    ctx = blackboard.get_context_for("writer")
    assert "待确认设定变更" in ctx
    assert "magic_system" in ctx


def test_blackboard_get_context_for_rewrite_round(blackboard):
    blackboard.rewrite_round = 2
    ctx = blackboard.get_context_for("writer")
    assert "重写轮次" in ctx
    assert "第 2 轮重写" in ctx


def test_blackboard_get_context_for_current_chapter_id(blackboard):
    blackboard.current_chapter_id = "ch-123"
    ctx = blackboard.get_context_for("writer")
    assert "当前章节" in ctx
    assert "ch-123" in ctx


def test_blackboard_get_context_for_all_fields_absent_when_not_set(blackboard):
    ctx = blackboard.get_context_for("writer")
    assert "上次审阅" not in ctx
    assert "当前草稿" not in ctx
    assert "待确认设定变更" not in ctx
    assert "重写轮次" not in ctx
    assert "当前章节" not in ctx


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


def test_gathering_context_populates_outline_and_style(db_session):
    from app.agents.autonomy import AutonomyConfig
    from app.agents.blackboard import Blackboard
    from app.agents.orchestrator import Orchestrator, OrchestratorState
    from app.models.outline import Outline
    from app.models.project import Project
    from app.models.style import ProjectStyleLink, Style

    project = Project(id="proj-1", title="Test", description="", genre="fantasy", status="active")
    outline = Outline(
        id="out-1", project_id="proj-1", parent_id=None, level=1, sort_order=0,
        title="Vol1", summary="", notes="", status="draft",
        word_count_target=0, word_count_actual=0, pov_character="",
    )
    style = Style(id="style-1", name="Epic", source="", source_text="", analysis='{"tone":"grand"}', tags="[]")
    link = ProjectStyleLink(project_id="proj-1", style_id="style-1", weight=1.5)

    db_session.add(project)
    db_session.add(outline)
    db_session.add(style)
    db_session.add(link)
    db_session.commit()

    bb = Blackboard(
        project_id="proj-1",
        task={"type": "write_chapter", "chapter_outline_id": "out-1", "target_words": 3000},
        autonomy_config=AutonomyConfig(),
    )
    orch = Orchestrator(db=db_session, blackboard=bb, adapter=None, task_id=None)
    result_state = orch._gathering_context()

    assert result_state == OrchestratorState.WRITING
    assert bb._outline_context != ""
    assert "Vol1" in bb._outline_context
    assert bb._style_context != ""
    assert "Epic" in bb._style_context
    assert "grand" in bb._style_context
