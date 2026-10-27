import re
from datetime import date
from enum import Enum


class Status(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class Priority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class RuleError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


def clean_title(title: str) -> str:
    """제목 규칙(D-014, D-015): 비었거나 공백만 있으면 거부한다."""
    cleaned = title.strip()
    if not cleaned:
        raise RuleError("TITLE_REQUIRED", "제목을 입력해 주세요.")
    return cleaned


EMAIL_MAX = 254
PASSWORD_MIN = 8
PASSWORD_MAX = 128
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_email(email: str) -> str:
    """이메일 규칙(D-019): 앞뒤 공백을 지우고 소문자로 바꾸며, 형식이 틀리면 거부한다."""
    cleaned = email.strip().lower()
    if len(cleaned) > EMAIL_MAX or not _EMAIL_RE.match(cleaned):
        raise RuleError("INVALID_EMAIL", "이메일 형식이 올바르지 않습니다.")
    return cleaned


def check_password(password: str) -> str:
    """비밀번호 규칙(D-019): 8자 이상 128자 이하. 앞뒤 공백도 비밀번호의 일부로 둔다."""
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        raise RuleError(
            "INVALID_PASSWORD",
            f"비밀번호는 {PASSWORD_MIN}자 이상 {PASSWORD_MAX}자 이하여야 합니다.",
        )
    return password


def parse_status(value: str) -> Status:
    """상태 값 규칙(D-004): 세 가지 외의 값은 거부한다."""
    try:
        return Status(value)
    except ValueError:
        raise RuleError("INVALID_STATUS", "올바르지 않은 상태입니다.") from None


def parse_priority(value: object) -> Priority:
    """우선순위 규칙(R-010): LOW, NORMAL, HIGH와 정확히 같은 값만 허용한다. 지울 수 없어 null도 거부한다."""
    if isinstance(value, str):
        try:
            return Priority(value)
        except ValueError:
            pass
    raise RuleError(
        "INVALID_PRIORITY", "우선순위는 LOW, NORMAL, HIGH 중 하나여야 합니다.", 422
    )


_DUE_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def parse_due_date(value: object) -> str | None:
    """마감일 규칙(R-011): null(없음)이거나 실제 있는 날짜 YYYY-MM-DD. 지난 날짜도 허용한다."""
    if value is None:
        return None
    if isinstance(value, str) and _DUE_DATE_RE.fullmatch(value):
        try:
            date.fromisoformat(value)
            return value
        except ValueError:
            pass
    raise RuleError(
        "INVALID_DUE_DATE", "마감일은 YYYY-MM-DD 형식의 실제 날짜여야 합니다.", 422
    )


def not_found() -> RuleError:
    return RuleError("NOT_FOUND", "카드를 찾을 수 없습니다.", 404)
