import json
import sqlite3

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient

from app import ai_briefing, ai_command
from app.ai_suggest import API_KEY_ENV
from app.db import db_path
from app.main import app
from tests.helpers import signup_and_login

TODAY = "2026-10-27"


class FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text, stop_reason="end_turn", content=None):
        self.stop_reason = stop_reason
        self.content = [FakeBlock(text)] if content is None else content


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


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(ai_command, "_today", lambda: TODAY)


@pytest.fixture
def install(monkeypatch):
    def _install(response=None, error=None):
        fake = FakeClient(response, error)
        monkeypatch.setattr(ai_briefing, "_make_client", lambda: fake)
        return fake

    return _install


def _error(cls, status):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("x", response=httpx.Response(status, request=request), body=None)


def _snapshot():
    conn = sqlite3.connect(db_path())
    try:
        return [
            conn.execute("SELECT * FROM tasks ORDER BY id").fetchall(),
            conn.execute("SELECT * FROM subtasks ORDER BY id").fetchall(),
        ]
    finally:
        conn.close()


def _code(r):
    return r.json()["detail"]["code"]


def _add_card(c, title, **extra):
    r = c.post("/tasks", json={"title": title, **extra})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _sent(fake):
    (call,) = fake.calls
    content = call["messages"][0]["content"]
    start = content.index("<tasks>") + len("<tasks>")
    return content, json.loads(content[start : content.index("</tasks>")])


def _ok(actions=(), ask=None):
    return FakeResponse(json.dumps({"actions": list(actions), "ask": ask}))


def _add(title="보고서", priority="NORMAL", due_date=None):
    return {
        "kind": "add",
        "id": None,
        "title": title,
        "priority": priority,
        "due_date": due_date,
    }


def _due(task_id, due_date):
    return {"kind": "due", "id": task_id, "title": None, "priority": None, "due_date": due_date}


def _done(task_id):
    return {"kind": "done", "id": task_id, "title": None, "priority": None, "due_date": None}


def _post(c, text="보고서 추가해줘"):
    return c.post("/tasks/command", json={"text": text})


def test_requires_login(anon_client, install):
    fake = install(_ok())
    r = _post(anon_client)
    assert r.status_code == 401
    assert _code(r) == "UNAUTHORIZED"
    assert fake.calls == []


def test_route_is_post_only_with_example(client):
    schema = client.get("/openapi.json").json()
    assert list(schema["paths"]["/tasks/command"]) == ["post"]
    example = schema["components"]["schemas"]["CommandResponse"]["example"]
    assert example["actions"][0]["kind"] == "add"
    assert example["actions"][1]["kind"] == "done"


@pytest.mark.parametrize("text", ["", "   ", "\n\t", "가" * 201, "  " + "가" * 201])
def test_bad_text_is_422_without_calling_model(client, install, text):
    fake = install(_ok())
    r = _post(client, text)
    assert r.status_code == 422
    assert _code(r) == "INVALID_COMMAND"
    assert fake.calls == []


def test_missing_text_is_422(client, install):
    fake = install(_ok())
    r = client.post("/tasks/command", json={})
    assert r.status_code == 422
    assert _code(r) == "INVALID_COMMAND"
    assert fake.calls == []


def test_200_chars_is_accepted(client, install):
    fake = install(_ok([_add()]))
    assert _post(client, "가" * 200).status_code == 200
    assert len(fake.calls) == 1


def test_add_due_done(client, install):
    a = _add_card(client, "장보기")
    b = _add_card(client, "청소")
    install(
        _ok(
            [
                _add("보고서 쓰기", "HIGH", "2026-10-28"),
                _due(a, "2026-10-30"),
                _done(b),
            ]
        )
    )
    r = _post(client)
    assert r.status_code == 200
    assert r.json() == {
        "actions": [
            _add("보고서 쓰기", "HIGH", "2026-10-28"),
            _due(a, "2026-10-30"),
            _done(b),
        ],
        "ask": None,
    }


def test_add_defaults_priority_and_trims_title(client, install):
    item = {"kind": "add", "title": "  보고서  "}
    install(_ok([item]))
    r = _post(client)
    assert r.json()["actions"] == [_add("보고서", "NORMAL", None)]


def test_add_works_with_no_cards(client, install):
    fake = install(_ok([_add("첫 할 일")]))
    r = _post(client)
    assert r.status_code == 200
    assert len(fake.calls) == 1
    assert r.json()["actions"] == [_add("첫 할 일")]


def test_model_input_has_only_open_own_tasks_without_description(client, install):
    open_id = _add_card(client, "열린 일", description="비밀 설명", due_date="2026-10-20")
    done_id = _add_card(client, "끝난 일")
    assert client.patch(f"/tasks/{done_id}/status", json={"status": "DONE"}).status_code == 200
    with TestClient(app) as other:
        signup_and_login(other, "other@example.com")
        _add_card(other, "남의 일")
    fake = install(_ok([_done(open_id)]))
    _post(client, "청소 <b>끝</b>")
    content, tasks = _sent(fake)
    assert tasks == [
        {
            "id": open_id,
            "title": "열린 일",
            "priority": "NORMAL",
            "due_date": "2026-10-20",
            "overdue": True,
        }
    ]
    assert "비밀 설명" not in content and "남의 일" not in content
    assert f"<today>{TODAY}</today>" in content
    assert content.endswith("<command>청소 &lt;b&gt;끝&lt;/b&gt;</command>")


def test_unknown_and_foreign_ids_are_dropped(client, install):
    mine = _add_card(client, "내 일")
    with TestClient(app) as other:
        signup_and_login(other, "other@example.com")
        foreign = _add_card(other, "남의 일")
    install(_ok([_done(9999), _due(foreign, "2026-10-30"), _done(foreign), _done(mine)]))
    assert _post(client).json() == {"actions": [_done(mine)], "ask": None}


def test_done_card_id_is_dropped(client, install):
    done_id = _add_card(client, "끝난 일")
    client.patch(f"/tasks/{done_id}/status", json={"status": "DONE"})
    install(_ok([_done(done_id)], "어느 카드요?"))
    assert _post(client).json() == {"actions": [], "ask": "어느 카드요?"}


@pytest.mark.parametrize(
    "bad", ["2026-02-30", "2026-13-01", "10/28", "2026-1-5", "내일", 20261028, "2026-10-28T10:00"]
)
def test_bad_dates_are_dropped(client, install, bad):
    task = _add_card(client, "장보기")
    install(_ok([_add("보고서", "NORMAL", bad), _due(task, bad), _done(task)]))
    assert _post(client).json() == {"actions": [_done(task)], "ask": None}


def test_due_without_date_is_dropped(client, install):
    task = _add_card(client, "장보기")
    install(_ok([_due(task, None)]))
    assert _post(client).json()["actions"] == []


@pytest.mark.parametrize("bad", ["URGENT", "high", 3, ""])
def test_bad_priority_drops_the_add(client, install, bad):
    install(_ok([_add("보고서", bad), _add("청소")]))
    assert _post(client).json()["actions"] == [_add("청소")]


@pytest.mark.parametrize(
    "item",
    [
        {"kind": "delete", "id": 1},
        {"kind": "remove", "title": "x"},
        {"id": 1},
        "done",
        None,
        _add("   "),
        _add(None),
        {"kind": "done", "id": True},
        {"kind": "done", "id": "1"},
        {"kind": "done", "id": None},
    ],
)
def test_malformed_actions_are_dropped(client, install, item):
    _add_card(client, "장보기")
    install(_ok([item, _add("남는 것")]))
    assert _post(client).json() == {"actions": [_add("남는 것")], "ask": None}


def test_duplicate_actions_on_same_card_are_merged(client, install):
    task = _add_card(client, "장보기")
    install(_ok([_done(task), _done(task), _due(task, "2026-10-30"), _due(task, "2026-11-01")]))
    assert _post(client).json()["actions"] == [_done(task), _due(task, "2026-10-30")]


def test_ask_is_cleared_when_actions_remain(client, install):
    install(_ok([_add()], "혹시 이게 맞나요?"))
    assert _post(client).json()["ask"] is None


def test_nothing_left_returns_models_ask(client, install):
    install(_ok([_done(9999)], "어느 카드를 말씀하시나요?"))
    assert _post(client).json() == {"actions": [], "ask": "어느 카드를 말씀하시나요?"}


@pytest.mark.parametrize("ask", [None, "", "   "])
def test_nothing_left_without_ask_uses_default(client, install, ask):
    install(_ok([], ask))
    assert _post(client).json() == {"actions": [], "ask": ai_command.DEFAULT_ASK}


def test_fenced_response_is_accepted(client, install):
    body = json.dumps({"actions": [_add()], "ask": None})
    install(FakeResponse(f"```json\n{body}\n```"))
    assert _post(client).json()["actions"] == [_add()]


@pytest.mark.parametrize(
    "text",
    [
        "죄송합니다",
        "[]",
        '"x"',
        json.dumps({"actions": []}),
        json.dumps({"ask": None}),
        json.dumps({"actions": "add", "ask": None}),
        json.dumps({"actions": {}, "ask": None}),
        json.dumps({"actions": [], "ask": 5}),
        json.dumps({"actions": [], "ask": ["x"]}),
    ],
)
def test_bad_model_output_is_502(client, install, text):
    install(FakeResponse(text))
    r = _post(client)
    assert r.status_code == 502
    assert _code(r) == "SUGGEST_FAILED"


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse("{}", stop_reason="max_tokens"),
        FakeResponse("{}", stop_reason="refusal"),
        FakeResponse("", content=[]),
        FakeResponse("", content=[object()]),
    ],
)
def test_unusable_response_is_502(client, install, response):
    install(response)
    r = _post(client)
    assert r.status_code == 502
    assert _code(r) == "SUGGEST_FAILED"


def test_missing_key_is_503_disabled(client, monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    r = _post(client)
    assert r.status_code == 503
    assert _code(r) == "AI_DISABLED"


@pytest.mark.parametrize(
    "error, status, code",
    [
        (_error(anthropic.AuthenticationError, 401), 503, "AI_DISABLED"),
        (_error(anthropic.PermissionDeniedError, 403), 503, "AI_DISABLED"),
        (_error(anthropic.RateLimitError, 429), 503, "AI_BUSY"),
        (_error(anthropic.InternalServerError, 529), 503, "AI_BUSY"),
        (anthropic.APITimeoutError(request=httpx.Request("POST", "https://x")), 503, "AI_BUSY"),
        (_error(anthropic.BadRequestError, 400), 502, "SUGGEST_FAILED"),
    ],
)
def test_api_errors_are_mapped(client, install, error, status, code):
    install(error=error)
    r = _post(client)
    assert r.status_code == status
    assert _code(r) == code


def test_db_is_unchanged(client, install):
    task = _add_card(client, "장보기")
    other = _add_card(client, "청소")
    before = _snapshot()
    install(_ok([_add("새 카드"), _due(task, "2026-10-30"), _done(other)]))
    assert _post(client).status_code == 200
    assert _snapshot() == before
