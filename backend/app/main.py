import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import require_session_secret
from app.routes import auth, briefing, suggest, tasks, weekplan
from app.rules import RuleError


@asynccontextmanager
async def lifespan(_: FastAPI):
    require_session_secret()
    yield


app = FastAPI(title="task-flow API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"code": code, "message": message}},
    )


@app.exception_handler(RuleError)
def rule_error_handler(_: Request, exc: RuleError) -> JSONResponse:
    return _error(exc.status_code, exc.code, exc.message)


@app.exception_handler(sqlite3.Error)
def storage_error_handler(_: Request, __: sqlite3.Error) -> JSONResponse:
    return _error(500, "STORAGE_ERROR", "저장소 처리에 실패했습니다.")


app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(suggest.router)
app.include_router(briefing.router)
app.include_router(weekplan.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
