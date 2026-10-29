"""create subtasks

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """subtasks 테이블 (R-015, D-028). 카드에 딸린 세부 항목이다.

    DB의 외래 키 강제에 기대지 않는다. 카드를 지울 때 API가 같은 트랜잭션에서 세부 항목도 지우고,
    소유자는 부모 카드의 owner_id로 확인한다. id는 지운 뒤에도 다시 쓰지 않는다(tasks와 같다).
    기존 카드는 세부 항목이 없는 채로 그대로 남는다.
    """
    op.create_table(
        "subtasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_subtasks_task_id", "subtasks", ["task_id"])


def downgrade() -> None:
    """되돌리기는 만들지 않는다. 적용 전에 만든 백업 파일로 복원한다. (D-024, D-028)"""
    raise NotImplementedError("0006은 되돌리지 않는다. 적용 전 백업 파일로 복원하세요.")
