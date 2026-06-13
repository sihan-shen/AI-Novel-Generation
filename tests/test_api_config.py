class TestConfigAPI:
    def test_get_config(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "ok"
        assert isinstance(body["data"], dict)

    def test_save_and_get(self, client):
        resp = client.post("/api/config", json={"llm_provider": "openai"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["llm_provider"] == "openai"

        # Verify persisted
        resp = client.get("/api/config")
        assert resp.json()["data"]["llm_provider"] == "openai"
