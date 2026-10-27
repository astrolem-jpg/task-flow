import sqlite3

import pytest

from app.db import db_path


def _make(c, **extra):
    r = c.post("/tasks", json={"title": "t", "description": "d", **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _edit(c, task_id, **extra):
    return c.patch(f"/tasks/{task_id}", json={"title": "t", "description": "d", **extra})


def _code(r):
    return r.json()["detail"]["code"]


def test_create_defaults_to_normal_and_no_due_date(client):
    t = _make(client)
    assert t["priority"] == "NORMAL"
    assert t["due_date"] is None


def test_create_with_priority_and_due_date_persists(client):
    t = _make(client, priority="HIGH", due_date="2026-12-31")
    assert (t["priority"], t["due_date"]) == ("HIGH", "2026-12-31")
    listed = client.get("/tasks").json()[0]
    assert (listed["priority"], listed["due_date"]) == ("HIGH", "2026-12-31")


def test_past_due_date_is_allowed(client):
    assert _make(client, due_date="2000-01-01")["due_date"] == "2000-01-01"


@pytest.mark.parametrize("value", ["urgent", "high", "HIGH ", "", None, 1, ["HIGH"]])
def test_create_rejects_invalid_priority_with_422(client, value):
    r = client.post("/tasks", json={"title": "t", "priority": value})
    assert r.status_code == 422
    assert _code(r) == "INVALID_PRIORITY"
    assert client.get("/tasks").json() == []


@pytest.mark.parametrize(
    "value",
    ["2026-02-30", "2026-13-01", "2026-1-1", "20261031", "2026/10/31", "2026-10-31T10:00",
     "2026-10-31 10:00", "내일", "", 20261031, ["2026-10-31"], "２０２６-１０-３１"],
)
def test_create_rejects_invalid_due_date_with_422(client, value):
    r = client.post("/tasks", json={"title": "t", "due_date": value})
    assert r.status_code == 422
    assert _code(r) == "INVALID_DUE_DATE"
    assert client.get("/tasks").json() == []


def test_edit_changes_priority_and_due_date(client):
    t = _make(client)
    r = _edit(client, t["id"], priority="LOW", due_date="2026-11-01")
    assert r.status_code == 200
    assert (r.json()["priority"], r.json()["due_date"]) == ("LOW", "2026-11-01")


def test_edit_without_new_fields_keeps_them(client):
    t = _make(client, priority="HIGH", due_date="2026-11-01")
    r = _edit(client, t["id"])
    assert r.status_code == 200
    assert (r.json()["priority"], r.json()["due_date"]) == ("HIGH", "2026-11-01")


def test_edit_due_date_null_clears_it(client):
    t = _make(client, due_date="2026-11-01")
    r = _edit(client, t["id"], due_date=None)
    assert r.status_code == 200
    assert r.json()["due_date"] is None


def test_edit_priority_null_is_422_and_card_unchanged(client):
    t = _make(client, priority="HIGH", due_date="2026-11-01")
    r = _edit(client, t["id"], priority=None)
    assert r.status_code == 422
    assert _code(r) == "INVALID_PRIORITY"
    assert client.get("/tasks").json()[0]["priority"] == "HIGH"


def test_edit_invalid_values_422_and_card_unchanged(client):
    t = _make(client, priority="HIGH", due_date="2026-11-01")
    bad = [
        ({"priority": "MAX"}, "INVALID_PRIORITY"),
        ({"due_date": "2026-02-30"}, "INVALID_DUE_DATE"),
        ({"due_date": "11/01"}, "INVALID_DUE_DATE"),
    ]
    for extra, code in bad:
        r = _edit(client, t["id"], title="바뀌면 안 됨", **extra)
        assert r.status_code == 422 and _code(r) == code
    card = client.get("/tasks").json()[0]
    assert card["title"] == "t"
    assert (card["priority"], card["due_date"]) == ("HIGH", "2026-11-01")


def test_status_change_keeps_priority_and_due_date(client):
    t = _make(client, priority="HIGH", due_date="2026-11-01")
    r = client.patch(f"/tasks/{t['id']}/status", json={"status": "DONE"})
    assert r.status_code == 200
    body = r.json()
    assert (body["status"], body["priority"], body["due_date"]) == ("DONE", "HIGH", "2026-11-01")


def test_old_style_requests_still_work(client):
    t = client.post("/tasks", json={"title": "옛 방식"}).json()
    r = client.patch(f"/tasks/{t['id']}", json={"title": "고침", "description": "x"})
    assert r.status_code == 200
    assert (r.json()["priority"], r.json()["due_date"]) == ("NORMAL", None)


def test_title_rule_still_checked_first(client):
    r = client.post("/tasks", json={"title": " ", "priority": "bad", "due_date": "bad"})
    assert r.status_code == 400
    assert _code(r) == "TITLE_REQUIRED"


def test_other_users_card_with_new_fields_is_404_and_unchanged(client):
    from fastapi.testclient import TestClient

    from app.main import app
    from tests.helpers import signup_and_login

    a = _make(client, priority="HIGH", due_date="2026-11-01")
    with TestClient(app) as other:
        signup_and_login(other, email="b@example.com", password="password-for-b")
        r = _edit(other, a["id"], priority="LOW", due_date=None)
        assert r.status_code == 404 and _code(r) == "NOT_FOUND"
        assert other.get("/tasks").json() == []
    card = client.get("/tasks").json()[0]
    assert (card["priority"], card["due_date"]) == ("HIGH", "2026-11-01")


def test_new_fields_require_login(anon_client):
    assert anon_client.post("/tasks", json={"title": "t", "priority": "HIGH"}).status_code == 401
    assert anon_client.patch("/tasks/1", json={"title": "t", "due_date": None}).status_code == 401


def test_response_hides_owner_and_hashes_but_db_stores_values(client):
    t = _make(client, priority="LOW", due_date="2026-11-01")
    assert set(t) == {"id", "title", "description", "status", "priority", "due_date"}
    conn = sqlite3.connect(db_path())
    row = conn.execute("SELECT priority, due_date FROM tasks WHERE id = ?", (t["id"],)).fetchone()
    conn.close()
    assert row == ("LOW", "2026-11-01")
