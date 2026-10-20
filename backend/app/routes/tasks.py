from fastapi import APIRouter

from app import db
from app.rules import Status, clean_title, not_found, parse_status
from app.schemas import StatusChange, Task, TaskCreate, TaskUpdate

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


@router.patch("/{task_id}", response_model=Task)
def update_task(task_id: int, body: TaskUpdate) -> Task:
    title = clean_title(body.title)
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE tasks SET title = ?, description = ? WHERE id = ?",
            (title, body.description, task_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise not_found()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    finally:
        conn.close()
    return _to_task(row)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int) -> None:
    conn = db.connect()
    try:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise not_found()
    finally:
        conn.close()


@router.patch("/{task_id}/status", response_model=Task)
def change_status(task_id: int, body: StatusChange) -> Task:
    status = parse_status(body.status)
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ?", (status.value, task_id)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise not_found()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    finally:
        conn.close()
    return _to_task(row)
