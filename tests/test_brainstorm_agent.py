"""Tests for Brainstorm Agent."""
import json

import pytest

from app.agents.agents.brainstorm import build_brainstorm_config
from app.agents.tools.brainstorm import save_inspiration
from app.models.agent_task import AgentTask
from app.models.project import Project


def test_build_brainstorm_config(db_session):
    """Brainstorm config has the expected tools and settings."""
    config = build_brainstorm_config(
        db=db_session, project_id="p1", task_id="t1",
    )
    assert config.model == ""
    assert config.temperature == 0.9
    assert config.max_steps == 50
    assert config.token_budget == 100_000

    tool_names = {t.name for t in config.tools}
    assert "lookup_settings" in tool_names
    assert "get_outline_context" in tool_names
    assert "search_any" in tool_names
    assert "save_inspiration" in tool_names


def test_save_inspiration_adds_to_pending(db_session):
    """save_inspiration accumulates proposals in task.task_metadata."""
    db_session.add(Project(id="p1", title="Test"))
    task = AgentTask(
        id="t1", project_id="p1", task_type="brainstorm",
        status="running",
    )
    db_session.add(task)
    db_session.commit()

    result = save_inspiration(
        db=db_session, task_id="t1",
        insp_type="idea", title="主角设定", content="一个退役的佣兵",
    )
    data = json.loads(result)
    assert data["status"] == "proposed"
    assert data["pending_count"] == 1

    # Verify persisted
    db_session.refresh(task)
    pending = task.task_metadata.get("pending_inspirations", [])
    assert len(pending) == 1
    assert pending[0]["title"] == "主角设定"
    assert pending[0]["type"] == "idea"


def test_save_inspiration_multiple_accumulates(db_session):
    """Multiple save_inspiration calls all accumulate."""
    db_session.add(Project(id="p1", title="Test"))
    task = AgentTask(
        id="t1", project_id="p1", task_type="brainstorm",
        status="running",
    )
    db_session.add(task)
    db_session.commit()

    save_inspiration(db=db_session, task_id="t1", insp_type="idea", title="A", content="a")
    save_inspiration(db=db_session, task_id="t1", insp_type="setting", title="B", content="b")

    db_session.refresh(task)
    pending = task.task_metadata.get("pending_inspirations", [])
    assert len(pending) == 2


@pytest.mark.asyncio
async def test_run_agent_handoff_action():
    """run_agent returns status='handoff' when agent emits handoff action."""
    from app.agents.autonomy import AutonomyConfig
    from app.agents.base import AgentConfig, run_agent
    from app.agents.blackboard import Blackboard

    bb = Blackboard(
        project_id="p1",
        task={"type": "brainstorm"},
        autonomy_config=AutonomyConfig(),
    )

    class FakeAdapter:
        async def generate(self, messages, **kwargs):
            from app.llm.adapter import LLMResponse
            return LLMResponse(
                content=json.dumps({"action": "handoff", "summary": "切换到写作"}),
                usage={"input_tokens": 10, "output_tokens": 5},
            )

        def count_tokens(self, text):
            return 10

    config = AgentConfig(
        system_prompt="You brainstorm.",
        tools=[],
        model="claude-sonnet-4-6",
    )

    result = await run_agent(config, bb, FakeAdapter())
    assert result.status == "handoff"
    assert result.output == "切换到写作"


def testdetect_intent_brainstorm():
    """Intent detection classifies brainstorm requests."""
    from app.routers.agent.brainstorm import detect_intent

    class FakeIntentAdapter:
        async def generate(self, messages, **kwargs):
            import re

            from app.llm.adapter import LLMResponse
            msg = messages[-1]["content"]
            # Extract user message from prompt template: 用户消息: "<message>"
            m = re.search(r'用户消息:\s*"(.+?)"', msg)
            user_msg = m.group(1) if m else msg
            # Simulate intent classification based on Chinese keywords
            if "脑暴" in user_msg or "灵感" in user_msg or "创意" in user_msg:
                return LLMResponse(
                    content=json.dumps({"intent": "brainstorm"}),
                    usage={"input_tokens": 10, "output_tokens": 3},
                )
            elif "写" in user_msg or "章节" in user_msg:
                return LLMResponse(
                    content=json.dumps({"intent": "writing"}),
                    usage={"input_tokens": 10, "output_tokens": 3},
                )
            return LLMResponse(
                content=json.dumps({"intent": "other"}),
                usage={"input_tokens": 10, "output_tokens": 3},
            )

        def count_tokens(self, text):
            return 10

    adapter = FakeIntentAdapter()

    import asyncio
    assert asyncio.run(detect_intent(adapter, "帮我脑暴一下主角设定")) == "brainstorm"
    assert asyncio.run(detect_intent(adapter, "帮我写第一章")) == "writing"
    assert asyncio.run(detect_intent(adapter, "你好")) == "other"



