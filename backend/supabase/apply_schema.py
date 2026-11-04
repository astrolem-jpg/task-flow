"""backend/.env 의 DATABASE_URL 로 연결해 schema.sql 을 한 번 실행하고 테이블별 주인 · RLS 를 출력한다.

실행 (psycopg 는 --with 로만 쓴다. pyproject 는 바꾸지 않는다):
    uv run --with "psycopg[binary]" python supabase/apply_schema.py
"""
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
TABLES = ("users", "sessions", "tasks", "subtasks")

CHECK_SQL = """
select c.relname, r.rolname, c.relrowsecurity
from pg_class c
join pg_roles r on r.oid = c.relowner
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r' and c.relname = any(%s)
"""


def main() -> int:
    load_dotenv(HERE.parent / ".env")
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL 이 backend/.env 에 없습니다.", file=sys.stderr)
        return 1

    sql = (HERE / "schema.sql").read_text(encoding="utf-8")
    try:
        with psycopg.connect(url) as conn:
            conn.execute(sql)
            rows = conn.execute(CHECK_SQL, (list(TABLES),)).fetchall()
    except psycopg.Error as exc:
        # 연결 문자열은 출력하지 않는다.
        print(f"실패: {type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''}", file=sys.stderr)
        return 1

    found = {name: (owner, rls) for name, owner, rls in rows}
    for name in TABLES:
        if name not in found:
            print(f"{name:<9} 없음")
            continue
        owner, rls = found[name]
        print(f"{name:<9} owner={owner}  rls={'on' if rls else 'off'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
