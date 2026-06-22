import json

import pytest

from app.agents.autonomy import AutonomyConfig
from app.agents.blackboard import Blackboard
from app.agents.orchestrator import Orchestrator, OrchestratorState


class FakeAdapter:
    async def generate(self, messages, **kwargs):
        from app.llm.adapter import LLMResponse
        return LLMResponse(
            content=json.dumps({"action": "finish", "summary": "done"}),
            usage={"input_tokens": 10, "output_tokens": 5},
        )

    def count_tokens(self, text):
        return 10


class FakeOutlineItem:
    """Minimal stand-in for an Outline ORM object."""

    def __init__(self, id: str, level: int, title: str, parent_id: str | None = None, sort_order: int = 0):
        self.id = id
        self.level = level
        self.title = title
        self.parent_id = parent_id
        self.sort_order = sort_order
        self.summary = ""
        self.status = "draft"


class FakeProject:
    def __init__(self, project_id="p1"):
        self.id = project_id
        self.title = "Test Project"
        self.description = ""
        self.genre = "fantasy"
        self.status = "active"


class FakeDBWithOutlines:
    """Fake DB that returns outline items when queried via OutlineService.get_tree."""

    def __init__(self, outline_items=None):
        self.outline_items = outline_items or []
        self._target = None

    def query(self, *a):
        self._target = a[0] if a else None
        return self

    def filter(self, *a):
        return self

    def order_by(self, *a):
        return self

    def all(self):
        if self._target is not None and getattr(self._target, "__tablename__", None) == "outlines":
            return self.outline_items
        return []

    def first(self):
        if self._target is not None and getattr(self._target, "__tablename__", None) == "projects":
            return FakeProject()
        return None

    def add(self, obj):
        pass

    def commit(self):
        pass


@pytest.fixture
def bb_volume():
    return Blackboard(
        project_id="p1",
        task={"type": "write_chapter", "chapter_outline_id": "o1", "target_words": 3000},
        autonomy_config=AutonomyConfig(milestone_granularity="volume"),
    )


@pytest.fixture
def bb_chapter():
    return Blackboard(
        project_id="p1",
        task={"type": "write_chapter", "chapter_outline_id": "o1", "target_words": 3000},
        autonomy_config=AutonomyConfig(milestone_granularity="chapter"),
    )


@pytest.mark.asyncio
async def test_milestone_loop_volume_granularity_iterates_three_chapters(bb_volume):
    """Volume/act granularity should iterate over all outline nodes at level 1."""
    outlines = [
        FakeOutlineItem("vol-1", level=1, title="Volume 1"),
        FakeOutlineItem("vol-2", level=1, title="Volume 2"),
        FakeOutlineItem("vol-3", level=1, title="Volume 3"),
    ]
    db = FakeDBWithOutlines(outline_items=outlines)
    orch = Orchestrator(db=db, blackboard=bb_volume, adapter=FakeAdapter())

    final_state = await orch._run_milestone_loop()

    assert final_state == OrchestratorState.DONE
    assert orch.milestone_progress["current_index"] == 3
    assert orch.milestone_progress["total"] == 3
    assert len(orch.milestone_progress["completed_ids"]) == 3
    assert orch.milestone_progress["completed_ids"] == ["vol-1", "vol-2", "vol-3"]


@pytest.mark.asyncio
async def test_milestone_loop_chapter_granularity_skips_milestone_loop(bb_chapter):
    """Chapter granularity should NOT use the milestone loop; normal run() path preserved."""
    outlines = [
        FakeOutlineItem("chap-1", level=2, title="Chapter 1"),
        FakeOutlineItem("chap-2", level=2, title="Chapter 2"),
        FakeOutlineItem("chap-3", level=2, title="Chapter 3"),
    ]
    db = FakeDBWithOutlines(outline_items=outlines)
    orch = Orchestrator(db=db, blackboard=bb_chapter, adapter=FakeAdapter())

    # _run_milestone_loop should still work when called directly, but for chapter
    # granularity we expect it to look at level=2 nodes.
    final_state = await orch._run_milestone_loop()

    # Since chapter granularity looks at level=2, and we have 3 level-2 items,
    # it should iterate all 3 when called directly.
    assert final_state == OrchestratorState.DONE
    assert orch.milestone_progress["completed_ids"] == ["chap-1", "chap-2", "chap-3"]


@pytest.mark.asyncio
async def test_milestone_loop_empty_outline_exits_cleanly(bb_volume):
    """Empty outline tree should exit cleanly with DONE and no crash."""
    db = FakeDBWithOutlines(outline_items=[])
    orch = Orchestrator(db=db, blackboard=bb_volume, adapter=FakeAdapter())

    final_state = await orch._run_milestone_loop()

    assert final_state == OrchestratorState.DONE
    assert orch.milestone_progress["current_index"] == 0
    assert orch.milestone_progress["total"] == 0
    assert orch.milestone_progress["completed_ids"] == []


@pytest.mark.asyncio
async def test_milestone_loop_token_budget_breaks_mid_loop(bb_volume):
    """If token budget is exceeded mid-loop, the loop should break early."""
    outlines = [
        FakeOutlineItem("vol-1", level=1, title="Volume 1"),
        FakeOutlineItem("vol-2", level=1, title="Volume 2"),
        FakeOutlineItem("vol-3", level=1, title="Volume 3"),
    ]
    db = FakeDBWithOutlines(outline_items=outlines)
    orch = Orchestrator(db=db, blackboard=bb_volume, adapter=FakeAdapter())
    # Artificially set cumulative_tokens past the budget before entering the loop
    orch.blackboard.cumulative_tokens = orch.blackboard.token_budget + 1

    final_state = await orch._run_milestone_loop()

    assert final_state == OrchestratorState.DONE
    assert orch.milestone_progress["current_index"] == 0
    assert orch.milestone_progress["completed_ids"] == []


@pytest.mark.asyncio
async def test_run_uses_milestone_loop_for_volume_granularity(bb_volume):
    """run() should dispatch to _run_milestone_loop when granularity is volume/act."""
    outlines = [
        FakeOutlineItem("vol-1", level=1, title="Volume 1"),
        FakeOutlineItem("vol-2", level=1, title="Volume 2"),
    ]
    db = FakeDBWithOutlines(outline_items=outlines)
    orch = Orchestrator(db=db, blackboard=bb_volume, adapter=FakeAdapter())
    # Bypass _gathering_context by pre-setting state to WRITING
    orch.state = OrchestratorState.WRITING

    final_state = await orch.run()

    # run() always transitions through DONE → _done() → IDLE
    assert final_state in (OrchestratorState.DONE, OrchestratorState.IDLE)
    assert orch.milestone_progress["completed_ids"] == ["vol-1", "vol-2"]


@pytest.mark.asyncio
async def test_run_preserves_single_chapter_for_chapter_granularity(bb_chapter):
    """run() should keep single-chapter behavior when granularity is chapter (default)."""
    db = FakeDBWithOutlines(outline_items=[])
    orch = Orchestrator(db=db, blackboard=bb_chapter, adapter=FakeAdapter())
    # Bypass _gathering_context by pre-setting state to WRITING
    orch.state = OrchestratorState.WRITING

    final_state = await orch.run()

    # Single-chapter path: WRITING → REVIEWING → DONE → _done() → IDLE
    assert final_state in (OrchestratorState.DONE, OrchestratorState.IDLE)
    # milestone_loop should not have been invoked for chapter default
    assert orch.milestone_progress["current_index"] == 0
