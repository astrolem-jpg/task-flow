from fastapi.testclient import TestClient

from app.main import app


def test_create_without_description_defaults_todo(client):
    r = client.post("/tasks", json={"title": "첫 카드"})
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "첫 카드"
    assert body["description"] == ""
    assert body["status"] == "TODO"
    assert isinstance(body["id"], int)


def test_create_rejects_empty_and_blank_title(client):
    for title in ["", "   ", "\t\n"]:
        r = client.post("/tasks", json={"title": title})
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "TITLE_REQUIRED"
    assert client.get("/tasks").json() == []


def test_list_empty_is_success(client):
    r = client.get("/tasks")
    assert r.status_code == 200
    assert r.json() == []


def test_list_in_id_order(client):
    client.post("/tasks", json={"title": "a"})
    client.post("/tasks", json={"title": "b", "description": "d"})
    titles = [t["title"] for t in client.get("/tasks").json()]
    assert titles == ["a", "b"]


def test_data_persists_across_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKFLOW_DB", str(tmp_path / "keep.db"))
    with TestClient(app) as c:
        c.post("/tasks", json={"title": "남아야 함"})
    with TestClient(app) as c:
        assert [t["title"] for t in c.get("/tasks").json()] == ["남아야 함"]


def _make(client, title="t", description="d"):
    return client.post("/tasks", json={"title": title, "description": description}).json()


def test_status_change_any_to_any_keeps_title_and_description(client):
    t = _make(client)
    for s in ["DONE", "TODO", "IN_PROGRESS", "DONE", "IN_PROGRESS"]:
        r = client.patch(f"/tasks/{t['id']}/status", json={"status": s})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == s
        assert body["title"] == "t" and body["description"] == "d"
    assert client.get("/tasks").json()[0]["status"] == "IN_PROGRESS"


def test_status_change_same_status_is_success(client):
    t = _make(client)
    r = client.patch(f"/tasks/{t['id']}/status", json={"status": "TODO"})
    assert r.status_code == 200


def test_status_change_invalid_value_rejected_and_unchanged(client):
    t = _make(client)
    for bad in ["", "done", "할 일", "WHATEVER"]:
        r = client.patch(f"/tasks/{t['id']}/status", json={"status": bad})
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "INVALID_STATUS"
    assert client.get("/tasks").json()[0]["status"] == "TODO"


def test_status_change_missing_task_404(client):
    r = client.patch("/tasks/999/status", json={"status": "DONE"})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOT_FOUND"


def test_update_changes_title_description_keeps_status(client):
    t = _make(client)
    client.patch(f"/tasks/{t['id']}/status", json={"status": "DONE"})
    r = client.patch(f"/tasks/{t['id']}", json={"title": "  새 제목 ", "description": "새 설명"})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "새 제목"
    assert body["description"] == "새 설명"
    assert body["status"] == "DONE"
    assert client.get("/tasks").json()[0]["title"] == "새 제목"


def test_update_can_clear_description(client):
    t = _make(client)
    r = client.patch(f"/tasks/{t['id']}", json={"title": "t", "description": ""})
    assert r.status_code == 200
    assert r.json()["description"] == ""


def test_update_rejects_empty_and_blank_title_unchanged(client):
    t = _make(client)
    for title in ["", "   "]:
        r = client.patch(f"/tasks/{t['id']}", json={"title": title, "description": "x"})
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "TITLE_REQUIRED"
    saved = client.get("/tasks").json()[0]
    assert saved["title"] == "t" and saved["description"] == "d"


def test_update_missing_task_404(client):
    r = client.patch("/tasks/999", json={"title": "a", "description": ""})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOT_FOUND"


def test_delete_removes_task_and_stays_removed(client):
    a = _make(client, "a")
    b = _make(client, "b")
    r = client.delete(f"/tasks/{a['id']}")
    assert r.status_code == 204
    assert [t["id"] for t in client.get("/tasks").json()] == [b["id"]]


def test_delete_missing_task_404(client):
    r = client.delete("/tasks/999")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOT_FOUND"


def test_delete_twice_second_is_404(client):
    t = _make(client)
    assert client.delete(f"/tasks/{t['id']}").status_code == 204
    assert client.delete(f"/tasks/{t['id']}").status_code == 404


def test_delete_persists_across_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKFLOW_DB", str(tmp_path / "del.db"))
    with TestClient(app) as c:
        t = c.post("/tasks", json={"title": "x"}).json()
        c.delete(f"/tasks/{t['id']}")
    with TestClient(app) as c:
        assert c.get("/tasks").json() == []
