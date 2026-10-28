from fastapi import APIRouter, Depends

from app import db
from app.auth import get_current_user
from app.rules import (
    SUBTASKS_MAX,
    RuleError,
    Status,
    clean_title,
    not_found,
    parse_due_date,
    parse_priority,
    parse_status,
    parse_subtasks,
    too_many_subtasks,
)
from app.schemas import (
    StatusChange,
    Subtask,
    SubtasksAdd,
    Task,
    TaskCreate,
    TaskUpdate,
    User,
)

# 로그인하지 않은 요청은 모든 Task 동작에서 401이다. (R-009, D-022)
# 카드는 소유자(owner_id)로 걸러 자기 카드만 다룬다. 남의 카드는 없는 카드와 같이 404다.
# 세부 항목은 소유자 열이 없다. 항상 부모 카드를 owner_id로 먼저 확인한 뒤에만 읽고 쓴다. (D-028)
router = APIRouter(
    prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)]
)


def _to_subtask(row) -> Subtask:
    return Subtask(id=row["id"], title=row["title"], description=row["description"])


def _to_task(row, subtasks: list[Subtask]) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=Status(row["status"]),
        priority=row["priority"],
        due_date=row["due_date"],
        subtasks=subtasks,
    )


def _fetch_task(conn, task_id: int, owner_id: int) -> Task | None:
    """자기 카드 하나를 세부 항목과 함께 읽는다. 없거나 남의 카드면 None이다."""
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ? AND owner_id = ?", (task_id, owner_id)
    ).fetchone()
    if row is None:
        return None
    subtasks = conn.execute(
        "SELECT * FROM subtasks WHERE task_id = ? ORDER BY id", (task_id,)
    ).fetchall()
    return _to_task(row, [_to_subtask(s) for s in subtasks])


def _insert_subtasks(conn, task_id: int, items: list[tuple[str, str]]) -> None:
    conn.executemany(
        "INSERT INTO subtasks (task_id, title, description) VALUES (?, ?, ?)",
        [(task_id, title, description) for title, description in items],
    )


@router.get("", response_model=list[Task])
def list_tasks(user: User = Depends(get_current_user)) -> list[Task]:
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE owner_id = ? ORDER BY id", (user.id,)
        ).fetchall()
        # 부모 카드의 owner_id로 걸러 자기 카드의 세부 항목만 읽는다.
        sub_rows = conn.execute(
            "SELECT s.* FROM subtasks s JOIN tasks t ON t.id = s.task_id"
            " WHERE t.owner_id = ? ORDER BY s.id",
            (user.id,),
        ).fetchall()
    finally:
        conn.close()
    by_task: dict[int, list[Subtask]] = {}
    for s in sub_rows:
        by_task.setdefault(s["task_id"], []).append(_to_subtask(s))
    return [_to_task(r, by_task.get(r["id"], [])) for r in rows]


@router.post("", response_model=Task, status_code=201)
def create_task(body: TaskCreate, user: User = Depends(get_current_user)) -> Task:
    title = clean_title(body.title)
    priority = parse_priority(body.priority)
    due_date = parse_due_date(body.due_date)
    subtasks = parse_subtasks(body.subtasks)
    conn = db.connect()
    try:
        # 카드와 세부 항목은 한 트랜잭션이다. 어느 하나라도 실패하면 카드도 만들지 않는다.
        cur = conn.execute(
            "INSERT INTO tasks (title, description, status, priority, due_date, owner_id)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (title, body.description, Status.TODO.value, priority.value, due_date, user.id),
        )
        _insert_subtasks(conn, cur.lastrowid, subtasks)
        conn.commit()
        task = _fetch_task(conn, cur.lastrowid, user.id)
    finally:
        conn.close()
    return task


@router.post("/{task_id}/subtasks", response_model=Task, status_code=201)
def add_subtasks(
    task_id: int, body: SubtasksAdd, user: User = Depends(get_current_user)
) -> Task:
    """기존 카드에 세부 항목을 붙인다(R-015, D-028). 한 번에 모두 붙거나 하나도 안 붙는다."""
    items = parse_subtasks(body.items)
    if not items:
        raise RuleError(
            "INVALID_SUBTASKS", "붙일 세부 항목이 없습니다.", 422
        )
    conn = db.connect()
    try:
        if _fetch_task(conn, task_id, user.id) is None:
            raise not_found()
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM subtasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        if count + len(items) > SUBTASKS_MAX:
            raise too_many_subtasks()
        _insert_subtasks(conn, task_id, items)
        conn.commit()
        task = _fetch_task(conn, task_id, user.id)
    finally:
        conn.close()
    return task


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: int, body: TaskUpdate, user: User = Depends(get_current_user)
) -> Task:
    title = clean_title(body.title)
    # 보내지 않은 priority, due_date는 그대로 둔다. due_date는 null이면 지운다.
    # 세부 항목은 바꾸지 않는다.
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
        task = _fetch_task(conn, task_id, user.id)
    finally:
        conn.close()
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, user: User = Depends(get_current_user)) -> None:
    conn = db.connect()
    try:
        cur = conn.execute(
            "DELETE FROM tasks WHERE id = ? AND owner_id = ?", (task_id, user.id)
        )
        if cur.rowcount == 0:
            raise not_found()
        # 자기 카드를 지운 경우에만 세부 항목을 지운다. 같은 트랜잭션이다. (D-028)
        conn.execute("DELETE FROM subtasks WHERE task_id = ?", (task_id,))
        conn.commit()
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
        task = _fetch_task(conn, task_id, user.id)
    finally:
        conn.close()
    return task
