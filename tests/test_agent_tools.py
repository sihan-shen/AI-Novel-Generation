import json
from app.models.project import Project
from app.models.outline import Outline
from app.models.setting import Setting
from app.models.chapter import Chapter
from app.agents.tools.writing import lookup_settings, get_outline_context, get_recent_chapters, write_chapter
from app.agents.tools.shared import search_any


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
