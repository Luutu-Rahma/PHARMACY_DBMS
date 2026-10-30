import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))
os.environ.setdefault("SESSION_SECRET", "test-session-secret-which-is-longer-than-thirty-two-characters")
os.environ.setdefault("COOKIE_SECURE", "false")

import auth
import db
import main


@pytest.mark.parametrize(
    ("role", "allowed", "denied"),
    [
        ("Admin", "sales", "not-a-page"),
        ("InventoryManager", "inventory", "users"),
        ("Pharmacist", "drugs", "sales"),
        ("Cashier", "sales", "reports"),
    ],
)
def test_role_permissions(role, allowed, denied):
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b"", "server": ("test", 80), "client": ("test", 1), "scheme": "http", "session": {"user": {"id": 8, "name": "Test User", "role": role}}}
    request = Request(scope)
    assert auth.require_role(request, allowed)["role"] == role
    with pytest.raises(HTTPException) as error:
        auth.require_role(request, denied)
    assert error.value.status_code == 403


def test_unauthenticated_sales_is_redirected(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-which-is-longer-than-thirty-two-characters")
    from fastapi.testclient import TestClient

    with TestClient(main.app) as client:
        response = client.get("/sales", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_checks_legacy_sha256_database_query(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-which-is-longer-than-thirty-two-characters")
    from fastapi.testclient import TestClient

    calls = []

    def fake_fetch_one(sql, params=()):
        calls.append((sql, params))
        return {"UserID": 12, "FullName": "Test Pharmacist", "Role": "Pharmacist"}

    monkeypatch.setattr(main, "fetch_one", fake_fetch_one)
    with TestClient(main.app) as client:
        login_page = client.get("/login")
        token = client.cookies.get("pharmaflow_session")
        assert token
        # CSRF token is present as a hidden input; extract it without HTML parsing dependencies.
        import re
        csrf = re.search(r'name="_csrf" value="([^"]+)"', login_page.text).group(1)
        response = client.post("/login", data={"username": "test", "password": "hidden", "_csrf": csrf}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert calls[0][1] == ("test", "hidden")
    assert "Password=SHA2(%s,256)" in calls[0][0]


def test_login_rejects_bad_csrf_without_database_access(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-which-is-longer-than-thirty-two-characters")
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main, "fetch_one", lambda *_: pytest.fail("DB must not be queried"))
    with TestClient(main.app) as client:
        response = client.post("/login", data={"username": "test", "password": "hidden", "_csrf": "bad"})
    assert response.status_code == 403


@pytest.mark.parametrize(("value", "expected"), [("1", 1), ("500", 500)])
def test_positive_integer_validation(value, expected):
    assert main.parse_positive_int(value, "Quantity") == expected


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "9999999999", "not-a-number"])
def test_positive_integer_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        main.parse_positive_int(value, "Quantity")


def test_price_validation():
    assert str(main.parse_price("12.3")) == "12.30"
    for value in ("0", "-4", "nan", "inf", "invalid"):
        with pytest.raises(ValueError):
            main.parse_price(value)


def test_safe_database_errors_never_return_connection_values():
    error = db.DatabaseUnavailable("TLS verification or network connection failed. Check the Aiven CA certificate and network access.")
    message = main.safe_db_message(error)
    assert "password" not in message.lower()
    assert "mysql://" not in message
    assert "TLS verification" in message


def test_settings_require_aiven_ca_and_never_accept_localhost(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "mysql://user:secret@mysql.example.aivencloud.com:19151/defaultdb?ssl-mode=REQUIRED")
    monkeypatch.delenv("AIVEN_CA_CERT", raising=False)
    with pytest.raises(db.DatabaseConfigurationError, match="AIVEN_CA_CERT"):
        db.settings_from_env()

    cert = tmp_path / "ca.pem"
    cert.write_text("test-only")
    monkeypatch.setenv("AIVEN_CA_CERT", str(cert))
    config = db.settings_from_env()
    assert config.host == "mysql.example.aivencloud.com"
    assert config.port == 19151

    monkeypatch.setenv("DATABASE_URL", "mysql://user:secret@localhost:3306/defaultdb?ssl-mode=REQUIRED")
    with pytest.raises(db.DatabaseConfigurationError, match="Aiven"):
        db.settings_from_env()


def test_connection_error_message_is_safe():
    assert "password" in db._safe_connection_message(Exception(1045))
    assert "mysql://" not in db._safe_connection_message(Exception("secret connection string"))


def test_authenticated_pages_render_without_live_database(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-which-is-longer-than-thirty-two-characters")
    from fastapi.testclient import TestClient
    import re

    def fake_fetch_one(sql, params=()):
        if "WHERE UserName=%s" in sql:
            return {"UserID": 5, "FullName": "Test Administrator", "Role": "Admin"}
        if "drug_count" in sql:
            return {"drug_count": 0, "sellable": 0}
        if "DATEDIFF" in sql and "COUNT(*) AS n" in sql:
            return {"n": 0}
        if "COUNT(*) AS n" in sql:
            return {"n": 0, "total": 0}
        return None

    monkeypatch.setattr(main, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(main, "fetch_all", lambda *_: [])
    with TestClient(main.app) as client:
        login_page = client.get("/login")
        csrf = re.search(r'name="_csrf" value="([^"]+)"', login_page.text).group(1)
        client.post("/login", data={"username": "admin", "password": "hidden", "_csrf": csrf})
        for path in ("/dashboard", "/sales", "/inventory", "/catalogue/drugs", "/catalogue/suppliers", "/catalogue/categories", "/reports", "/drugs", "/stock", "/users"):
            response = client.get(path)
            assert response.status_code == 200, (path, response.text[:300])


def test_pharmacist_cannot_open_admin_or_sales_pages(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-which-is-longer-than-thirty-two-characters")
    from fastapi.testclient import TestClient
    import re

    monkeypatch.setattr(main, "fetch_one", lambda sql, params=(): {"UserID": 4, "FullName": "Test Pharmacist", "Role": "Pharmacist"})
    monkeypatch.setattr(main, "fetch_all", lambda *_: [])
    with TestClient(main.app) as client:
        login_page = client.get("/login")
        csrf = re.search(r'name="_csrf" value="([^"]+)"', login_page.text).group(1)
        client.post("/login", data={"username": "pharmacist", "password": "hidden", "_csrf": csrf})
        assert client.get("/reports").status_code == 200
        assert client.get("/sales").status_code == 403
        assert client.get("/users").status_code == 403
