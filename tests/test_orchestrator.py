import json
import pytest
from app.agents.orchestrator import Orchestrator, OrchestratorState
from app.agents.blackboard import Blackboard
from app.agents.autonomy import AutonomyConfig


@pytest.fixture
def bb():
    return Blackboard(
        project_id="p1",
        task={"type": "write_chapter", "chapter_outline_id": "o1", "target_words": 3000},
        autonomy_config=AutonomyConfig(),
    )


class FakeAdapter:
    async def generate(self, messages, **kwargs):
        from app.llm.adapter import LLMResponse
        return LLMResponse(
            content=json.dumps({"action": "finish", "summary": "done"}),
            usage={"input_tokens": 10, "output_tokens": 5},
        )
    def count_tokens(self, text): return 10


class FakeDB:
    def query(self, *a): return self
    def filter(self, *a): return self
    def all(self): return []
    def first(self): return None
    add = filter
    commit = lambda self: None


def test_orchestrator_initial_state(bb):
    orch = Orchestrator(db=None, blackboard=bb, adapter=FakeAdapter())
    assert orch.state == OrchestratorState.IDLE


def test_orchestrator_gathering_context_transitions(bb):
    orch = Orchestrator(db=None, blackboard=bb, adapter=FakeAdapter())
    orch.state = OrchestratorState.GATHERING_CONTEXT
    orch.db = FakeDB()
    next_state = orch._gathering_context()
    assert next_state == OrchestratorState.IDLE  # context gathering fails gracefully


def test_orchestrator_done_to_idle(bb):
    orch = Orchestrator(db=None, blackboard=bb, adapter=FakeAdapter())
    orch.state = OrchestratorState.DONE
    next_state = orch._done()
    assert next_state == OrchestratorState.IDLE


@pytest.mark.asyncio
async def test_orchestrator_run_minimal_flow(bb):
    orch = Orchestrator(db=FakeDB(), blackboard=bb, adapter=FakeAdapter())
    final_state = await orch.run()
    assert final_state in (OrchestratorState.IDLE, OrchestratorState.DONE)


def test_orchestrator_constructor_with_task_id(bb):
    orch = Orchestrator(db=None, blackboard=bb, adapter=FakeAdapter(), task_id="task-123")
    assert orch._task_id == "task-123"
    assert orch.state == OrchestratorState.IDLE


def test_orchestrator_constructor_without_task_id(bb):
    orch = Orchestrator(db=None, blackboard=bb, adapter=FakeAdapter())
    assert orch._task_id is None
    assert orch.state == OrchestratorState.IDLE


def test_orchestrator_state_enum_has_all_states():
    """Verify the state enum has all expected states for the full state machine."""
    assert hasattr(OrchestratorState, "IDLE")
    assert hasattr(OrchestratorState, "GATHERING_CONTEXT")
    assert hasattr(OrchestratorState, "WRITING")
    assert hasattr(OrchestratorState, "REVIEWING")
    assert hasattr(OrchestratorState, "FIXING_SETTINGS")
    assert hasattr(OrchestratorState, "REWRITING")
    assert hasattr(OrchestratorState, "WAITING_USER")
    assert hasattr(OrchestratorState, "DONE")
    assert hasattr(OrchestratorState, "CANCELLED")


@pytest.mark.asyncio
async def test_reviewer_transitions_to_done_when_no_chapter_id(bb):
    """Reviewer should skip to DONE when current_chapter_id is None."""
    orch = Orchestrator(db=FakeDB(), blackboard=bb, adapter=FakeAdapter())
    orch.blackboard.current_chapter_id = None
    next_state = await orch._run_reviewer()
    assert next_state == OrchestratorState.DONE


@pytest.mark.asyncio
async def test_reviewer_transitions_to_done_when_chapter_exists(bb):
    """Reviewer with a chapter_id should complete the review flow."""
    orch = Orchestrator(db=FakeDB(), blackboard=bb, adapter=FakeAdapter())
    orch.blackboard.current_chapter_id = "chap-1"
    next_state = await orch._run_reviewer()
    # FakeAdapter returns finish immediately with no score → defaults to 5.0 → DONE
    assert next_state == OrchestratorState.DONE


@pytest.mark.asyncio
async def test_reviewer_low_score_triggers_rewrite(bb):
    """When review score < 2.5 and rewrite rounds remain, should go to REWRITING."""

    class ScoreReturningAdapter(FakeAdapter):
        async def generate(self, messages, **kwargs):
            from app.llm.adapter import LLMResponse
            return LLMResponse(
                content='{"action": "finish", "summary": "{\\"overall_score\\": 2.0, \\"setting_score\\": 2.0, \\"style_score\\": 2.0, \\"logic_score\\": 2.0}"}',
                usage={"input_tokens": 10, "output_tokens": 5},
            )

    orch = Orchestrator(db=FakeDB(), blackboard=bb, adapter=ScoreReturningAdapter())
    orch.blackboard.current_chapter_id = "chap-1"
    orch.blackboard.rewrite_round = 0
    orch.blackboard.autonomy_config.max_rewrite_rounds = 3
    next_state = await orch._run_reviewer()
    assert next_state == OrchestratorState.REWRITING
    assert orch.blackboard.rewrite_round == 1


@pytest.mark.asyncio
async def test_reviewer_low_score_max_rounds_waits_user(bb):
    """When review score < 2.5 and rewrite rounds exhausted, should go to WAITING_USER."""

    class ScoreReturningAdapter(FakeAdapter):
        async def generate(self, messages, **kwargs):
            from app.llm.adapter import LLMResponse
            return LLMResponse(
                content='{"action": "finish", "summary": "{\\"overall_score\\": 1.5, \\"setting_score\\": 1.5, \\"style_score\\": 1.5, \\"logic_score\\": 1.5}"}',
                usage={"input_tokens": 10, "output_tokens": 5},
            )

    orch = Orchestrator(db=FakeDB(), blackboard=bb, adapter=ScoreReturningAdapter())
    orch.blackboard.current_chapter_id = "chap-1"
    orch.blackboard.rewrite_round = 3
    orch.blackboard.autonomy_config.max_rewrite_rounds = 3
    next_state = await orch._run_reviewer()
    assert next_state == OrchestratorState.WAITING_USER


@pytest.mark.asyncio
async def test_reviewer_pending_changes_triggers_fixing_settings(bb):
    """When review score >= 2.5 and pending_setting_changes exist, should go to FIXING_SETTINGS."""
    orch = Orchestrator(db=FakeDB(), blackboard=bb, adapter=FakeAdapter())
    orch.blackboard.current_chapter_id = "chap-1"
    orch.blackboard.pending_setting_changes = [{"id": "s1"}]
    next_state = await orch._run_reviewer()
    assert next_state == OrchestratorState.FIXING_SETTINGS


@pytest.mark.asyncio
async def test_settings_mgr_transitions_to_rewriting(bb):
    """Settings manager should transition to REWRITING after completion."""
    orch = Orchestrator(db=FakeDB(), blackboard=bb, adapter=FakeAdapter())
    next_state = await orch._run_settings_mgr()
    assert next_state == OrchestratorState.REWRITING


@pytest.mark.asyncio
async def test_rewriter_delegates_to_writer(bb):
    """Rewriter should delegate to _run_writer and transition to REVIEWING."""
    orch = Orchestrator(db=FakeDB(), blackboard=bb, adapter=FakeAdapter())
    next_state = await orch._run_rewriter()
    assert next_state == OrchestratorState.REVIEWING
