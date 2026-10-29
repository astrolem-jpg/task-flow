import json
import sqlite3

import anthropic
import httpx
import pytest

from app import ai_suggest
from app.ai_suggest import (
    API_KEY_ENV,
    MODEL,
    TASKS_MAX_TOKENS,
    TASKS_SYSTEM_PROMPT,
    parse_task_candidates,
)
from app.db import db_path
from app.rules import RuleError


def _item(n=1, **over):
    item = {
        "title": f"할 일 {n}",
        "description": f"설명 {n}",
        "priority": "NORMAL",
        "due_date": None,
    }
    item.update(over)
    return item


def _items(count):
    return [_item(n) for n in range(1, count + 1)]


def _text(count=4):
    return json.dumps({"items": _items(count)})


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


def _post(c, **body):
    return c.post("/tasks/suggest-tasks", json=body)


def _code(r):
    return r.json()["detail"]["code"]


# --- 정상: 3~5개가 미리 보기로 나온다 -------------------------------------------


@pytest.mark.parametrize("count", [3, 4, 5])
def test_returns_three_to_five_candidates(client, install, count):
    install(FakeResponse(_text(count)))
    r = _post(client, title="이사 준비")
    assert r.status_code == 200
    assert r.json() == {"items": _items(count)}


def test_requests_four_and_passes_topic_server_date_and_agreed_settings(client, install):
    fake = install(FakeResponse(_text()))
    _post(client, title="  이사 준비  ", description="다음 달")
    (call,) = fake.calls
    assert call["messages"][0]["content"] == (
        "<today>2026-10-27</today>\n<title>이사 준비</title>\n<description>다음 달</description>"
    )
    assert call["model"] == MODEL == "claude-haiku-5-5"
    assert call["thinking"] == {"type": "disabled"}
    assert call["max_tokens"] == TASKS_MAX_TOKENS
    assert "4개" in call["system"]
    assert "{count}" not in call["system"]
    assert "{count}" in TASKS_SYSTEM_PROMPT


def test_works_without_description_and_without_any_card(client, install):
    install(FakeResponse(_text()))
    assert client.get("/tasks").json() == []
    assert _post(client, title="주제만").status_code == 200


def test_candidates_keep_priority_due_date_and_past_dates(client, install):
    items = [
        _item(1, priority="HIGH", due_date="2026-10-28"),
        _item(2, priority="LOW", due_date="2020-01-01"),
        _item(3, description=""),
    ]
    install(FakeResponse(json.dumps({"items": items})))
    assert _post(client, title="t").json()["items"] == items


def test_candidate_title_and_description_are_trimmed(client, install):
    install(FakeResponse(json.dumps({"items": [_item(1, title="  제목  ", description=" 설 명 "), _item(2), _item(3)]})))
    first = _post(client, title="t").json()["items"][0]
    assert (first["title"], first["description"]) == ("제목", "설 명")


@pytest.mark.parametrize("wrap", ["```json\n{}\n```", "```\n{}\n```", "'''json\n{}\n'''"])
def test_code_block_marks_are_accepted(client, install, wrap):
    install(FakeResponse(wrap.replace("{}", _text())))
    assert _post(client, title="t").status_code == 200


# --- 저장하지 않는다 -----------------------------------------------------------


def test_success_does_not_create_or_change_cards(client, install):
    client.post("/tasks", json={"title": "기존", "description": "d", "priority": "LOW"})
    before = _tasks_snapshot()
    install(FakeResponse(_text()))
    assert _post(client, title="이사").status_code == 200
    assert _tasks_snapshot() == before
    assert [t["title"] for t in client.get("/tasks").json()] == ["기존"]


# --- 로그인, 입력 --------------------------------------------------------------


def test_requires_login(anon_client, install):
    fake = install(FakeResponse(_text()))
    r = _post(anon_client, title="t")
    assert r.status_code == 401
    assert _code(r) == "UNAUTHORIZED"
    assert fake.calls == []


@pytest.mark.parametrize("title", ["", "   ", "\n\t"])
def test_blank_title_is_400_and_model_not_called(client, install, title):
    fake = install(FakeResponse(_text()))
    r = _post(client, title=title)
    assert r.status_code == 400
    assert _code(r) == "TITLE_REQUIRED"
    assert fake.calls == []


# --- 응답 검사: 하나라도 어긋나면 전체가 502 -----------------------------------

BAD_BODIES = {
    "not-json": "후보: 청소",
    "not-object": json.dumps(_items(4)),
    "no-items-key": json.dumps({"tasks": _items(4)}),
    "items-not-list": json.dumps({"items": "x"}),
    "too-few": _text(2),
    "too-many": _text(6),
    "empty": _text(0),
    "item-not-object": json.dumps({"items": [*_items(3), "x"]}),
    "missing-key": json.dumps({"items": [*_items(3), {"title": "t", "priority": "LOW", "due_date": None}]}),
    "title-not-string": json.dumps({"items": [*_items(3), _item(4, title=5)]}),
    "title-blank": json.dumps({"items": [*_items(3), _item(4, title="   ")]}),
    "description-not-string": json.dumps({"items": [*_items(3), _item(4, description=None)]}),
    "bad-priority": json.dumps({"items": [*_items(3), _item(4, priority="URGENT")]}),
    "lowercase-priority": json.dumps({"items": [*_items(3), _item(4, priority="high")]}),
    "bad-date-format": json.dumps({"items": [*_items(3), _item(4, due_date="10/28")]}),
    "impossible-date": json.dumps({"items": [*_items(3), _item(4, due_date="2026-02-30")]}),
}


@pytest.mark.parametrize("body", BAD_BODIES.values(), ids=BAD_BODIES.keys())
def test_invalid_model_answers_are_502_and_leave_cards_unchanged(client, install, body):
    client.post("/tasks", json={"title": "기존", "priority": "HIGH", "due_date": "2026-11-01"})
    before = _tasks_snapshot()
    install(FakeResponse(body))
    r = _post(client, title="t")
    assert r.status_code == 502
    assert _code(r) == "SUGGEST_FAILED"
    assert r.json()["detail"]["message"] == "제안 실패"
    assert _tasks_snapshot() == before


@pytest.mark.parametrize("stop_reason", ["max_tokens", "refusal"])
def test_truncated_or_refused_answer_is_502(client, install, stop_reason):
    install(FakeResponse(_text(), stop_reason=stop_reason))
    r = _post(client, title="t")
    assert (r.status_code, _code(r)) == (502, "SUGGEST_FAILED")


def test_parse_function_raises_rule_error_not_value_error():
    with pytest.raises(RuleError) as info:
        parse_task_candidates("not json")
    assert (info.value.status_code, info.value.code) == (502, "SUGGEST_FAILED")


# --- 실패: 7절과 같은 상태와 코드, DB는 그대로 ----------------------------------

CALL_FAILURES = [
    (_error(anthropic.RateLimitError, 429), 503, "AI_BUSY"),
    (_error(anthropic.OverloadedError, 529), 503, "AI_BUSY"),
    (_error(anthropic.InternalServerError, 500), 503, "AI_BUSY"),
    (_error(anthropic.AuthenticationError, 401), 503, "AI_DISABLED"),
    (_error(anthropic.PermissionDeniedError, 403), 503, "AI_DISABLED"),
    (_error(anthropic.BadRequestError, 400), 502, "SUGGEST_FAILED"),
]


@pytest.mark.parametrize(
    "error,status,code",
    CALL_FAILURES,
    ids=["rate-limit", "overloaded", "server-error", "bad-key", "forbidden", "bad-request"],
)
def test_call_failures_use_the_agreed_status_and_leave_cards_unchanged(
    client, install, error, status, code
):
    client.post("/tasks", json={"title": "기존"})
    before = _tasks_snapshot()
    install(error=error)
    r = _post(client, title="t")
    assert (r.status_code, _code(r)) == (status, code)
    assert r.json()["detail"]["message"]
    assert _tasks_snapshot() == before


def test_missing_key_is_503_ai_disabled_and_other_features_work(client, monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    r = _post(client, title="t")
    assert (r.status_code, _code(r)) == (503, "AI_DISABLED")
    assert r.json()["detail"]["message"] == "AI 기능 꺼짐"
    assert client.get("/tasks").status_code == 200
    assert client.post("/tasks", json={"title": "직접 등록"}).status_code == 201


def test_key_value_never_appears_in_responses(client, install, monkeypatch):
    secret = "test-key-not-real"
    monkeypatch.setenv(API_KEY_ENV, secret)
    install(error=_error(anthropic.AuthenticationError, 401))
    assert secret not in _post(client, title="t").text
    install(FakeResponse(_text()))
    assert secret not in _post(client, title="t").text


# --- 기존 경로와 겹치지 않는다 ---------------------------------------------------


def test_registering_candidates_uses_the_existing_create_api(client, install):
    install(FakeResponse(_text(3)))
    items = _post(client, title="이사").json()["items"]
    created = [client.post("/tasks", json=item) for item in items]
    assert [r.status_code for r in created] == [201, 201, 201]
    assert [t["title"] for t in client.get("/tasks").json()] == [i["title"] for i in items]


def test_other_users_cards_are_not_affected(client, install):
    install(FakeResponse(_text()))
    client.post("/tasks", json={"title": "내 카드"})
    before = _tasks_snapshot()
    _post(client, title="t")
    assert _tasks_snapshot() == before


def test_existing_suggest_route_and_new_route_are_both_post_only(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert list(paths["/tasks/suggest"]) == ["post"]
    assert list(paths["/tasks/suggest-tasks"]) == ["post"]
