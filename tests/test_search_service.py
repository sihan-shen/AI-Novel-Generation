from app.models.chapter import Chapter
from app.models.idea import Idea
from app.models.outline import Outline
from app.models.project import Project
from app.models.setting import Setting
from app.services.search_service import SearchService


def _seed(db):
    p1 = Project(id="p1", title="时间机器", description="科幻小说")
    p2 = Project(id="p2", title="魔法学院", description="奇幻设定")
    db.add_all([p1, p2])

    db.add(Chapter(id="c1", project_id="p1", title="第一章·命名风暴", content="魔法风暴肆虐", sort_order=1))
    db.add(Chapter(id="c2", project_id="p1", title="第二章·归来", content="主角归来", sort_order=2))

    db.add(Outline(id="o1", project_id="p1", title="主线·时间循环", summary="时间循环的核心", level=1, sort_order=1))

    db.add(Setting(id="s1", project_id="p2", name="魔法风暴系", category="体系", content="一种元素系魔法", summary=""))
    db.add(Idea(id="i1", project_id="p1", title="风暴起源", content="风暴的起源应当与古代仪式有关"))

    db.commit()


def test_search_returns_chapters_by_title(db_session):
    _seed(db_session)
    results = SearchService.search(db_session, q="命名风暴", type="all")
    assert any(r["id"] == "c1" and r["type"] == "chapter" for r in results)


def test_search_filters_by_type(db_session):
    _seed(db_session)
    results = SearchService.search(db_session, q="风暴", type="setting")
    assert all(r["type"] == "setting" for r in results)
    assert any(r["id"] == "s1" for r in results)


def test_search_returns_snippet(db_session):
    _seed(db_session)
    results = SearchService.search(db_session, q="时间循环", type="outline")
    assert len(results) == 1
    assert results[0]["snippet"] != ""


def test_search_attaches_project_title(db_session):
    _seed(db_session)
    results = SearchService.search(db_session, q="时间机器", type="project")
    assert results[0]["project_title"] is None  # project IS the project
    results = SearchService.search(db_session, q="命名风暴", type="chapter")
    assert results[0]["project_title"] == "时间机器"


def test_search_idea_by_title_or_content(db_session):
    _seed(db_session)
    by_title = SearchService.search(db_session, q="风暴起源", type="idea")
    assert any(r["id"] == "i1" for r in by_title)
    by_content = SearchService.search(db_session, q="古代仪式", type="idea")
    assert any(r["id"] == "i1" for r in by_content)


def test_search_respects_limit(db_session):
    _seed(db_session)
    results = SearchService.search(db_session, q="", type="all", limit=2)
    assert len(results) <= 2
