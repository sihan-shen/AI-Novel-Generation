import pytest
from app.models.project import Project


class TestProjectsAPI:
    def test_list_empty(self, client):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "ok"
        assert body["data"] == []

    def test_create_and_list(self, client, db_session):
        resp = client.post("/api/projects", json={
            "title": "测试项目",
            "description": "描述",
            "genre": "科幻",
        })
        assert resp.status_code == 201
        created = resp.json()["data"]
        assert created["title"] == "测试项目"

        resp = client.get("/api/projects")
        assert len(resp.json()["data"]) == 1

    def test_get_by_id(self, client, db_session):
        db_session.add(Project(id="p1", title="P1", description="", genre=""))
        db_session.commit()

        resp = client.get("/api/projects/p1")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "P1"

    def test_get_not_found(self, client):
        resp = client.get("/api/projects/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"

    def test_delete(self, client, db_session):
        db_session.add(Project(id="p2", title="P2", description="", genre=""))
        db_session.commit()

        resp = client.delete("/api/projects/p2")
        assert resp.status_code == 200

        resp = client.get("/api/projects")
        assert resp.json()["data"] == []
