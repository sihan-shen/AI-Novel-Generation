import pytest
from app.models.project import Project
from app.models.outline import Outline


class TestOutlinesAPI:
    def _seed_project(self, db_session):
        db_session.add(Project(id="p1", title="Test", description="", genre=""))
        db_session.commit()

    def test_list_empty(self, client, db_session):
        self._seed_project(db_session)
        resp = client.get("/api/projects/p1/outlines")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_create_and_list(self, client, db_session):
        self._seed_project(db_session)
        resp = client.post("/api/projects/p1/outlines", json={
            "project_id": "p1", "level": 1, "title": "第一卷",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["title"] == "第一卷"
        assert data["level"] == 1

        resp = client.get("/api/projects/p1/outlines")
        assert len(resp.json()["data"]) == 1

    def test_get_by_id(self, client, db_session):
        self._seed_project(db_session)
        db_session.add(Outline(id="o1", project_id="p1", level=1, title="卷二", sort_order=0))
        db_session.commit()

        resp = client.get("/api/projects/p1/outlines/o1")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "卷二"

    def test_update(self, client, db_session):
        self._seed_project(db_session)
        db_session.add(Outline(id="o2", project_id="p1", level=1, title="旧标题", sort_order=0))
        db_session.commit()

        resp = client.put("/api/projects/p1/outlines/o2", json={"title": "新标题"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "新标题"

    def test_delete(self, client, db_session):
        self._seed_project(db_session)
        db_session.add(Outline(id="o3", project_id="p1", level=1, title="删掉", sort_order=0))
        db_session.commit()

        resp = client.delete("/api/projects/p1/outlines/o3")
        assert resp.status_code == 200

        resp = client.get("/api/projects/p1/outlines")
        assert resp.json()["data"] == []

    def test_get_not_found(self, client, db_session):
        self._seed_project(db_session)
        resp = client.get("/api/projects/p1/outlines/nonexistent")
        assert resp.status_code == 404
