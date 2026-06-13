from app.models.project import Project
from app.models.review import Review


class TestReviewsAPI:
    def _seed(self, db_session):
        db_session.add(Project(id="p1", title="Test", description="", genre=""))
        db_session.commit()

    def test_list_empty(self, client, db_session):
        self._seed(db_session)
        resp = client.get("/api/projects/p1/reviews")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_list_with_data(self, client, db_session):
        self._seed(db_session)
        db_session.add(Review(id="r1", project_id="p1", chapter_id="c1", scope="batch",
                              summary="{}", findings="[]"))
        db_session.commit()

        resp = client.get("/api/projects/p1/reviews")
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["scope"] == "batch"

    def test_get_detail(self, client, db_session):
        self._seed(db_session)
        db_session.add(Review(id="r2", project_id="p1", chapter_id="c1", scope="batch",
                              summary='{"score": 8}', findings='[{"issue": "typo"}]'))
        db_session.commit()

        resp = client.get("/api/projects/p1/reviews/r2")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["summary"]["score"] == 8
        assert body["findings"][0]["issue"] == "typo"
