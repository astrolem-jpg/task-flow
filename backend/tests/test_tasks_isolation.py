import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.db import db_path
from app.main import app
from tests.helpers import signup_and_login


@pytest.fixture
def client_b(client):
    """같은 DB를 쓰는 두 번째 사용자. client는 첫 번째 사용자(A)다."""
    with TestClient(app) as c:
        signup_and_login(c, email="b@example.com", password="password-for-b")
        yield c


def _make(c, title="t", description="d"):
    r = c.post("/tasks", json={"title": title, "description": description})
    assert r.status_code == 201
    return r.json()


def test_each_user_sees_only_own_cards(client, client_b):
    a = _make(client, "A의 카드")
    b = _make(client_b, "B의 카드")
    assert [t["id"] for t in client.get("/tasks").json()] == [a["id"]]
    assert [t["id"] for t in client_b.get("/tasks").json()] == [b["id"]]


def test_new_user_starts_with_empty_list(client, client_b):
    _make(client)
    assert client_b.get("/tasks").json() == []


def test_other_users_card_cannot_be_changed_or_deleted(client, client_b):
    a = _make(client, "원본", "설명")
    calls = [
        ("PATCH", f"/tasks/{a['id']}", {"title": "침입", "description": "x"}),
        ("PATCH", f"/tasks/{a['id']}/status", {"status": "DONE"}),
        ("DELETE", f"/tasks/{a['id']}", None),
    ]
    for method, path, body in calls:
        r = client_b.request(method, path, json=body)
        assert r.status_code == 404, (method, path)
        assert r.json()["detail"]["code"] == "NOT_FOUND"
    assert client.get("/tasks").json() == [
        {
            "id": a["id"], "title": "원본", "description": "설명", "status": "TODO",
            "priority": "NORMAL", "due_date": None, "subtasks": [],
        }
    ]


def test_other_users_card_looks_the_same_as_missing_card(client, client_b):
    a = _make(client)
    for method, suffix, body in [
        ("PATCH", "", {"title": "x", "description": ""}),
        ("PATCH", "/status", {"status": "DONE"}),
        ("DELETE", "", None),
    ]:
        theirs = client_b.request(method, f"/tasks/{a['id']}{suffix}", json=body)
        missing = client_b.request(method, f"/tasks/9999{suffix}", json=body)
        assert theirs.status_code == missing.status_code == 404
        assert theirs.json() == missing.json()


def test_title_rule_still_checked_before_lookup(client, client_b):
    a = _make(client)
    r = client_b.patch(f"/tasks/{a['id']}", json={"title": " ", "description": ""})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "TITLE_REQUIRED"


def test_create_stores_owner_but_does_not_expose_it(client, client_b):
    a = _make(client)
    b = _make(client_b)
    assert set(a) == {"id", "title", "description", "status", "priority", "due_date", "subtasks"}
    conn = sqlite3.connect(db_path())
    owners = dict(conn.execute("SELECT id, owner_id FROM tasks"))
    emails = dict(conn.execute("SELECT id, email FROM users"))
    conn.close()
    assert emails[owners[a["id"]]] == "user@example.com"
    assert emails[owners[b["id"]]] == "b@example.com"


def test_users_can_own_cards_with_same_title(client, client_b):
    _make(client, "같은 제목")
    _make(client_b, "같은 제목")
    assert len(client.get("/tasks").json()) == 1
    assert len(client_b.get("/tasks").json()) == 1


def test_own_card_still_fully_usable(client, client_b):
    a = _make(client, "t")
    assert client.patch(f"/tasks/{a['id']}/status", json={"status": "DONE"}).status_code == 200
    r = client.patch(f"/tasks/{a['id']}", json={"title": "새", "description": ""})
    assert r.status_code == 200 and r.json()["status"] == "DONE"
    assert client.delete(f"/tasks/{a['id']}").status_code == 204
    assert client.get("/tasks").json() == []
