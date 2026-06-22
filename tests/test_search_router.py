from app.models.chapter import Chapter
from app.models.project import Project


def test_search_endpoint_returns_results(client, db_session):
    db_session.add(Project(id="p1", title="时间机器", description="科幻"))
    db_session.add(Chapter(id="c1", project_id="p1", title="第一章·命名风暴", content="魔法风暴", sort_order=1))
    db_session.commit()

    response = client.get("/api/search?q=命名风暴")
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert any(r["id"] == "c1" for r in body["results"])


def test_search_endpoint_type_filter(client, db_session):
    db_session.add(Project(id="p1", title="时间机器", description="科幻"))
    db_session.add(Chapter(id="c1", project_id="p1", title="风暴章", content="", sort_order=1))
    db_session.commit()

    response = client.get("/api/search?q=风暴&type=project")
    assert response.status_code == 200
    body = response.json()
    assert all(r["type"] == "project" for r in body["results"])


def test_search_endpoint_empty_query_returns_results(client, db_session):
    db_session.add(Project(id="p1", title="时间机器", description=""))
    db_session.commit()

    response = client.get("/api/search?q=")
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) >= 1


def test_search_endpoint_invalid_type_returns_empty(client, db_session):
    response = client.get("/api/search?q=x&type=bogus")
    assert response.status_code == 200
    assert response.json() == {"results": [], "total": 0}
