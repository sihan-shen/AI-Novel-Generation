from app.models.idea import Idea


class TestIdeasAPI:
    def test_list_empty(self, client):
        resp = client.get("/api/ideas")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_create_and_list(self, client, db_session):
        resp = client.post("/api/ideas", json={"title": "好点子", "content": "细节", "source": "手写"})
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["title"] == "好点子"

        resp = client.get("/api/ideas")
        assert len(resp.json()["data"]) == 1

    def test_delete(self, client, db_session):
        db_session.add(Idea(id="i1", project_id=None, title="删掉", content="", source="手写", sort_order=0))
        db_session.commit()

        resp = client.delete("/api/ideas/i1")
        assert resp.status_code == 200

        resp = client.get("/api/ideas")
        assert resp.json()["data"] == []
