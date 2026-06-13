import pytest
from app.models.project import Project
from app.models.setting import Setting


class TestSettingsAPI:
    def _seed(self, db_session):
        db_session.add(Project(id="p1", title="Test", description="", genre=""))
        db_session.commit()

    def test_list_empty(self, client, db_session):
        self._seed(db_session)
        resp = client.get("/api/projects/p1/settings")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_create_and_list(self, client, db_session):
        self._seed(db_session)
        resp = client.post("/api/projects/p1/settings", json={
            "project_id": "p1", "category": "人物", "name": "张三", "summary": "主角",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "张三"

        resp = client.get("/api/projects/p1/settings")
        assert len(resp.json()["data"]) == 1

    def test_get_by_id(self, client, db_session):
        self._seed(db_session)
        db_session.add(Setting(id="s1", project_id="p1", category="人物", name="李四",
                               summary="", content="", weight=5, key="", tags="[]"))
        db_session.commit()

        resp = client.get("/api/projects/p1/settings/s1")
        assert resp.status_code == 200
        assert resp.json()["data"]["setting"]["name"] == "李四"

    def test_update(self, client, db_session):
        self._seed(db_session)
        db_session.add(Setting(id="s2", project_id="p1", category="人物", name="旧名",
                               summary="", content="", weight=5, key="", tags="[]"))
        db_session.commit()

        resp = client.put("/api/projects/p1/settings/s2", json={"name": "新名"})
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "新名"

    def test_delete(self, client, db_session):
        self._seed(db_session)
        db_session.add(Setting(id="s3", project_id="p1", category="人物", name="删掉",
                               summary="", content="", weight=5, key="", tags="[]"))
        db_session.commit()

        resp = client.delete("/api/projects/p1/settings/s3")
        assert resp.status_code == 200

        resp = client.get("/api/projects/p1/settings")
        assert resp.json()["data"] == []

    def test_category_filter(self, client, db_session):
        self._seed(db_session)
        db_session.add(Setting(id="s4", project_id="p1", category="人物", name="王五",
                               summary="", content="", weight=5, key="", tags="[]"))
        db_session.add(Setting(id="s5", project_id="p1", category="地理", name="城池",
                               summary="", content="", weight=5, key="", tags="[]"))
        db_session.commit()

        resp = client.get("/api/projects/p1/settings?category=人物")
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name"] == "王五"

    def test_get_not_found(self, client, db_session):
        self._seed(db_session)
        resp = client.get("/api/projects/p1/settings/nonexistent")
        assert resp.status_code == 404
