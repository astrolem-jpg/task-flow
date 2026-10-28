import json
import sqlite3

import anthropic
import httpx
import pytest

from app import ai_suggest
from app.ai_suggest import API_KEY_ENV
from app.db import db_path

GOOD = {"priority": "HIGH", "due_date": "2026-10-28", "reason": "내일까지라 급합니다."}


class FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text, stop_reason="end_turn"):
        self.stop_reason = stop_reason
        self.content = [FakeBlock(text)]


class FakeClient:
    """실제 API를 부르지 않는다."""

    def __init__(self, response=None, error=None):
        self.calls = []
        self._response = response
        self._error = error
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._response


@pytest.fixture
def install(monkeypatch):
    def _install(response=None, error=None):
        client = FakeClient(response, error)
        monkeypatch.setattr(ai_suggest, "_make_client", lambda: client)
        return client

    monkeypatch.setattr(ai_suggest, "_today", lambda: "2026-10-27")
    return _install


def _error(cls, status):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("x", response=httpx.Response(status, request=request), body=None)


def _tasks_snapshot():
    conn = sqlite3.connect(db_path())
    try:
        return conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    finally:
        conn.close()


def _suggest(c, **body):
    return c.post("/tasks/suggest", json=body)


def _code(r):
    return r.json()["detail"]["code"]


def test_returns_only_priority_due_date_and_reason(client, install):
    install(FakeResponse(json.dumps(GOOD)))
    r = _suggest(client, title="내일까지 보고서 마무리, 급함", description="")
    assert r.status_code == 200
    assert r.json() == GOOD


def test_works_without_description_and_without_any_card(client, install):
    install(FakeResponse(json.dumps(GOOD)))
    assert client.get("/tasks").json() == []
    assert _suggest(client, title="제목만").status_code == 200


def test_title_is_trimmed_and_passed_with_description_and_server_date(client, install):
    fake = install(FakeResponse(json.dumps(GOOD)))
    _suggest(client, title="  보고서  ", description="내일까지")
    (call,) = fake.calls
    assert call["messages"][0]["content"] == (
        "<today>2026-10-27</today>\n<title>보고서</title>\n<description>내일까지</description>"
    )
    assert call["thinking"] == {"type": "disabled"}
    assert call["model"] == "claude-haiku-5-5"


def test_success_does_not_touch_cards(client, install):
    client.post("/tasks", json={"title": "기존", "description": "d", "priority": "LOW"})
    before = _tasks_snapshot()
    install(FakeResponse(json.dumps(GOOD)))
    assert _suggest(client, title="보고서").status_code == 200
    assert _tasks_snapshot() == before
    assert client.get("/tasks").json()[0]["priority"] == "LOW"


# --- 로그인, 입력 --------------------------------------------------------------


def test_requires_login(anon_client, install):
    fake = install(FakeResponse(json.dumps(GOOD)))
    r = _suggest(anon_client, title="t")
    assert r.status_code == 401
    assert _code(r) == "UNAUTHORIZED"
    assert fake.calls == []


@pytest.mark.parametrize("title", ["", "   ", "\n\t"])
def test_blank_title_is_400_and_model_not_called(client, install, title):
    fake = install(FakeResponse(json.dumps(GOOD)))
    r = _suggest(client, title=title)
    assert r.status_code == 400
    assert _code(r) == "TITLE_REQUIRED"
    assert fake.calls == []


# --- 실패: 어느 경우에도 DB는 그대로 ---------------------------------------------

FAILURES = [
    (FakeResponse("제안: HIGH"), 502, "SUGGEST_FAILED", "제안 실패"),
    (FakeResponse('{"priority": "URGENT", "due_date": null, "reason": "x"}'), 502, "SUGGEST_FAILED", "제안 실패"),
    (FakeResponse('{"priority": "HIGH", "due_date": "2026-02-30", "reason": "x"}'), 502, "SUGGEST_FAILED", "제안 실패"),
    (FakeResponse(json.dumps(GOOD), stop_reason="max_tokens"), 502, "SUGGEST_FAILED", "제안 실패"),
    (_error(anthropic.RateLimitError, 429), 503, "AI_BUSY", None),
    (_error(anthropic.OverloadedError, 529), 503, "AI_BUSY", None),
    (_error(anthropic.AuthenticationError, 401), 503, "AI_DISABLED", "AI 기능 꺼짐"),
]


@pytest.mark.parametrize(
    "outcome,status,code,message",
    FAILURES,
    ids=["not-json", "bad-priority", "bad-date", "truncated", "rate-limit", "overloaded", "bad-key"],
)
def test_failures_use_the_agreed_status_and_leave_cards_unchanged(
    client, install, outcome, status, code, message
):
    client.post("/tasks", json={"title": "기존", "priority": "HIGH", "due_date": "2026-11-01"})
    before = _tasks_snapshot()
    if isinstance(outcome, Exception):
        install(error=outcome)
    else:
        install(outcome)

    r = _suggest(client, title="보고서")

    assert r.status_code == status
    assert _code(r) == code
    if message:
        assert r.json()["detail"]["message"] == message
    else:
        assert r.json()["detail"]["message"]
    assert _tasks_snapshot() == before


def test_missing_key_is_503_ai_disabled_and_server_still_works(client, monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    before = _tasks_snapshot()
    r = _suggest(client, title="보고서")
    assert r.status_code == 503
    assert _code(r) == "AI_DISABLED"
    assert r.json()["detail"]["message"] == "AI 기능 꺼짐"
    assert _tasks_snapshot() == before
    assert client.get("/tasks").status_code == 200


def test_key_value_never_appears_in_responses(client, install, monkeypatch):
    secret = "test-key-not-real"
    monkeypatch.setenv(API_KEY_ENV, secret)
    install(error=_error(anthropic.AuthenticationError, 401))
    assert secret not in _suggest(client, title="t").text
    install(FakeResponse(json.dumps(GOOD)))
    assert secret not in _suggest(client, title="t").text


# --- 기존 경로와 겹치지 않는다 ---------------------------------------------------


def test_existing_task_actions_still_work_after_adding_suggest(client, install):
    install(FakeResponse(json.dumps(GOOD)))
    created = client.post("/tasks", json={"title": "t", "priority": "LOW"})
    assert created.status_code == 201
    task_id = created.json()["id"]
    assert _suggest(client, title="t").status_code == 200
    assert client.patch(f"/tasks/{task_id}", json={"title": "새"}).status_code == 200
    assert client.patch(f"/tasks/{task_id}/status", json={"status": "DONE"}).status_code == 200
    assert [t["id"] for t in client.get("/tasks").json()] == [task_id]
    assert client.delete(f"/tasks/{task_id}").status_code == 204


def test_route_is_registered_as_post_only(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert list(paths["/tasks/suggest"]) == ["post"]
