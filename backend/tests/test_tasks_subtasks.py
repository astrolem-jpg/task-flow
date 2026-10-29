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


def _subs(*titles, description=""):
    return [{"title": t, "description": description} for t in titles]


def _make(c, subtasks=None, **extra):
    body = {"title": "이사 준비", "description": "d", **extra}
    if subtasks is not None:
        body["subtasks"] = subtasks
    r = c.post("/tasks", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _add(c, task_id, items):
    return c.post(f"/tasks/{task_id}/subtasks", json={"items": items})


def _code(r):
    return r.json()["detail"]["code"]


def _db(sql, params=()):
    conn = sqlite3.connect(db_path())
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _titles(task):
    return [s["title"] for s in task["subtasks"]]


# --- 응답 모양 -----------------------------------------------------------------


def test_cards_without_subtasks_show_an_empty_list(client):
    t = _make(client)
    assert t["subtasks"] == []
    assert client.get("/tasks").json()[0]["subtasks"] == []


def test_subtask_has_only_id_title_and_description(client):
    t = _make(client, _subs("업체 견적 받기", description="3곳"))
    (s,) = t["subtasks"]
    assert set(s) == {"id", "title", "description"}
    assert (s["title"], s["description"]) == ("업체 견적 받기", "3곳")


def test_create_with_subtasks_saves_card_and_items_together_in_id_order(client):
    t = _make(client, _subs("a", "b", "c"), priority="HIGH", due_date="2026-11-01")
    assert _titles(t) == ["a", "b", "c"]
    assert [s["id"] for s in t["subtasks"]] == sorted(s["id"] for s in t["subtasks"])
    listed = client.get("/tasks").json()
    assert len(listed) == 1
    assert listed[0] == t
    assert (listed[0]["priority"], listed[0]["due_date"]) == ("HIGH", "2026-11-01")


def test_create_without_subtasks_or_with_null_or_empty_works_as_before(client):
    assert _make(client)["subtasks"] == []
    explicit_null = client.post("/tasks", json={"title": "t", "subtasks": None})
    assert explicit_null.status_code == 201
    assert explicit_null.json()["subtasks"] == []
    assert _make(client, [])["subtasks"] == []


def test_subtask_title_is_trimmed_and_description_may_be_omitted(client):
    t = _make(client, [{"title": "  제목  "}])
    assert t["subtasks"][0]["title"] == "제목"
    assert t["subtasks"][0]["description"] == ""


# --- 생성 거절: 카드도 만들지 않는다 --------------------------------------------

BAD_CREATE = [
    ("not-list", "x", 422, "INVALID_SUBTASKS"),
    ("item-not-object", ["x"], 422, "INVALID_SUBTASKS"),
    ("title-not-string", [{"title": 5}], 422, "INVALID_SUBTASKS"),
    ("description-not-string", [{"title": "a", "description": None}], 422, "INVALID_SUBTASKS"),
    ("blank-title", [{"title": "   "}], 400, "TITLE_REQUIRED"),
    ("missing-title", [{"description": "d"}], 400, "TITLE_REQUIRED"),
    ("too-many", _subs(*[f"s{i}" for i in range(21)]), 422, "TOO_MANY_SUBTASKS"),
]


@pytest.mark.parametrize(
    "value,status,code",
    [b[1:] for b in BAD_CREATE],
    ids=[b[0] for b in BAD_CREATE],
)
def test_rejected_create_creates_no_card_and_no_subtasks(client, value, status, code):
    r = client.post("/tasks", json={"title": "카드", "subtasks": value})
    assert (r.status_code, _code(r)) == (status, code)
    assert client.get("/tasks").json() == []
    assert _db("SELECT COUNT(*) FROM tasks") == [(0,)]
    assert _db("SELECT COUNT(*) FROM subtasks") == [(0,)]


def test_create_accepts_exactly_twenty_subtasks(client):
    t = _make(client, _subs(*[f"s{i}" for i in range(20)]))
    assert len(t["subtasks"]) == 20


def test_bad_subtask_does_not_hide_card_title_rule(client):
    r = client.post("/tasks", json={"title": "  ", "subtasks": _subs("a")})
    assert (r.status_code, _code(r)) == (400, "TITLE_REQUIRED")
    assert _db("SELECT COUNT(*) FROM tasks") == [(0,)]


# --- 추가: POST /tasks/{id}/subtasks -------------------------------------------


def test_add_attaches_to_the_card_and_returns_whole_card(client):
    t = _make(client, _subs("먼저"), priority="LOW", due_date="2026-12-01")
    r = _add(client, t["id"], _subs("a", "b", "c"))
    assert r.status_code == 201
    body = r.json()
    assert _titles(body) == ["먼저", "a", "b", "c"]
    # 카드의 다른 값은 바뀌지 않는다.
    assert {k: body[k] for k in ("id", "title", "description", "status", "priority", "due_date")} == {
        "id": t["id"], "title": "이사 준비", "description": "d", "status": "TODO",
        "priority": "LOW", "due_date": "2026-12-01",
    }
    assert client.get("/tasks").json() == [body]


def test_add_does_not_create_other_cards(client):
    t = _make(client)
    _add(client, t["id"], _subs("a", "b", "c", "d"))
    assert len(client.get("/tasks").json()) == 1
    assert _db("SELECT COUNT(*) FROM tasks") == [(1,)]


def test_add_can_be_repeated_up_to_twenty(client):
    t = _make(client)
    for start in (0, 5, 10, 15):
        r = _add(client, t["id"], _subs(*[f"s{start + i}" for i in range(5)]))
        assert r.status_code == 201
    assert len(r.json()["subtasks"]) == 20


def test_add_over_twenty_in_total_is_422_and_attaches_none(client):
    t = _make(client, _subs(*[f"s{i}" for i in range(18)]))
    r = _add(client, t["id"], _subs("x", "y", "z"))
    assert (r.status_code, _code(r)) == (422, "TOO_MANY_SUBTASKS")
    assert _db("SELECT COUNT(*) FROM subtasks WHERE task_id = ?", (t["id"],)) == [(18,)]


@pytest.mark.parametrize(
    "items,status,code",
    [
        (None, 422, "INVALID_SUBTASKS"),
        ([], 422, "INVALID_SUBTASKS"),
        ("x", 422, "INVALID_SUBTASKS"),
        (["x"], 422, "INVALID_SUBTASKS"),
        ([{"title": 1}], 422, "INVALID_SUBTASKS"),
        ([{"title": "   "}], 400, "TITLE_REQUIRED"),
    ],
    ids=["missing", "empty", "not-list", "not-object", "title-not-string", "blank-title"],
)
def test_add_rejects_bad_items_and_changes_nothing(client, items, status, code):
    t = _make(client, _subs("기존"))
    r = client.post(f"/tasks/{t['id']}/subtasks", json={} if items is None else {"items": items})
    assert (r.status_code, _code(r)) == (status, code)
    assert _db("SELECT title FROM subtasks") == [("기존",)]


def test_add_is_all_or_nothing_when_one_item_is_bad(client):
    t = _make(client)
    r = _add(client, t["id"], [{"title": "좋음"}, {"title": "  "}, {"title": "좋음2"}])
    assert (r.status_code, _code(r)) == (400, "TITLE_REQUIRED")
    assert _db("SELECT COUNT(*) FROM subtasks") == [(0,)]


def test_add_to_missing_card_is_404(client):
    r = _add(client, 9999, _subs("a"))
    assert (r.status_code, _code(r)) == (404, "NOT_FOUND")
    assert _db("SELECT COUNT(*) FROM subtasks") == [(0,)]


# --- 수정, 상태 변경, 삭제 -----------------------------------------------------


def test_update_and_status_change_keep_subtasks_and_return_them(client):
    t = _make(client, _subs("a", "b"))
    updated = client.patch(f"/tasks/{t['id']}", json={"title": "새 제목", "description": "x"})
    assert updated.status_code == 200
    assert _titles(updated.json()) == ["a", "b"]
    moved = client.patch(f"/tasks/{t['id']}/status", json={"status": "DONE"})
    assert moved.status_code == 200
    assert _titles(moved.json()) == ["a", "b"]
    assert _db("SELECT COUNT(*) FROM subtasks") == [(2,)]


def test_update_ignores_subtasks_in_the_request(client):
    t = _make(client, _subs("a"))
    r = client.patch(
        f"/tasks/{t['id']}", json={"title": "t", "description": "", "subtasks": _subs("무시")}
    )
    assert r.status_code == 200
    assert _titles(r.json()) == ["a"]


def test_delete_removes_the_card_and_its_subtasks_only(client):
    keep = _make(client, _subs("남는 항목"))
    gone = _make(client, _subs("a", "b"))
    assert client.delete(f"/tasks/{gone['id']}").status_code == 204
    assert [t["id"] for t in client.get("/tasks").json()] == [keep["id"]]
    assert _db("SELECT task_id, title FROM subtasks") == [(keep["id"], "남는 항목")]


# --- 로그인과 소유자 격리 ------------------------------------------------------


def test_new_endpoint_requires_login(anon_client):
    r = anon_client.post("/tasks/1/subtasks", json={"items": _subs("a")})
    assert (r.status_code, _code(r)) == (401, "UNAUTHORIZED")


def test_create_with_subtasks_requires_login(anon_client):
    r = anon_client.post("/tasks", json={"title": "t", "subtasks": _subs("a")})
    assert r.status_code == 401
    assert _db("SELECT COUNT(*) FROM subtasks") == [(0,)]


def test_other_users_card_cannot_get_subtasks_and_stays_unchanged(client, client_b):
    a = _make(client, _subs("A의 항목"))
    r = _add(client_b, a["id"], _subs("침입"))
    assert (r.status_code, _code(r)) == (404, "NOT_FOUND")
    assert _titles(client.get("/tasks").json()[0]) == ["A의 항목"]
    assert _db("SELECT title FROM subtasks") == [("A의 항목",)]


def test_other_users_cannot_delete_subtasks_through_card_delete(client, client_b):
    a = _make(client, _subs("A의 항목"))
    assert client_b.delete(f"/tasks/{a['id']}").status_code == 404
    assert _db("SELECT title FROM subtasks") == [("A의 항목",)]
    assert len(client.get("/tasks").json()) == 1


def test_each_user_sees_only_own_subtasks(client, client_b):
    a = _make(client, _subs("A1", "A2"))
    b = _make(client_b, _subs("B1"))
    assert _titles(client.get("/tasks").json()[0]) == ["A1", "A2"]
    assert _titles(client_b.get("/tasks").json()[0]) == ["B1"]
    assert [t["id"] for t in client.get("/tasks").json()] == [a["id"]]
    assert [t["id"] for t in client_b.get("/tasks").json()] == [b["id"]]


def test_response_never_exposes_owner_id_or_hashes(client):
    t = _make(client, _subs("a"))
    assert "owner_id" not in t and "password_hash" not in t
    assert "task_id" not in t["subtasks"][0]
    assert "owner_id" not in client.get("/tasks").json()[0]


# --- 후보와의 관계 -------------------------------------------------------------


def test_suggest_tasks_never_creates_subtasks(client, monkeypatch):
    from app import ai_suggest

    items = [
        {"title": f"할 일 {n}", "description": "", "priority": "NORMAL", "due_date": None}
        for n in range(4)
    ]
    monkeypatch.setattr(ai_suggest, "suggest_tasks", lambda title, description: items)
    t = _make(client)
    r = client.post("/tasks/suggest-tasks", json={"title": "이사"})
    assert r.status_code == 200
    assert _db("SELECT COUNT(*) FROM subtasks") == [(0,)]
    assert client.get("/tasks").json() == [t]


def test_candidates_can_be_attached_as_subtasks_with_card_values_unchanged(client, monkeypatch):
    from app import ai_suggest

    items = [
        {"title": f"할 일 {n}", "description": "d", "priority": "HIGH", "due_date": "2026-11-01"}
        for n in range(3)
    ]
    monkeypatch.setattr(ai_suggest, "suggest_tasks", lambda title, description: items)
    t = _make(client, priority="LOW")
    candidates = client.post("/tasks/suggest-tasks", json={"title": "이사"}).json()["items"]
    r = _add(client, t["id"], [{"title": c["title"], "description": c["description"]} for c in candidates])
    assert r.status_code == 201
    body = r.json()
    assert _titles(body) == ["할 일 0", "할 일 1", "할 일 2"]
    # 후보의 우선순위와 마감일은 카드에 옮겨지지 않는다.
    assert (body["priority"], body["due_date"]) == ("LOW", None)
    assert len(client.get("/tasks").json()) == 1
