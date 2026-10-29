import pytest

from app.auth import COOKIE_NAME

# (메서드, 경로, 본문): 보호 대상 5개 동작. 999는 없는 카드 id다.
TASK_CALLS = [
    ("GET", "/tasks", None),
    ("POST", "/tasks", {"title": "x", "description": "d"}),
    ("PATCH", "/tasks/1", {"title": "x", "description": "d"}),
    ("DELETE", "/tasks/1", None),
    ("PATCH", "/tasks/1/status", {"status": "DONE"}),
    ("PATCH", "/tasks/999", {"title": "x", "description": "d"}),
    ("DELETE", "/tasks/999", None),
    ("PATCH", "/tasks/999/status", {"status": "DONE"}),
]


@pytest.mark.parametrize("method,path,body", TASK_CALLS)
def test_task_api_requires_login(anon_client, method, path, body):
    r = anon_client.request(method, path, json=body)
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize("method,path,body", TASK_CALLS)
def test_tampered_cookie_is_rejected(anon_client, method, path, body):
    anon_client.cookies.set(COOKIE_NAME, "tampered-token")
    assert anon_client.request(method, path, json=body).status_code == 401


def test_rejected_requests_change_nothing(client, anon_client):
    t = client.post("/tasks", json={"title": "원본", "description": "d"}).json()
    for method, path, body in [
        ("POST", "/tasks", {"title": "침입"}),
        ("PATCH", f"/tasks/{t['id']}", {"title": "바뀜", "description": "x"}),
        ("PATCH", f"/tasks/{t['id']}/status", {"status": "DONE"}),
        ("DELETE", f"/tasks/{t['id']}", None),
    ]:
        assert anon_client.request(method, path, json=body).status_code == 401
    assert client.get("/tasks").json() == [
        {
            "id": t["id"], "title": "원본", "description": "d", "status": "TODO",
            "priority": "NORMAL", "due_date": None, "subtasks": [],
        }
    ]


def test_logged_out_session_loses_access(client):
    assert client.get("/tasks").status_code == 200
    client.post("/auth/logout")
    assert client.get("/tasks").status_code == 401


def test_public_endpoints_need_no_login(anon_client):
    assert anon_client.get("/health").status_code == 200
    r = anon_client.post(
        "/auth/signup", json={"email": "p@x.com", "password": "password1"}
    )
    assert r.status_code == 201
    r = anon_client.post(
        "/auth/login", json={"email": "p@x.com", "password": "password1"}
    )
    assert r.status_code == 200
