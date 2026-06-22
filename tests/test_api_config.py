import contextlib


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

    def test_get_config_masks_api_key(self, client):
        """GET /api/config must NOT return raw api_key. It should return
        api_key_set (bool) and api_key_masked (str in 'sk-...xxxx' format).
        """
        secret = "sk-abc123456789XYZ"  # 17 chars; last 4 = "9XYZ"
        # Save a real key
        resp = client.post("/api/config", json={"api_key": secret})
        assert resp.status_code == 200

        # GET should not expose the raw key
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "api_key" not in data, "raw api_key must not leak in GET response"
        assert "api_key_set" in data
        assert "api_key_masked" in data
        assert data["api_key_set"] is True
        # Format: first 3 chars + "..." + last 4 chars of the secret
        assert data["api_key_masked"].endswith("9XYZ")
        assert data["api_key_masked"].startswith("sk-")
        # The middle must be redacted
        assert secret not in data["api_key_masked"]

        # Empty key -> both indicators reflect "not set"
        resp = client.post("/api/config", json={"api_key": ""})
        assert resp.status_code == 200
        resp = client.get("/api/config")
        data = resp.json()["data"]
        assert data["api_key_set"] is False
        assert data["api_key_masked"] == ""

    def test_save_config_still_accepts_raw_key(self, client):
        """POST /api/config must still accept raw api_key and persist it,
        so get_adapter() can read the real key from get_all().
        """
        from app.database import get_db
        from app.services.config_service import ConfigService

        secret = "sk-persisted1234567"
        resp = client.post("/api/config", json={"api_key": secret})
        assert resp.status_code == 200

        # Verify raw key is stored by reading via get (internal API)
        db_gen = get_db()
        db = next(db_gen)
        try:
            raw = ConfigService.get(db, "api_key")
            assert raw == secret, "raw api_key must be preserved in storage"
        finally:
            with contextlib.suppress(StopIteration):
                next(db_gen)
