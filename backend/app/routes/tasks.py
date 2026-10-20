from fastapi import APIRouter

from app import db
from app.rules import Status, clean_title
from app.schemas import Task, TaskCreate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _to_task(row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=Status(row["status"]),
    )


@router.get("", response_model=list[Task])
def list_tasks() -> list[Task]:
    conn = db.connect()
    try:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    finally:
        conn.close()
    return [_to_task(r) for r in rows]


@router.post("", response_model=Task, status_code=201)
def create_task(body: TaskCreate) -> Task:
    title = clean_title(body.title)
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT INTO tasks (title, description, status) VALUES (?, ?, ?)",
            (title, body.description, Status.TODO.value),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()
    return _to_task(row)
