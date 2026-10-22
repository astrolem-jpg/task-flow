import sqlite3

import pytest

from app.db import db_path


@pytest.fixture
def client(anon_client):
    """가입 테스트는 로그인하지 않은 상태에서 시작한다."""
    return anon_client


def _signup(client, email="a@x.com", password="password1"):
    return client.post("/auth/signup", json={"email": email, "password": password})


def _users():
    conn = sqlite3.connect(db_path())
    try:
        return conn.execute("SELECT email, password_hash FROM users ORDER BY id").fetchall()
    finally:
        conn.close()


def test_signup_success_returns_id_and_email_only(client):
    r = _signup(client)
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"id", "email"}
    assert body["email"] == "a@x.com"
    assert isinstance(body["id"], int)
    assert "password" not in r.text and "scrypt" not in r.text


def test_signup_stores_hash_not_plain_password(client):
    _signup(client, password="password1")
    [(email, stored)] = _users()
    assert email == "a@x.com"
    assert stored.startswith("scrypt$")
    assert "password1" not in stored


def test_signup_normalizes_email(client):
    r = _signup(client, email="  Mixed.Case@X.com ")
    assert r.status_code == 201
    assert r.json()["email"] == "mixed.case@x.com"


def test_signup_duplicate_email_is_409_case_insensitive(client):
    assert _signup(client, email="a@x.com").status_code == 201
    for email in ["a@x.com", "A@X.COM", " a@x.com "]:
        r = _signup(client, email=email)
        assert r.status_code == 409
        assert r.json()["detail"]["code"] == "EMAIL_TAKEN"
    assert len(_users()) == 1


def test_signup_rejects_invalid_email(client):
    for email in ["", "   ", "plain", "a@", "@x.com", "a@x", "a b@x.com", "a@@x.com", "a@x." ]:
        r = _signup(client, email=email)
        assert r.status_code == 400, email
        assert r.json()["detail"]["code"] == "INVALID_EMAIL"
    assert _users() == []


def test_signup_rejects_too_long_email(client):
    r = _signup(client, email="a" * 250 + "@x.com")
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_EMAIL"


def test_signup_password_length_boundaries(client):
    r = _signup(client, email="short@x.com", password="1234567")
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_PASSWORD"
    assert _signup(client, email="min@x.com", password="12345678").status_code == 201
    assert _signup(client, email="max@x.com", password="p" * 128).status_code == 201
    r = _signup(client, email="long@x.com", password="p" * 129)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_PASSWORD"


def test_signup_missing_fields_are_rule_errors(client):
    r = client.post("/auth/signup", json={})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_EMAIL"
    r = client.post("/auth/signup", json={"email": "a@x.com"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_PASSWORD"


def test_signup_does_not_log_in(client):
    _signup(client)
    assert "set-cookie" not in _signup(client, email="b@x.com").headers
