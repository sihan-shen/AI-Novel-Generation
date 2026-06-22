from app.models.chapter import Chapter
from app.models.project import Project


class TestChaptersAPI:
    def _seed(self, db_session):
        db_session.add(Project(id="p1", title="Test", description="", genre=""))
        db_session.commit()

    def test_list_empty(self, client, db_session):
        self._seed(db_session)
        resp = client.get("/api/projects/p1/chapters")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_create_and_list(self, client, db_session):
        self._seed(db_session)
        resp = client.post("/api/projects/p1/chapters", json={
            "project_id": "p1", "title": "第一章",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["title"] == "第一章"

        resp = client.get("/api/projects/p1/chapters")
        assert len(resp.json()["data"]) == 1

    def test_get_by_id(self, client, db_session):
        self._seed(db_session)
        db_session.add(Chapter(id="c1", project_id="p1", title="C1", content="", sort_order=0))
        db_session.commit()

        resp = client.get("/api/projects/p1/chapters/c1")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "C1"

    def test_update(self, client, db_session):
        self._seed(db_session)
        db_session.add(Chapter(id="c2", project_id="p1", title="旧标题", content="", sort_order=0))
        db_session.commit()

        resp = client.put("/api/projects/p1/chapters/c2", json={"title": "新标题"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "新标题"

    def test_delete(self, client, db_session):
        self._seed(db_session)
        db_session.add(Chapter(id="c3", project_id="p1", title="删掉", content="", sort_order=0))
        db_session.commit()

        resp = client.delete("/api/projects/p1/chapters/c3")
        assert resp.status_code == 200

        resp = client.get("/api/projects/p1/chapters")
        assert resp.json()["data"] == []

    def test_get_not_found(self, client, db_session):
        self._seed(db_session)
        resp = client.get("/api/projects/p1/chapters/nonexistent")
        assert resp.status_code == 404
