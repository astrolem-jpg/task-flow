from pydantic import BaseModel

from app.rules import Priority, Status


# priority, due_date는 보냈는지(model_fields_set)와 값 검증을 rules.py가 맡는다.
# 허용 밖의 값이 pydantic의 기본 오류가 아니라 규칙 오류(422)로 돌아가게 object로 받는다. (D-004)
class TaskCreate(BaseModel):
    title: str = ""
    description: str = ""
    priority: object = Priority.NORMAL.value
    due_date: object = None


class Task(BaseModel):
    id: int
    title: str
    description: str
    status: Status
    priority: Priority
    due_date: str | None


class TaskUpdate(BaseModel):
    title: str = ""
    description: str = ""
    priority: object = None
    due_date: object = None


class StatusChange(BaseModel):
    status: str = ""


class SignupRequest(BaseModel):
    email: str = ""
    password: str = ""


class LoginRequest(BaseModel):
    email: str = ""
    password: str = ""


class User(BaseModel):
    id: int
    email: str
