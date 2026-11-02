import uuid

from sqlalchemy import Column, DateTime, FetchedValue, MetaData, Table, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column

# Đặt tên khóa giống cách Postgres tự đặt, để bảng mới tạo từ Python
# có tên constraint cùng kiểu với các bảng đã có.
NAMING_CONVENTION = {
    "pk": "%(table_name)s_pkey",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "uq": "%(table_name)s_%(column_0_N_name)s_key",
    "ix": "idx_%(table_name)s_%(column_0_N_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# auth.users do Supabase Auth quản lý. Khai báo ở đây chỉ để khóa ngoại
# trỏ tới được; Alembic không bao giờ tạo/sửa bảng này.
auth_users = Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    schema="auth",
)


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), default=uuid.uuid4)


def created_at():
    return mapped_column(DateTime(timezone=True), server_default=text("now()"))


def updated_at():
    # Trigger set_updated_at trong DB tự cập nhật khi UPDATE
    return mapped_column(DateTime(timezone=True), server_default=text("now()"), server_onupdate=FetchedValue())

