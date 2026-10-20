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
