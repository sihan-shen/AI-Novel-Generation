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


def test_orchestrator_initial_state(bb):
    orch = Orchestrator(db=None, blackboard=bb, adapter=FakeAdapter())
    assert orch.state == OrchestratorState.IDLE


def test_orchestrator_gathering_context_transitions(bb):
    orch = Orchestrator(db=None, blackboard=bb, adapter=FakeAdapter())
    orch.state = OrchestratorState.GATHERING_CONTEXT
    import sqlalchemy
    # Mock db to avoid actual DB connection
    class FakeDB:
        def query(self, *a): return self
        def filter(self, *a): return self
        def all(self): return []
        def first(self): return None
        add = filter
        commit = lambda self: None
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
    class FakeWriterDB:
        def query(self, *a): return self
        def filter(self, *a): return self
        def all(self): return []
        def first(self): return None
        add = filter
        commit = lambda self: None
    orch = Orchestrator(db=FakeWriterDB(), blackboard=bb, adapter=FakeAdapter())
    final_state = await orch.run()
    assert final_state in (OrchestratorState.IDLE, OrchestratorState.DONE)
