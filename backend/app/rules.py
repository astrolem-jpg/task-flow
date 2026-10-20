from enum import Enum


class Status(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


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


def parse_status(value: str) -> Status:
    """상태 값 규칙(D-004): 세 가지 외의 값은 거부한다."""
    try:
        return Status(value)
    except ValueError:
        raise RuleError("INVALID_STATUS", "올바르지 않은 상태입니다.") from None


def not_found() -> RuleError:
    return RuleError("NOT_FOUND", "카드를 찾을 수 없습니다.", 404)
