"""create users

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-22 17:16:35.124692

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """users 테이블 (D-019). 비밀번호는 해시만 저장한다."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sqlite_autoincrement=True,
    )


def downgrade() -> None:
    op.drop_table("users")
