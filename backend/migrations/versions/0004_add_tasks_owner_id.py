"""add tasks owner_id

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-22 17:29:49.702668

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """tasks.owner_id (D-018, D-021). 기존 카드는 NULL로 남고 첫 가입 때 첫 가입자에게 귀속된다.

    SQLite는 ALTER로 제약을 추가할 수 없어 DB 수준의 외래 키는 두지 않는다.
    소유자 값은 API가 항상 채우고, 조회와 변경은 모두 owner_id로 걸러진다.
    """
    op.add_column("tasks", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_index("ix_tasks_owner_id", "tasks", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_owner_id", table_name="tasks")
    with op.batch_alter_table("tasks", table_kwargs={"sqlite_autoincrement": True}) as batch:
        batch.drop_column("owner_id")
