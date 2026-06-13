def test_pytest_runs():
    assert 1 + 1 == 2


def test_app_imports(client):
    response = client.get("/api/projects")
    assert response.status_code == 200


def test_db_session_override_round_trip(client, db_session):
    """Inserting via db_session must be visible to the JSON API route."""
    from app.models.project import Project
    db_session.add(Project(id="smoke-p1", title="冒烟测试项目", description=""))
    db_session.commit()

    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()["data"]
    assert any(p["title"] == "冒烟测试项目" for p in data)


def test_openapi_spec_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "paths" in spec
    assert "/api/projects" in spec["paths"]
