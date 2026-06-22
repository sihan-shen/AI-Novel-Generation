from app.models.chapter import Chapter
from app.models.chapter_snapshot import ChapterSnapshot
from app.models.project import Project


class TestRollbackAPI:
    def _seed_project(self, db_session, project_id="p1"):
        db_session.add(Project(id=project_id, title="Test", description="", genre=""))
        db_session.commit()

    def test_rollback_restores_content(self, client, db_session):
        self._seed_project(db_session)
        db_session.add(Chapter(id="c1", project_id="p1", title="new title", content="new", sort_order=0))
        db_session.add(ChapterSnapshot(id="s1", chapter_id="c1", task_id="t1", title="old title", content="old"))
        db_session.commit()

        resp = client.post("/api/projects/p1/chapters/c1/rollback?task_id=t1")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "restored"
        assert resp.json()["data"]["chapter_id"] == "c1"

        resp_get = client.get("/api/projects/p1/chapters/c1")
        assert resp_get.json()["data"]["content"] == "old"
        assert resp_get.json()["data"]["title"] == "old title"

    def test_rollback_no_snapshot(self, client, db_session):
        self._seed_project(db_session)
        db_session.add(Chapter(id="c1", project_id="p1", title="T", content="C", sort_order=0))
        db_session.commit()

        resp = client.post("/api/projects/p1/chapters/c1/rollback?task_id=nonexistent")
        assert resp.status_code == 404
        assert "No snapshot found" in resp.json()["detail"]

    def test_rollback_cross_project_guard(self, client, db_session):
        self._seed_project(db_session, project_id="p1")
        self._seed_project(db_session, project_id="p2")
        db_session.add(Chapter(id="c1", project_id="p1", title="T", content="C", sort_order=0))
        db_session.add(ChapterSnapshot(id="s1", chapter_id="c1", task_id="t1", title="S", content="S"))
        db_session.commit()

        resp = client.post("/api/projects/p2/chapters/c1/rollback?task_id=t1")
        assert resp.status_code == 404
