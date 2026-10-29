import sqlite3

from app.db import db_path
from tests.test_tasks_weekplan import FIRST, _add, _day, _ok, _post, fixed_today, install  # noqa: F401


def _set_due_date(task_id, value):
    # API는 규칙 밖 마감일을 막으므로, 이미 DB에 들어 있는 경우를 직접 만든다.
    conn = sqlite3.connect(db_path())
    try:
        conn.execute("UPDATE tasks SET due_date = ? WHERE id = ?", (value, task_id))
        conn.commit()
    finally:
        conn.close()


def test_board_survives_due_date_outside_the_rule(client):
    bad = _add(client, "규칙 밖")
    good = _add(client, "정상", due_date="2026-10-30")
    _set_due_date(bad, "다음주")
    r = client.get("/tasks")
    assert r.status_code == 200
    assert {t["id"]: t["due_date"] for t in r.json()} == {bad: "다음주", good: "2026-10-30"}


def test_weekplan_survives_due_date_outside_the_rule(client, install):  # noqa: F811
    bad = _add(client, "규칙 밖")
    good = _add(client, "정상", due_date="2026-10-30")
    _set_due_date(bad, "다음주")
    install(_ok([_day(FIRST, bad, good)]))
    r = _post(client)
    assert r.status_code == 200
    assert r.json()["days"] == [_day(FIRST, bad, good)]
