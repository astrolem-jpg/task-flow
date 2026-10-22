import sqlite3

import pytest

from tests.helpers import downgrade, migrate

# M1에서 만든 파일의 tasks 구조(Alembic 도입 전)
LEGACY_SCHEMA = """
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'TODO'
)
"""


def _tables(path):
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    finally:
        conn.close()
    return {r[0] for r in rows}


def _columns(path, table):
    conn = sqlite3.connect(path)
    try:
        return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    finally:
        conn.close()


@pytest.fixture
def db_file(tmp_path, monkeypatch):
    path = tmp_path / "mig.db"
    monkeypatch.setenv("TASKFLOW_DB", str(path))
    return path


def test_fresh_db_gets_tasks_and_users(db_file):
    migrate()
    assert {"tasks", "users", "alembic_version"} <= _tables(db_file)
    assert _columns(db_file, "users") == ["id", "email", "password_hash", "created_at"]
    assert _columns(db_file, "tasks") == ["id", "title", "description", "status"]


def test_legacy_db_keeps_cards_after_upgrade(db_file):
    conn = sqlite3.connect(db_file)
    conn.execute(LEGACY_SCHEMA)
    conn.execute("INSERT INTO tasks (title, description, status) VALUES ('옛 카드', 'd', 'DONE')")
    conn.commit()
    conn.close()

    migrate()

    conn = sqlite3.connect(db_file)
    rows = conn.execute("SELECT title, description, status FROM tasks").fetchall()
    conn.close()
    assert rows == [("옛 카드", "d", "DONE")]
    assert "users" in _tables(db_file)


def test_upgrade_twice_is_safe(db_file):
    migrate()
    migrate()
    assert "users" in _tables(db_file)


def test_users_email_is_unique(db_file):
    migrate()
    conn = sqlite3.connect(db_file)
    conn.execute("INSERT INTO users (email, password_hash, created_at) VALUES ('a@x.com', 'h', 't')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO users (email, password_hash, created_at) VALUES ('a@x.com', 'h', 't')")
    conn.close()


def test_downgrade_users_keeps_tasks(db_file):
    migrate()
    downgrade("0001")
    assert "users" not in _tables(db_file)
    assert "tasks" in _tables(db_file)
