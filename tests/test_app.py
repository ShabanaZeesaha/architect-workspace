from src.app import create_app


def test_health_returns_ok():
    client = create_app().test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_version_returns_string():
    client = create_app().test_client()

    response = client.get("/version")

    assert response.status_code == 200
    assert response.get_json() == {"version": "0.1.0"}
