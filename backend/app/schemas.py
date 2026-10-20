from pydantic import BaseModel

from app.rules import Status


class TaskCreate(BaseModel):
    title: str = ""
    description: str = ""


class Task(BaseModel):
    id: int
    title: str
    description: str
    status: Status


class StatusChange(BaseModel):
    status: str = ""
