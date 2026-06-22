import json

from app.agents.tools.shared import search_any
from app.agents.tools.writing import (
    get_outline_context,
    get_recent_chapters,
    lookup_settings,
    write_chapter,
)
from app.models.chapter import Chapter
from app.models.outline import Outline
from app.models.project import Project
from app.models.setting import Setting


def test_lookup_settings_finds_by_keyword(db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Setting(id="s1", project_id="p1", category="世界观", name="魔法体系", summary="一种古老的魔法", content="详细信息...", key="magic", weight=5, status="active"))
    db_session.add(Setting(id="s2", project_id="p1", category="人物", name="主角", summary="一个普通人", status="active"))
    db_session.commit()
    result = json.loads(lookup_settings(db_session, keywords=["魔法"], project_id="p1"))
    assert len(result) == 1
    assert result[0]["name"] == "魔法体系"


def test_get_outline_context(db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Outline(id="o1", project_id="p1", parent_id=None, level=1, sort_order=1, title="卷一"))
    db_session.add(Outline(id="o2", project_id="p1", parent_id="o1", level=2, sort_order=1, title="第一章"))
    db_session.add(Outline(id="o3", project_id="p1", parent_id="o1", level=2, sort_order=2, title="第二章"))
    db_session.commit()
    result = json.loads(get_outline_context(db_session, project_id="p1"))
    assert len(result) == 3
    focused = json.loads(get_outline_context(db_session, project_id="p1", outline_id="o2"))
    assert focused["current"]["title"] == "第一章"
    assert focused["parent"]["title"] == "卷一"
    assert len(focused["siblings"]) == 1


def test_get_recent_chapters(db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Chapter(id="c1", project_id="p1", title="Ch1", content="aaa", sort_order=1))
    db_session.add(Chapter(id="c2", project_id="p1", title="Ch2", content="bbb", sort_order=2))
    db_session.add(Chapter(id="c3", project_id="p1", title="Ch3", content="ccc", sort_order=3))
    db_session.commit()
    result = json.loads(get_recent_chapters(db_session, project_id="p1", count=2))
    assert len(result) == 2


def test_write_chapter_draft_mode(db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.commit()
    result = json.loads(write_chapter(db_session, project_id="p1", outline_id="o1", title="New Chapter", content="Once upon a time...", write_mode="draft", task_id="t1"))
    assert result["status"] == "created"
    ch = db_session.query(Chapter).first()
    assert ch.title == "New Chapter"
    assert ch.status == "draft"
    assert ch.generated_by_type == "agent"


def test_write_chapter_draft_mode_upserts(db_session):
    db_session.add(Project(id="p1", title="Test Project"))
    db_session.add(Chapter(id="c1", project_id="p1", outline_id="o1", title="Old", content="old content", sort_order=1, status="draft"))
    db_session.commit()
    result = json.loads(write_chapter(db_session, project_id="p1", outline_id="o1", title="Updated", content="new content", write_mode="draft", task_id="t1"))
    assert result["status"] == "updated"


def test_search_any(db_session):
    db_session.add(Project(id="p1", title="时间机器"))
    db_session.commit()
    result = json.loads(search_any(db_session, q="时间", type="project"))
    assert len(result) >= 1
    assert result[0]["title"] == "时间机器"


def test_search_any_project_scoped(db_session):
    """search_any with project_id only returns rows from that project."""
    db_session.add(Project(id="p1", title="Project Alpha"))
    db_session.add(Project(id="p2", title="Project Beta"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", summary="Alice in p1", content="...", key="alice", weight=1, status="active"))
    db_session.add(Setting(id="s2", project_id="p2", category="人物", name="Bob", summary="Bob in p2", content="...", key="bob", weight=1, status="active"))
    db_session.commit()

    result = json.loads(search_any(db_session, q="Alice", type="setting", project_id="p1"))
    assert len(result) == 1
    assert result[0]["title"] == "Alice"

    # The OTHER project's setting must NOT appear
    result_other = json.loads(search_any(db_session, q="Bob", type="setting", project_id="p1"))
    assert len(result_other) == 0


def test_search_any_project_id_none_fallback_global(db_session):
    """project_id=None falls back to global search (backward compat)."""
    db_session.add(Project(id="p1", title="Project Alpha"))
    db_session.add(Project(id="p2", title="Project Beta"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", summary="Alice in p1", content="...", key="alice", weight=1, status="active"))
    db_session.add(Setting(id="s2", project_id="p2", category="人物", name="Bob", summary="Bob in p2", content="...", key="bob", weight=1, status="active"))
    db_session.commit()

    result = json.loads(search_any(db_session, q="", type="setting", project_id=None))
    assert len(result) == 2


def test_writer_search_any_tool_is_project_scoped(db_session):
    """Writer agent's search_any handler passes project_id."""
    from app.agents.agents.writer import build_writer_config
    from app.agents.autonomy import AutonomyConfig
    from app.agents.blackboard import Blackboard

    db_session.add(Project(id="p1", title="Project Alpha"))
    db_session.add(Project(id="p2", title="Project Beta"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", summary="Alice in p1", content="...", key="alice", weight=1, status="active"))
    db_session.add(Setting(id="s2", project_id="p2", category="人物", name="Bob", summary="Bob in p2", content="...", key="bob", weight=1, status="active"))
    db_session.commit()

    bb = Blackboard(project_id="p1", task={"type": "writing"}, autonomy_config=AutonomyConfig())
    config = build_writer_config(db_session, project_id="p1", blackboard=bb)
    search_tool = next(t for t in config.tools if t.name == "search_any")
    result = json.loads(search_tool.handler(q="Alice"))
    assert len(result) == 1
    assert result[0]["title"] == "Alice"

    # Must NOT find the other project's setting
    result_other = json.loads(search_tool.handler(q="Bob"))
    assert len(result_other) == 0


def test_reviewer_search_any_tool_is_project_scoped(db_session):
    """Reviewer agent's search_any handler passes project_id."""
    from app.agents.agents.reviewer import build_reviewer_config
    from app.agents.autonomy import AutonomyConfig
    from app.agents.blackboard import Blackboard

    db_session.add(Project(id="p1", title="Project Alpha"))
    db_session.add(Project(id="p2", title="Project Beta"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", summary="Alice in p1", content="...", key="alice", weight=1, status="active"))
    db_session.add(Setting(id="s2", project_id="p2", category="人物", name="Bob", summary="Bob in p2", content="...", key="bob", weight=1, status="active"))
    db_session.commit()

    bb = Blackboard(project_id="p1", task={"type": "review"}, autonomy_config=AutonomyConfig())
    config = build_reviewer_config(db_session, project_id="p1", chapter_id="c1", blackboard=bb)
    search_tool = next(t for t in config.tools if t.name == "search_any")
    result = json.loads(search_tool.handler(q="Alice"))
    assert len(result) == 1
    assert result[0]["title"] == "Alice"

    result_other = json.loads(search_tool.handler(q="Bob"))
    assert len(result_other) == 0


def test_settings_mgr_search_any_tool_is_project_scoped(db_session):
    """Settings manager agent's search_any handler passes project_id."""
    from app.agents.agents.settings_mgr import build_settings_mgr_config
    from app.agents.autonomy import AutonomyConfig
    from app.agents.blackboard import Blackboard

    db_session.add(Project(id="p1", title="Project Alpha"))
    db_session.add(Project(id="p2", title="Project Beta"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", summary="Alice in p1", content="...", key="alice", weight=1, status="active"))
    db_session.add(Setting(id="s2", project_id="p2", category="人物", name="Bob", summary="Bob in p2", content="...", key="bob", weight=1, status="active"))
    db_session.commit()

    bb = Blackboard(project_id="p1", task={"type": "settings"}, autonomy_config=AutonomyConfig())
    config = build_settings_mgr_config(db_session, project_id="p1", blackboard=bb)
    search_tool = next(t for t in config.tools if t.name == "search_any")
    result = json.loads(search_tool.handler(q="Alice"))
    assert len(result) == 1
    assert result[0]["title"] == "Alice"

    result_other = json.loads(search_tool.handler(q="Bob"))
    assert len(result_other) == 0


def test_brainstorm_search_any_tool_is_project_scoped(db_session):
    """Brainstorm agent's search_any handler passes project_id."""
    from app.agents.agents.brainstorm import build_brainstorm_config

    db_session.add(Project(id="p1", title="Project Alpha"))
    db_session.add(Project(id="p2", title="Project Beta"))
    db_session.add(Setting(id="s1", project_id="p1", category="人物", name="Alice", summary="Alice in p1", content="...", key="alice", weight=1, status="active"))
    db_session.add(Setting(id="s2", project_id="p2", category="人物", name="Bob", summary="Bob in p2", content="...", key="bob", weight=1, status="active"))
    db_session.commit()

    config = build_brainstorm_config(db_session, project_id="p1", task_id="t1")
    search_tool = next(t for t in config.tools if t.name == "search_any")
    result = json.loads(search_tool.handler(q="Alice"))
    assert len(result) == 1
    assert result[0]["title"] == "Alice"

    result_other = json.loads(search_tool.handler(q="Bob"))
    assert len(result_other) == 0


def test_brainstorm_config_includes_list_pending_inspirations(db_session):
    """build_brainstorm_config tools list includes list_pending_inspirations."""
    from app.agents.agents.brainstorm import build_brainstorm_config

    config = build_brainstorm_config(db_session, project_id="p1", task_id="t1")
    tool_names = {t.name for t in config.tools}
    assert "list_pending_inspirations" in tool_names


def test_list_pending_inspirations_tool(db_session):
    """list_pending_inspirations returns pending inspirations."""
    from app.agents.agents.brainstorm import build_brainstorm_config
    from app.models.agent_task import AgentTask

    db_session.add(Project(id="p1", title="Test"))
    task = AgentTask(id="t1", project_id="p1", task_type="brainstorm", status="running")
    db_session.add(task)
    db_session.commit()

    config = build_brainstorm_config(db_session, project_id="p1", task_id="t1")
    tool = next(t for t in config.tools if t.name == "list_pending_inspirations")
    result = json.loads(tool.handler())
    assert result == []

    from app.agents.tools.brainstorm import save_inspiration
    save_inspiration(db_session, task_id="t1", insp_type="idea", title="Idea 1", content="content")

    result = json.loads(tool.handler())
    assert len(result) == 1
    assert result[0]["title"] == "Idea 1"
