from fastapi.testclient import TestClient

from web.main import app


def test_healthcheck_is_database_independent():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_screen_renders_without_database_connection():
    response = TestClient(app).get("/login")
    assert response.status_code == 200
    assert "Welcome back" in response.text
    assert 'name="csrf_token"' in response.text


def test_protected_route_redirects_to_login_without_database_lookup():
    response = TestClient(app).get("/sales", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?next=/sales")


def test_login_rejects_external_redirect_destination():
    response = TestClient(app).get("/login?next=https://example.com")
    assert response.status_code == 200
    assert 'name="next" value="/"' in response.text
