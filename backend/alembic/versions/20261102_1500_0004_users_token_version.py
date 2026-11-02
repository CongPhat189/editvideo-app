"""thêm users.token_version để đăng xuất thu hồi được token

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-02
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        alter table public.users
          add column token_version integer not null default 0,
          add constraint users_token_version_chk check (token_version >= 0)
    """)


def downgrade() -> None:
    op.execute("alter table public.users drop column token_version")
