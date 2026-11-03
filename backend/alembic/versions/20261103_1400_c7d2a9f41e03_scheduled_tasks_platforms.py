"""scheduled_tasks.platforms: nền tảng cần đăng của lịch

Revision ID: c7d2a9f41e03
Revises: bc68e965bcae
Create Date: 2026-11-03 14:00:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c7d2a9f41e03"
down_revision: Union[str, Sequence[str], None] = "bc68e965bcae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("alter table public.scheduled_tasks add column platforms text[] not null default '{}'")


def downgrade() -> None:
    op.execute("alter table public.scheduled_tasks drop column platforms")
