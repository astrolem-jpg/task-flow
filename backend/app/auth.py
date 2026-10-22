import functools
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request

from app import db
from app.rules import RuleError
from app.schemas import User

COOKIE_NAME = "taskflow_session"
SESSION_DAYS = 7

_N, _R, _P = 2**14, 8, 1
_SALT_BYTES = 16
_DKLEN = 32


def hash_password(password: str) -> str:
    """scrypt 해시(D-019). 파라미터와 salt를 함께 저장한다: scrypt$n$r$p$salt$hash"""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN
    )
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """형식이 깨진 해시는 예외 없이 False."""
    try:
        scheme, n, r, p, salt_hex, hash_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = bytes.fromhex(hash_hex)
        digest = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


@functools.cache
def _dummy_hash() -> str:
    return hash_password("dummy-password-for-timing")


def verify_unknown_account(password: str) -> None:
    """없는 계정에도 해시 연산을 한 번 하여 응답 시간으로 계정 존재 여부가 드러나지 않게 한다."""
    verify_password(password, _dummy_hash())


def require_session_secret() -> str:
    secret = os.environ.get("SESSION_SECRET", "")
    if not secret:
        raise RuntimeError("SESSION_SECRET이 설정되어 있지 않습니다. backend/.env를 확인하세요.")
    return secret


def _token_hash(token: str) -> str:
    return hmac.new(
        require_session_secret().encode(), token.encode(), hashlib.sha256
    ).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_session(conn, user_id: int) -> str:
    """세션을 저장하고 쿠키에 담을 토큰 원문을 돌려준다. 원문은 DB에 남기지 않는다."""
    token = secrets.token_urlsafe(32)
    expires_at = (_now() + timedelta(days=SESSION_DAYS)).isoformat()
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_token_hash(token), user_id, expires_at),
    )
    conn.commit()
    return token


def delete_session(conn, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
    conn.commit()


def get_current_user(request: Request) -> User:
    """쿠키의 세션으로 로그인한 사용자를 찾는다. 없거나 만료되었으면 401."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise unauthorized()
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT u.id, u.email, s.expires_at FROM sessions s "
            "JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
            (_token_hash(token),),
        ).fetchone()
        if row is None:
            raise unauthorized()
        if datetime.fromisoformat(row["expires_at"]) <= _now():
            delete_session(conn, token)
            raise unauthorized()
    finally:
        conn.close()
    return User(id=row["id"], email=row["email"])


def unauthorized() -> RuleError:
    return RuleError("UNAUTHORIZED", "로그인이 필요합니다.", 401)
