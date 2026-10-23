"""baseline tasks

Revision ID: 0001
Revises: 
Create Date: 2026-10-22 17:16:34.427321

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """tasks 테이블의 최초 구조. 이미 있는 DB(M1에서 만든 파일)에서는 건드리지 않는다."""
    if "tasks" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Text(), nullable=False, server_default="TODO"),
        sqlite_autoincrement=True,
    )


def downgrade() -> None:
    """카드 데이터를 지우지 않기 위해 baseline은 되돌리지 않는다."""
    pass
