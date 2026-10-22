"""M1에서 만든 DB(owner_id 없음)를 가진 상태에서 첫 가입이 일어나는 경우. (D-021)"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import login, migrate, signup, signup_and_login

LEGACY_SCHEMA = """
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'TODO'
)
"""


@pytest.fixture
def legacy_db(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    monkeypatch.setenv("TASKFLOW_DB", str(path))
    conn = sqlite3.connect(path)
    conn.execute(LEGACY_SCHEMA)
    conn.executemany(
        "INSERT INTO tasks (title, description, status) VALUES (?, ?, ?)",
        [("옛 카드 1", "d1", "TODO"), ("옛 카드 2", "d2", "DONE")],
    )
    conn.commit()
    conn.close()
    migrate()
    return path


def _owners(path):
    conn = sqlite3.connect(path)
    try:
        return [r[0] for r in conn.execute("SELECT owner_id FROM tasks ORDER BY id")]
    finally:
        conn.close()


def test_cards_have_no_owner_until_first_signup(legacy_db):
    assert _owners(legacy_db) == [None, None]


def test_first_signup_takes_over_legacy_cards(legacy_db):
    with TestClient(app) as c:
        user = c.post(
            "/auth/signup", json={"email": "first@x.com", "password": "password1"}
        ).json()
        assert _owners(legacy_db) == [user["id"], user["id"]]
        login(c, "first@x.com", "password1")
        cards = c.get("/tasks").json()
    assert [(t["title"], t["description"], t["status"]) for t in cards] == [
        ("옛 카드 1", "d1", "TODO"),
        ("옛 카드 2", "d2", "DONE"),
    ]


def test_second_user_does_not_see_or_touch_legacy_cards(legacy_db):
    with TestClient(app) as first, TestClient(app) as second:
        signup_and_login(first, "first@x.com", "password1")
        signup_and_login(second, "second@x.com", "password2")
        assert second.get("/tasks").json() == []
        card_id = first.get("/tasks").json()[0]["id"]
        assert second.delete(f"/tasks/{card_id}").status_code == 404
        assert len(first.get("/tasks").json()) == 2


def test_only_the_first_signup_claims_cards(legacy_db):
    with TestClient(app) as c:
        signup(c, "first@x.com", "password1")
        # 첫 가입 뒤에 소유자 없는 카드가 생긴 상황. 두 번째 가입자가 가져가면 안 된다.
        conn = sqlite3.connect(legacy_db)
        conn.execute("INSERT INTO tasks (title) VALUES ('주인 없는 카드')")
        conn.commit()
        conn.close()
        signup(c, "second@x.com", "password2")
    assert _owners(legacy_db)[-1] is None


def test_failed_signup_does_not_claim_cards(legacy_db):
    with TestClient(app) as c:
        r = c.post("/auth/signup", json={"email": "bad", "password": "password1"})
        assert r.status_code == 400
        r = c.post("/auth/signup", json={"email": "ok@x.com", "password": "short"})
        assert r.status_code == 400
    assert _owners(legacy_db) == [None, None]
