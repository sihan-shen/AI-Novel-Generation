import asyncio
import json

import pytest

from app.agents.autonomy import AutonomyConfig
from app.agents.blackboard import Blackboard
from app.agents.orchestrator import Orchestrator, OrchestratorState


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


class SlowFakeAdapter:
    """Adapter that sleeps briefly so cancel() can be called mid-run."""
    def __init__(self, sleep_seconds: float = 0.15):
        self.sleep_seconds = sleep_seconds

    async def generate(self, messages, **kwargs):
        await asyncio.sleep(self.sleep_seconds)
        from app.llm.adapter import LLMResponse
        return LLMResponse(
            content=json.dumps({"action": "finish", "summary": "done"}),
            usage={"input_tokens": 10, "output_tokens": 5},
        )

    def count_tokens(self, text): return 10


class FakeProject:
    id = "p1"
    title = "Test Project"
    genre = "fantasy"
    status = "active"


class FakeDB:
    def query(self, *a): return self
    def filter(self, *a): return self
    def order_by(self, *a): return self
    def all(self): return []
    def first(self): return FakeProject()
    add = filter
    commit = lambda self: None


def test_orchestrator_cancel_sets_flag(bb):
    """Given: a fresh Orchestrator. When: cancel() is called. Then: cancelled is True."""
    orch = Orchestrator(db=FakeDB(), blackboard=bb, adapter=FakeAdapter())
    assert orch.cancelled is False
    orch.cancel()
    assert orch.cancelled is True


@pytest.mark.asyncio
async def test_orchestrator_cancel_mid_run_returns_cancelled(bb):
    """Given: Orchestrator running with a slow adapter.
    When: cancel() is called mid-run.
    Then: run() returns CANCELLED and emits a cancelled event."""
    orch = Orchestrator(db=FakeDB(), blackboard=bb, adapter=SlowFakeAdapter(sleep_seconds=0.15))

    run_task = asyncio.create_task(orch.run())
    # Give the orchestrator time to enter the WRITING state
    await asyncio.sleep(0.05)
    orch.cancel()

    final_state = await asyncio.wait_for(run_task, timeout=2.0)
    assert final_state == OrchestratorState.CANCELLED

    # Verify the cancelled event was emitted to the blackboard
    events = []
    while not bb.events.empty():
        events.append(bb.events.get_nowait())
    cancelled_events = [e for e in events if e.get("type") == "cancelled"]
    assert len(cancelled_events) == 1
    assert cancelled_events[0].get("sequence") == 0


def test_cancel_endpoint_no_active_task(client, db_session):
    """Given: no active task for the project.
    When: POST /chat/cancel is called.
    Then: returns 200 with idempotent 'No active task' message."""
    from app.models.project import Project
    db_session.add(Project(id="p1", title="Test"))
    db_session.commit()
    response = client.post("/api/project/p1/agent/chat/cancel", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert "No active task" in body["data"]["message"]


@pytest.mark.asyncio
async def test_cancel_endpoint_cancels_running_orchestrator(client, db_session):
    """Given: an active orchestrator stream.
    When: POST /chat/cancel is called.
    Then: the orchestrator is cancelled and task status is 'cancelled'."""
    from app.models.outline import Outline
    from app.models.project import Project
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Outline(id="o1", project_id="p1", parent_id=None, level=2, sort_order=1, title="Chapter 1"))
    db_session.commit()

    # Patch the adapter to be slow so we have time to cancel
    import app.routers.agent as agent_module
    original_get_adapter = agent_module.get_adapter

    def patched_get_adapter(db):
        return SlowFakeAdapter(sleep_seconds=0.2)

    agent_module.get_adapter = patched_get_adapter
    try:
        # Start the stream in a background task
        stream_task = asyncio.create_task(
            asyncio.to_thread(
                lambda: client.stream(
                    "POST", "/api/project/p1/agent/chat/stream",
                    json={"message": "Write chapter 1", "chapter_outline_id": "o1", "target_words": 100}
                )
            )
        )
        # Give the stream time to start and create the orchestrator
        await asyncio.sleep(0.1)

        # Call cancel
        cancel_response = client.post("/api/project/p1/agent/chat/cancel", json={})
        assert cancel_response.status_code == 200
        cancel_body = cancel_response.json()
        assert cancel_body["data"]["status"] == "ok"

        # Wait for the stream to finish
        response = await asyncio.wait_for(stream_task, timeout=3.0)
        with response as stream:
            content = ""
            for chunk in stream.iter_text():
                content += chunk
                if "done" in content:
                    break

        # Verify task status is cancelled in DB
        from app.models.agent_task import AgentTask
        task = db_session.query(AgentTask).filter(AgentTask.project_id == "p1").order_by(AgentTask.created_at.desc()).first()
        assert task is not None
        assert task.status == "cancelled"
    finally:
        agent_module.get_adapter = original_get_adapter
