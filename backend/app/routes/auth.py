import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response

from app import db
from app.auth import (
    COOKIE_NAME,
    SESSION_DAYS,
    create_session,
    delete_session,
    get_current_user,
    hash_password,
    verify_password,
    verify_unknown_account,
)
from app.rules import RuleError, check_password, clean_email
from app.schemas import LoginRequest, SignupRequest, User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=User, status_code=201)
def signup(body: SignupRequest) -> User:
    email = clean_email(body.email)
    check_password(body.password)
    password_hash = hash_password(body.password)
    created_at = datetime.now(timezone.utc).isoformat()
    conn = db.connect()
    try:
        try:
            cur = conn.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email, password_hash, created_at),
            )
        except sqlite3.IntegrityError:
            raise RuleError("EMAIL_TAKEN", "이미 가입된 이메일입니다.", 409) from None
        user_id = cur.lastrowid
        # 첫 가입자는 소유자가 없던 시절의 기존 카드를 넘겨받는다. (D-021)
        # 가입과 같은 트랜잭션이라 둘 중 하나만 반영되는 일이 없다.
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1:
            conn.execute("UPDATE tasks SET owner_id = ? WHERE owner_id IS NULL", (user_id,))
        conn.commit()
    finally:
        conn.close()
    return User(id=user_id, email=email)


def _invalid_credentials() -> RuleError:
    return RuleError("INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다.", 401)


@router.post("/login", response_model=User)
def login(body: LoginRequest, response: Response) -> User:
    # 형식 검사는 하지 않는다. 없는 계정과 틀린 비밀번호가 같은 응답이어야 한다.
    email = body.email.strip().lower()
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
        if row is None:
            verify_unknown_account(body.password)
            raise _invalid_credentials()
        if not verify_password(body.password, row["password_hash"]):
            raise _invalid_credentials()
        token = create_session(conn, row["id"])
    finally:
        conn.close()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return User(id=row["id"], email=row["email"])


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        conn = db.connect()
        try:
            delete_session(conn, token)
        finally:
            conn.close()
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")
    return response


@router.get("/me", response_model=User)
def me(user: User = Depends(get_current_user)) -> User:
    return user
