from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parent.parent


def migrate(revision: str = "head") -> None:
    """TASKFLOW_DB가 가리키는 DB에 Alembic revision을 적용한다. 테스트는 임시 DB에서만 쓴다."""
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), revision)


def downgrade(revision: str) -> None:
    command.downgrade(Config(str(BACKEND_DIR / "alembic.ini")), revision)
