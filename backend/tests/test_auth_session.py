import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth import COOKIE_NAME
from app.db import db_path
from app.main import app

EMAIL = "a@x.com"
PASSWORD = "password1"


def _signup(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/signup", json={"email": email, "password": password})


def _login(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _sessions():
    conn = sqlite3.connect(db_path())
    try:
        return conn.execute("SELECT token_hash, user_id, expires_at FROM sessions").fetchall()
    finally:
        conn.close()


@pytest.fixture
def client(anon_client):
    """세션 테스트는 로그인하지 않은 상태에서 시작한다."""
    return anon_client


@pytest.fixture
def registered(client):
    assert _signup(client).status_code == 201
    return client


def test_login_success_sets_http_only_cookie_and_me_works(registered):
    r = _login(registered)
    assert r.status_code == 200
    assert set(r.json()) == {"id", "email"}
    assert r.json()["email"] == EMAIL
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE_NAME}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=604800" in cookie
    me = registered.get("/auth/me")
    assert me.status_code == 200
    assert me.json() == r.json()


def test_login_normalizes_email(registered):
    assert _login(registered, email="  A@X.COM ").status_code == 200


def test_wrong_password_and_unknown_email_look_identical(registered):
    wrong = _login(registered, password="not-the-password")
    unknown = _login(registered, email="nobody@x.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["detail"]["code"] == "INVALID_CREDENTIALS"
    assert "set-cookie" not in wrong.headers and "set-cookie" not in unknown.headers
    assert _sessions() == []


def test_login_with_missing_fields_is_401(registered):
    r = registered.post("/auth/login", json={})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_me_without_cookie_is_401(client):
    r = client.get("/auth/me")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "UNAUTHORIZED"


def test_me_with_tampered_cookie_is_401(registered):
    _login(registered)
    registered.cookies.set(COOKIE_NAME, "tampered-token")
    assert registered.get("/auth/me").status_code == 401


def test_logout_ends_session_and_old_cookie_cannot_be_reused(registered):
    _login(registered)
    old_token = registered.cookies.get(COOKIE_NAME)
    r = registered.post("/auth/logout")
    assert r.status_code == 204
    assert f"{COOKIE_NAME}=" in r.headers["set-cookie"]
    assert "Max-Age=0" in r.headers["set-cookie"]
    assert _sessions() == []
    assert registered.get("/auth/me").status_code == 401
    registered.cookies.set(COOKIE_NAME, old_token)
    assert registered.get("/auth/me").status_code == 401


def test_logout_without_session_is_204(client):
    assert client.post("/auth/logout").status_code == 204


def test_expired_session_is_401_and_removed(registered):
    _login(registered)
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    conn = sqlite3.connect(db_path())
    conn.execute("UPDATE sessions SET expires_at = ?", (past,))
    conn.commit()
    conn.close()
    assert registered.get("/auth/me").status_code == 401
    assert _sessions() == []


def test_db_does_not_store_raw_token(registered):
    _login(registered)
    token = registered.cookies.get(COOKIE_NAME)
    [(token_hash, user_id, expires_at)] = _sessions()
    assert token not in (token_hash, str(user_id), expires_at)
    assert len(token_hash) == 64 and int(token_hash, 16) >= 0
    conn = sqlite3.connect(db_path())
    dump = "\n".join(conn.iterdump())
    conn.close()
    assert token not in dump


def test_two_logins_make_two_independent_sessions(registered):
    _login(registered)
    first = registered.cookies.get(COOKIE_NAME)
    _login(registered)
    assert len(_sessions()) == 2
    registered.post("/auth/logout")
    registered.cookies.set(COOKIE_NAME, first)
    assert registered.get("/auth/me").status_code == 200


def test_app_refuses_to_start_without_session_secret(client, monkeypatch):
    monkeypatch.delenv("SESSION_SECRET")
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        with TestClient(app):
            pass


def test_cors_allows_credentials_for_frontend_origin(client):
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert r.headers["access-control-allow-credentials"] == "true"
