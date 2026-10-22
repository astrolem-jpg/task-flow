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


class TaskUpdate(BaseModel):
    title: str = ""
    description: str = ""


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
