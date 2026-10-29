import json
import sqlite3

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient

from app import ai_briefing, ai_weekplan
from app.ai_suggest import API_KEY_ENV
from app.db import db_path
from app.main import app
from tests.helpers import signup_and_login

TODAY = "2026-10-27"
FIRST, LAST = "2026-10-27", "2026-11-02"  # 오늘부터 7일
EMPTY = {"days": [], "note": "오늘은 비어 있어요"}


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
    monkeypatch.setattr(ai_weekplan, "_today", lambda: TODAY)


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


def _add(c, title, **extra):
    r = c.post("/tasks", json={"title": title, **extra})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _sent(fake):
    (call,) = fake.calls
    content = call["messages"][0]["content"]
    start = content.index("<tasks>") + len("<tasks>")
    return content, json.loads(content[start : content.rindex("</tasks>")])


def _ok(days=(), note="차근차근 해요"):
    return FakeResponse(json.dumps({"days": list(days), "note": note}))


def _day(date, *ids):
    return {"date": date, "ids": list(ids)}


def _post(c):
    return c.post("/tasks/weekplan")


def test_requires_login(anon_client, install):
    fake = install(_ok())
    r = _post(anon_client)
    assert r.status_code == 401
    assert _code(r) == "UNAUTHORIZED"
    assert fake.calls == []


def test_route_is_post_only_with_example(client):
    schema = client.get("/openapi.json").json()
    assert list(schema["paths"]["/tasks/weekplan"]) == ["post"]
    example = schema["components"]["schemas"]["WeekPlanResponse"]["example"]
    assert example["days"][0] == {"date": "2026-10-27", "ids": [12]}
    assert "note" in example


def test_success_returns_days_and_note(client, install):
    a = _add(client, "보고서", due_date="2026-10-30")
    b = _add(client, "청소")
    install(_ok([_day("2026-10-29", a), _day("2026-10-28", b)], "화이팅"))
    r = _post(client)
    assert r.status_code == 200
    assert r.json() == {
        "days": [
            {"date": "2026-10-28", "ids": [b]},
            {"date": "2026-10-29", "ids": [a]},
        ],
        "note": "화이팅",
    }


def test_task_without_due_date_is_placed(client, install):
    n = _add(client, "마감 없는 일")
    install(_ok([_day("2026-10-31", n)]))
    assert _post(client).json()["days"] == [{"date": "2026-10-31", "ids": [n]}]


def test_model_input_has_only_open_own_tasks_without_description(client, install):
    open_id = _add(client, "열린 일", description="비밀 설명", priority="HIGH")
    done_id = _add(client, "끝난 일")
    client.patch(f"/tasks/{done_id}/status", json={"status": "DONE"})
    with TestClient(app) as other:
        signup_and_login(other, "other@example.com")
        _add(other, "남의 일")
    fake = install(_ok([_day(FIRST, open_id)]))
    assert _post(client).status_code == 200
    content, tasks = _sent(fake)
    assert [t["id"] for t in tasks] == [open_id]
    for leaked in ("비밀 설명", "끝난 일", "남의 일", "description"):
        assert leaked not in content
    assert content.startswith(f"<today>{TODAY}</today>\n")
    (call,) = fake.calls
    assert call["thinking"] == {"type": "disabled"}
    assert call["max_tokens"] == ai_weekplan.MAX_TOKENS


def test_no_open_tasks_skips_the_model(client, install):
    fake = install(_ok())
    r = _post(client)
    assert (r.status_code, r.json()) == (200, EMPTY)
    done = _add(client, "끝")
    client.patch(f"/tasks/{done}/status", json={"status": "DONE"})
    assert _post(client).json() == EMPTY
    assert fake.calls == []


def test_dates_outside_seven_days_are_dropped(client, install):
    a = _add(client, "a")
    b = _add(client, "b")
    c = _add(client, "c")
    d = _add(client, "d")
    install(
        _ok(
            [
                _day("2026-10-26", a),  # 어제
                _day(FIRST, b),
                _day(LAST, c),
                _day("2026-11-03", d),  # 8번째 날
            ]
        )
    )
    days = _post(client).json()["days"]
    assert days == [_day(FIRST, b), _day(LAST, c)]


@pytest.mark.parametrize("bad", ["2026-13-45", "10/28", "", None, 20261028])
def test_bad_dates_are_dropped(client, install, bad):
    a = _add(client, "a")
    b = _add(client, "b")
    install(_ok([{"date": bad, "ids": [a]}, _day(FIRST, b)]))
    assert _post(client).json()["days"] == [_day(FIRST, b)]


def test_unknown_ids_are_dropped(client, install):
    a = _add(client, "a")
    install(_ok([_day(FIRST, 999, a)]))
    assert _post(client).json()["days"] == [_day(FIRST, a)]


def test_id_goes_into_one_day_only(client, install):
    a = _add(client, "a")
    b = _add(client, "b")
    install(_ok([_day("2026-10-28", a, a, b), _day("2026-10-29", a)]))
    assert _post(client).json()["days"] == [_day("2026-10-28", a, b)]


def test_same_date_is_merged_and_empty_days_removed(client, install):
    a = _add(client, "a")
    b = _add(client, "b")
    install(_ok([_day(FIRST, a), _day("2026-10-28"), _day(FIRST, b)]))
    assert _post(client).json()["days"] == [_day(FIRST, a, b)]


def test_nothing_left_is_502(client, install):
    a = _add(client, "a")
    install(_ok([_day("2030-01-01", a), _day(FIRST, 999)]))
    r = _post(client)
    assert r.status_code == 502
    assert _code(r) == "SUGGEST_FAILED"


def _doc(**kw):
    base = {"days": [], "note": "n"}
    base.update(kw)
    return json.dumps(base)


BAD_TEXTS = {
    "not_json": "안녕하세요",
    "not_object": "[1, 2]",
    "missing_note": json.dumps({"days": []}),
    "missing_days": json.dumps({"note": "n"}),
    "empty_days": _doc(),
    "days_not_list": _doc(days={}),
    "note_not_str": _doc(note=1),
    "day_not_dict": _doc(days=[1]),
    "ids_not_list": _doc(days=[{"date": FIRST, "ids": "1"}]),
    "id_str": _doc(days=[{"date": FIRST, "ids": ["1"]}]),
    "id_bool": _doc(days=[{"date": FIRST, "ids": [True]}]),
}


@pytest.mark.parametrize("name", list(BAD_TEXTS))
def test_bad_model_output_is_502(client, install, name):
    _add(client, "a")
    install(FakeResponse(BAD_TEXTS[name]))
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
    ids=["truncated", "refusal", "empty_content", "non_text_block"],
)
def test_unusable_response_is_502(client, install, response):
    _add(client, "a")
    install(response)
    r = _post(client)
    assert r.status_code == 502
    assert _code(r) == "SUGGEST_FAILED"


def test_missing_key_is_503_disabled(client, monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    _add(client, "a")
    r = _post(client)
    assert r.status_code == 503
    assert _code(r) == "AI_DISABLED"


@pytest.mark.parametrize(
    "error, status, code",
    [
        (_error(anthropic.RateLimitError, 429), 503, "AI_BUSY"),
        (_error(anthropic.AuthenticationError, 401), 503, "AI_DISABLED"),
        (_error(anthropic.BadRequestError, 400), 502, "SUGGEST_FAILED"),
    ],
    ids=["rate_limit", "auth", "bad_request"],
)
def test_api_errors_are_mapped(client, install, error, status, code):
    _add(client, "a")
    install(error=error)
    r = _post(client)
    assert r.status_code == status
    assert _code(r) == code


def test_db_is_unchanged(client, install):
    a = _add(client, "a", due_date="2026-10-30")
    _add(client, "b")
    before = _snapshot()
    install(_ok([_day(FIRST, a)]))
    assert _post(client).status_code == 200
    install(FakeResponse("not json"))
    assert _post(client).status_code == 502
    assert _snapshot() == before
