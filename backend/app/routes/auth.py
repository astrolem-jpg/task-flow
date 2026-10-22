import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter

from app import db
from app.auth import hash_password
from app.rules import RuleError, check_password, clean_email
from app.schemas import SignupRequest, User

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
        conn.commit()
        user_id = cur.lastrowid
    finally:
        conn.close()
    return User(id=user_id, email=email)
