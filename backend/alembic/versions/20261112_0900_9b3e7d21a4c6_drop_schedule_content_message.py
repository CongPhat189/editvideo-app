"""Bỏ cột scheduled_tasks.content_message_id và các lịch "xác nhận" chạy ngầm.

Lịch giờ chỉ lưu nguyên văn content trong payload. Dùng IF EXISTS vì cột đã được xóa tay trên Supabase.

Revision ID: 9b3e7d21a4c6
Revises: 4f2a91c5d7e8
Create Date: 2026-11-12 09:00:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "9b3e7d21a4c6"
down_revision: Union[str, Sequence[str], None] = "4f2a91c5d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("drop index if exists public.idx_scheduled_tasks_content_message")
    op.execute("alter table public.scheduled_tasks drop constraint if exists scheduled_tasks_content_message_fk")
    op.execute("alter table public.scheduled_tasks drop column if exists content_message_id")
    # Tin xác nhận ngầm của bản cũ (payload có "kind"): không còn dùng
    op.execute("delete from public.scheduled_tasks where payload ? 'kind'")


def downgrade() -> None:
    op.execute("alter table public.scheduled_tasks add column if not exists content_message_id uuid")
    op.execute(
        "alter table public.scheduled_tasks add constraint scheduled_tasks_content_message_fk "
        "foreign key (content_message_id, conversation_id) "
        "references public.messages (id, conversation_id) on delete set null (content_message_id)"
    )
    op.execute(
        "create index idx_scheduled_tasks_content_message on public.scheduled_tasks (content_message_id) "
        "where content_message_id is not null"
    )
