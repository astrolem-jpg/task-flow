"""add tasks priority and due_date

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """tasks.priority, tasks.due_date (R-010, R-011).

    기존 카드는 priority NORMAL, due_date NULL(마감일 없음)이 된다.
    due_date는 날짜만(YYYY-MM-DD) 담는 텍스트다. 값 검증은 API가 한다. (D-004)
    """
    op.add_column(
        "tasks",
        sa.Column("priority", sa.Text(), nullable=False, server_default="NORMAL"),
    )
    op.add_column("tasks", sa.Column("due_date", sa.Text(), nullable=True))


def downgrade() -> None:
    """되돌리기는 만들지 않는다. 적용 전에 만든 백업 파일로 복원한다. (D-024)"""
    raise NotImplementedError("0005는 되돌리지 않는다. 적용 전 백업 파일로 복원하세요.")
