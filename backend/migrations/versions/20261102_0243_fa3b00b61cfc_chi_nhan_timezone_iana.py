"""chi nhan timezone IANA

Trước đây trigger validate_timezone nhận cả "UTC+7", "+07", "ICT"... (Postgres hiểu "UTC+7"
theo kiểu POSIX là UTC-7, ngược dấu). Giờ chỉ nhận đúng tên IANA, vd "Asia/Ho_Chi_Minh".

Revision ID: fa3b00b61cfc
Revises: 0001
Create Date: 2026-11-02 02:43:47.198173
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'fa3b00b61cfc'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
create or replace function public.validate_timezone()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.timezone !~ '^(posix|right)/'
     and exists (select 1 from pg_catalog.pg_timezone_names where name = new.timezone) then
    return new;
  end if;
  raise exception 'invalid time zone "%": dùng tên IANA, vd Asia/Ho_Chi_Minh', new.timezone
    using errcode = '22023';
end;
$$;
""")


def downgrade() -> None:
    op.execute("""
create or replace function public.validate_timezone()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  perform now() at time zone new.timezone;
  return new;
end;
$$;
""")
