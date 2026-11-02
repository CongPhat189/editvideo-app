"""baseline: schema v2.1 (16 bảng, RLS, storage, functions)

Chạy 3 file SQL trong supabase/migrations - đúng những gì đang có trên Supabase.
Nếu database đã có schema này (đã push bằng Supabase CLI) thì bỏ qua, chỉ ghi
nhận phiên bản. Từ migration sau trở đi, mọi thay đổi đều sinh từ Python models.

Revision ID: 0001
Revises:
Create Date: 2026-11-02
"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SQL_DIR = Path(__file__).resolve().parents[3] / "supabase" / "migrations"
SQL_FILES = [
    "20261102000100_schema.sql",
    "20261102000200_security.sql",
    "20261102000300_storage.sql",
]


def upgrade() -> None:
    bind = op.get_bind()
    # Bảng ghi phiên bản của Alembic nằm trong public -> không cho Data API đụng vào
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON public.alembic_version FROM anon, authenticated")

    if bind.exec_driver_sql("select to_regclass('public.profiles') is not null").scalar():
        print("Schema v2.1 đã có sẵn trong database -> chỉ ghi nhận baseline.")
        return
    # Chạy nguyên file SQL qua driver (nhiều câu lệnh, có $$ ... $$)
    cursor = bind.connection.dbapi_connection.cursor()
    for name in SQL_FILES:
        cursor.execute((SQL_DIR / name).read_text(encoding="utf-8"))
        print(f"applied {name}")


def downgrade() -> None:
    raise NotImplementedError("Không hạ được baseline. Muốn làm lại từ đầu thì reset database.")
