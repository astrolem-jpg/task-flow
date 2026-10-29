from pydantic import BaseModel

from app.rules import Priority, Status


# priority, due_date는 보냈는지(model_fields_set)와 값 검증을 rules.py가 맡는다.
# 허용 밖의 값이 pydantic의 기본 오류가 아니라 규칙 오류(422)로 돌아가게 object로 받는다. (D-004)
# subtasks도 모양 검사를 rules.py(parse_subtasks)가 맡아 규칙 오류(422)로 돌아가게 object로 받는다.
class TaskCreate(BaseModel):
    title: str = ""
    description: str = ""
    priority: object = Priority.NORMAL.value
    due_date: object = None
    subtasks: object = None


# 카드에 딸린 세부 항목(R-015, D-028). 제목과 설명만 가진다.
class Subtask(BaseModel):
    id: int
    title: str
    description: str


class Task(BaseModel):
    id: int
    title: str
    description: str
    status: Status
    priority: Priority
    due_date: str | None
    subtasks: list[Subtask]


class SubtasksAdd(BaseModel):
    items: object = None


class TaskUpdate(BaseModel):
    title: str = ""
    description: str = ""
    priority: object = None
    due_date: object = None


# AI 제안은 저장하지 않는다. 요청은 입력 중인 제목과 설명이고, 응답은 제안 값과 근거다.
class SuggestRequest(BaseModel):
    title: str = ""
    description: str = ""


class SuggestResponse(BaseModel):
    priority: Priority
    due_date: str | None
    reason: str


# AI로 할일 만들기도 저장하지 않는다. 요청은 SuggestRequest와 같고, 응답은 후보 목록이다.
class TaskCandidate(BaseModel):
    title: str
    description: str
    priority: Priority
    due_date: str | None


class SuggestTasksResponse(BaseModel):
    items: list[TaskCandidate]


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


# 오늘 브리핑은 읽기만 한다. 응답은 먼저 할 일 최대 3개(근거 포함), 나중에 해도 되는 id, 응원 한 줄이다.
class BriefingPick(BaseModel):
    id: int
    reason: str


class BriefingResponse(BaseModel):
    top3: list[BriefingPick]
    later: list[int]
    cheer: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "top3": [{"id": 12, "reason": "어제 마감이라 가장 먼저 해야 해요."}],
                "later": [7, 9],
                "cheer": "오늘도 한 걸음씩, 잘하고 있어요!",
            }
        }
    }
