"""Link scheduled tasks to assistant content messages.

Revision ID: 4f2a91c5d7e8
Revises: c7d2a9f41e03
Create Date: 2026-11-04 09:00:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "4f2a91c5d7e8"
down_revision: Union[str, Sequence[str], None] = "c7d2a9f41e03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("alter table public.scheduled_tasks add column content_message_id uuid")
    op.execute(
        "alter table public.scheduled_tasks add constraint scheduled_tasks_content_message_fk "
        "foreign key (content_message_id, conversation_id) "
        "references public.messages (id, conversation_id) on delete set null (content_message_id)"
    )
    op.execute(
        "create index idx_scheduled_tasks_content_message on public.scheduled_tasks (content_message_id) "
        "where content_message_id is not null"
    )


def downgrade() -> None:
    op.execute("drop index if exists public.idx_scheduled_tasks_content_message")
    op.execute(
        "alter table public.scheduled_tasks drop constraint if exists scheduled_tasks_content_message_fk"
    )
    op.execute("alter table public.scheduled_tasks drop column if exists content_message_id")
