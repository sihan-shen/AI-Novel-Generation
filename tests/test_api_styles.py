from app.models.style import Style


class TestStylesAPI:
    def test_list_empty(self, client):
        resp = client.get("/api/styles")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_create_then_list(self, client, db_session):
        db_session.add(Style(id="s1", name="鲁迅风", source="manual", source_text="", analysis="冷峻"))
        db_session.commit()

        resp = client.get("/api/styles")
        assert len(resp.json()["data"]) == 1

    def test_delete(self, client, db_session):
        db_session.add(Style(id="s2", name="测试", source="manual", source_text="", analysis=""))
        db_session.commit()

        resp = client.delete("/api/styles/s2")
        assert resp.status_code == 200

        resp = client.get("/api/styles")
        assert len(resp.json()["data"]) == 0
