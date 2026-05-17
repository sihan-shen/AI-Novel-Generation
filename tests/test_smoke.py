def test_pytest_runs():
    assert 1 + 1 == 2


def test_app_imports(client):
    response = client.get("/")
    assert response.status_code == 200
