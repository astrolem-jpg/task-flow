from fastapi import APIRouter, Depends

from app import db
from app.auth import get_current_user
from app.rules import (
    Status,
    clean_title,
    not_found,
    parse_due_date,
    parse_priority,
    parse_status,
)
from app.schemas import StatusChange, Task, TaskCreate, TaskUpdate, User

# 로그인하지 않은 요청은 모든 Task 동작에서 401이다. (R-009, D-022)
# 카드는 소유자(owner_id)로 걸러 자기 카드만 다룬다. 남의 카드는 없는 카드와 같이 404다.
router = APIRouter(
    prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)]
)


def _to_task(row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=Status(row["status"]),
        priority=row["priority"],
        due_date=row["due_date"],
    )


@router.get("", response_model=list[Task])
def list_tasks(user: User = Depends(get_current_user)) -> list[Task]:
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE owner_id = ? ORDER BY id", (user.id,)
        ).fetchall()
    finally:
        conn.close()
    return [_to_task(r) for r in rows]


@router.post("", response_model=Task, status_code=201)
def create_task(body: TaskCreate, user: User = Depends(get_current_user)) -> Task:
    title = clean_title(body.title)
    priority = parse_priority(body.priority)
    due_date = parse_due_date(body.due_date)
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT INTO tasks (title, description, status, priority, due_date, owner_id)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (title, body.description, Status.TODO.value, priority.value, due_date, user.id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()
    return _to_task(row)


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: int, body: TaskUpdate, user: User = Depends(get_current_user)
) -> Task:
    title = clean_title(body.title)
    # 보내지 않은 priority, due_date는 그대로 둔다. due_date는 null이면 지운다.
    sets = ["title = ?", "description = ?"]
    values: list = [title, body.description]
    if "priority" in body.model_fields_set:
        sets.append("priority = ?")
        values.append(parse_priority(body.priority).value)
    if "due_date" in body.model_fields_set:
        sets.append("due_date = ?")
        values.append(parse_due_date(body.due_date))
    conn = db.connect()
    try:
        cur = conn.execute(
            f"UPDATE tasks SET {', '.join(sets)} WHERE id = ? AND owner_id = ?",
            (*values, task_id, user.id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise not_found()
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND owner_id = ?", (task_id, user.id)
        ).fetchone()
    finally:
        conn.close()
    return _to_task(row)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, user: User = Depends(get_current_user)) -> None:
    conn = db.connect()
    try:
        cur = conn.execute(
            "DELETE FROM tasks WHERE id = ? AND owner_id = ?", (task_id, user.id)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise not_found()
    finally:
        conn.close()


@router.patch("/{task_id}/status", response_model=Task)
def change_status(
    task_id: int, body: StatusChange, user: User = Depends(get_current_user)
) -> Task:
    status = parse_status(body.status)
    conn = db.connect()
    try:
        cur = conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ? AND owner_id = ?",
            (status.value, task_id, user.id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise not_found()
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND owner_id = ?", (task_id, user.id)
        ).fetchone()
    finally:
        conn.close()
    return _to_task(row)
