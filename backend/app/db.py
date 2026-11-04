import os

import psycopg
from psycopg.rows import dict_row

# schema.sql이 만드는 테이블과 열. init_db는 이 열이 있는지만 확인한다.
EXPECTED_COLUMNS = {
    "users": {"id", "email", "password_hash", "created_at"},
    "sessions": {"token_hash", "user_id", "expires_at"},
    "tasks": {"id", "title", "description", "status", "owner_id", "priority", "due_date"},
    "subtasks": {"id", "task_id", "title", "description"},
}


def connect() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL이 설정되어 있지 않습니다. backend/.env를 확인하세요.")
    # autocommit: 여러 문장을 묶을 때만 conn.transaction()을 쓴다.
    # prepare_threshold=None: Supabase 풀러(6543, 트랜잭션 모드)는 prepared statement를 지원하지 않는다.
    return psycopg.connect(
        url, row_factory=dict_row, autocommit=True, prepare_threshold=None
    )


def init_db() -> None:
    """테이블은 만들지 않는다. backend/supabase/schema.sql이 만들고, 여기서는 열이 있는지만 확인한다."""
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT table_name, column_name FROM information_schema.columns"
            " WHERE table_schema = 'public' AND table_name = ANY(%s)",
            (list(EXPECTED_COLUMNS),),
        ).fetchall()
    finally:
        conn.close()
    found: dict[str, set[str]] = {}
    for r in rows:
        found.setdefault(r["table_name"], set()).add(r["column_name"])
    missing = [
        f"{table}.{column}"
        for table, columns in EXPECTED_COLUMNS.items()
        for column in sorted(columns - found.get(table, set()))
    ]
    if missing:
        raise RuntimeError(
            "필요한 열이 없습니다: "
            + ", ".join(missing)
            + ". backend/supabase/schema.sql을 먼저 적용하세요."
        )
