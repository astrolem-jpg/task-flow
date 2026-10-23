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


def test_fresh_db_gets_tasks_users_and_sessions(db_file):
    migrate()
    assert {"tasks", "users", "sessions", "alembic_version"} <= _tables(db_file)
    assert _columns(db_file, "users") == ["id", "email", "password_hash", "created_at"]
    assert _columns(db_file, "sessions") == ["token_hash", "user_id", "expires_at"]
    assert _columns(db_file, "tasks") == ["id", "title", "description", "status", "owner_id"]
    conn = sqlite3.connect(db_file)
    indexes = {r[1] for r in conn.execute("PRAGMA index_list(tasks)")}
    conn.close()
    assert "ix_tasks_owner_id" in indexes


def test_legacy_db_keeps_cards_after_upgrade(db_file):
    conn = sqlite3.connect(db_file)
    conn.execute(LEGACY_SCHEMA)
    conn.execute("INSERT INTO tasks (title, description, status) VALUES ('옛 카드', 'd', 'DONE')")
    conn.commit()
    conn.close()

    migrate()

    conn = sqlite3.connect(db_file)
    rows = conn.execute("SELECT title, description, status, owner_id FROM tasks").fetchall()
    conn.close()
    assert rows == [("옛 카드", "d", "DONE", None)]
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


def test_downgrade_to_baseline_keeps_tasks(db_file):
    migrate()
    downgrade("0001")
    assert not {"users", "sessions"} & _tables(db_file)
    assert "tasks" in _tables(db_file)
    assert _columns(db_file, "tasks") == ["id", "title", "description", "status"]


def test_downgrade_owner_id_keeps_cards_and_autoincrement(db_file):
    migrate("0003")
    conn = sqlite3.connect(db_file)
    conn.execute("INSERT INTO tasks (title) VALUES ('남아야 함')")
    conn.commit()
    conn.close()
    migrate()
    downgrade("0003")
    assert _columns(db_file, "tasks") == ["id", "title", "description", "status"]
    conn = sqlite3.connect(db_file)
    titles = [r[0] for r in conn.execute("SELECT title FROM tasks")]
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'tasks'").fetchone()[0]
    conn.close()
    assert titles == ["남아야 함"]
    assert "AUTOINCREMENT" in sql.upper()


def test_downgrade_sessions_keeps_users(db_file):
    migrate()
    downgrade("0002")
    assert "sessions" not in _tables(db_file)
    assert "users" in _tables(db_file)
