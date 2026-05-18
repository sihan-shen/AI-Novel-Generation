def test_pytest_runs():
    assert 1 + 1 == 2


def test_app_imports(client):
    response = client.get("/")
    assert response.status_code == 200


def test_db_session_override_round_trip(client, db_session):
    """Inserting via db_session must be visible to a route that uses get_db."""
    from app.models.project import Project
    db_session.add(Project(id="smoke-p1", title="冒烟测试项目", description=""))
    db_session.commit()

    response = client.get("/projects/list")
    assert response.status_code == 200
    assert "冒烟测试项目" in response.text


def test_static_mount_exists(client):
    # 404 is fine — we just want to confirm /static/ is registered (not 405 Method Not Allowed)
    response = client.get("/static/nonexistent.js")
    assert response.status_code == 404
