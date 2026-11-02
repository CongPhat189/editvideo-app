"""Toàn bộ bảng của backend, gom trong một file.

Base: database Supabase (Postgres), do Alembic quản lý. Thêm hoặc sửa bảng thì sửa class ở đây, rồi chạy
`uv run python manage.py make "mô tả"` và `uv run python manage.py migrate`.

LocalBase: bảng demo của các API /api/*, nằm trong SQLite riêng (LOCAL_DATABASE_URL), do app/db/init_db.py
tạo khi khởi động. Alembic không đụng tới các bảng này.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    and_,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    FetchedValue,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    literal_column,
    MetaData,
    String,
    Text,
    text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    foreign,
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base as LocalBase


# ==================== Supabase - Nền tảng ====================

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


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), default=uuid.uuid4)


def created_at():
    return mapped_column(DateTime(timezone=True), server_default=text("now()"))


def updated_at():
    # Trigger set_updated_at trong DB tự cập nhật khi UPDATE
    return mapped_column(DateTime(timezone=True), server_default=text("now()"), server_onupdate=FetchedValue())


# ==================== Supabase - Người dùng ====================

class AppUser(Base):
    """Tài khoản app. Tên class khác `User` vì `User` là bảng demo trong SQLite ở cuối file."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("phone", name="users_phone_key"),
        CheckConstraint("length(btrim(full_name)) > 0", name="users_full_name_chk"),
        CheckConstraint("phone ~ '^\\+[1-9][0-9]{7,14}$'", name="users_phone_chk"),
        CheckConstraint("status in ('active', 'suspended', 'deleted')", name="users_status_chk"),
        CheckConstraint("(status = 'deleted') = (deleted_at is not null)", name="users_deleted_chk"),
        CheckConstraint("token_version >= 0", name="users_token_version_chk"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(20))  # E.164, vd +84912345678
    password_hash: Mapped[str] = mapped_column(Text)  # Argon2id
    token_version: Mapped[int] = mapped_column(Integer, server_default=text("0"))  # đăng xuất thì tăng
    avatar_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    settings: Mapped["UserSetting"] = relationship(back_populates="user", uselist=False, passive_deletes=True)
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", passive_deletes=True)
    scheduled_tasks: Mapped[list["ScheduledTask"]] = relationship(back_populates="user", passive_deletes=True)


class UserSetting(Base):
    __tablename__ = "user_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="user_settings_user_id_key"),
        CheckConstraint("theme in ('light', 'dark', 'system')", name="user_settings_theme_chk"),
        CheckConstraint("jsonb_typeof(settings_json) = 'object'", name="user_settings_settings_chk"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    theme: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    language: Mapped[str] = mapped_column(String(10), server_default=text("'vi'"))
    timezone: Mapped[str] = mapped_column(String(100), server_default=text("'Asia/Ho_Chi_Minh'"))
    notification_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    settings_json: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    user: Mapped[AppUser] = relationship(back_populates="settings")


# ==================== Supabase - GoClaw ====================

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(150))
    api_key: Mapped[str | None] = mapped_column(Text)  # API key đã mã hóa (app/core/crypto.py), không lưu bản gốc
    agent_key: Mapped[str | None] = mapped_column(Text)  # agent_key đã mã hóa (app/core/crypto.py), không lưu bản gốc
    domain: Mapped[str] = mapped_column(String(255))  # vd https://goclaw.abc.com
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


# ==================== Supabase - Chat ====================

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="conversations_id_user_key"),
        UniqueConstraint("goclaw_session_id", name="conversations_goclaw_session_id_key"),
        CheckConstraint("status in ('active', 'archived', 'deleted')", name="conversations_status_chk"),
        CheckConstraint("message_count >= 0", name="conversations_msg_count_chk"),
        CheckConstraint("status <> 'archived' or archived_at is not null", name="conversations_archived_chk"),
        CheckConstraint("(status = 'deleted') = (deleted_at is not null)", name="conversations_deleted_chk"),
        # Danh sách chat: ghim lên đầu, rồi theo hoạt động gần nhất
        Index(
            "idx_conversations_user_list",
            "user_id",
            text("pinned_at DESC NULLS LAST"),
            text("COALESCE(last_message_at, created_at) DESC"),
            "id",
            postgresql_where=text("deleted_at is null"),
        ),
        Index("idx_conversations_user_status", "user_id", "status"),
        Index("idx_conversations_agent", "agent_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"))
    title: Mapped[str | None] = mapped_column(String(255))
    goclaw_session_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    message_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[AppUser] = relationship(back_populates="conversations")
    agent: Mapped[Agent] = relationship()
    messages: Mapped[list["Message"]] = relationship(
        primaryjoin=lambda: and_(Conversation.id == foreign(Message.conversation_id),
                                 Conversation.user_id == foreign(Message.user_id)),
        order_by=lambda: (Message.created_at, Message.id),
        viewonly=True,
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("id", "conversation_id", name="messages_id_conversation_key"),
        # message.user_id BẮT BUỘC trùng chủ sở hữu conversation
        ForeignKeyConstraint(
            ["conversation_id", "user_id"],
            ["conversations.id", "conversations.user_id"],
            name="messages_conversation_owner_fk",
            ondelete="CASCADE",
        ),
        # chỉ reply tin trong CÙNG conversation
        ForeignKeyConstraint(
            ["reply_to_message_id", "conversation_id"],
            ["messages.id", "messages.conversation_id"],
            name="messages_reply_to_fk",
            ondelete="SET NULL (reply_to_message_id)",
        ),
        CheckConstraint("role in ('user', 'assistant', 'system', 'tool')", name="messages_role_chk"),
        CheckConstraint(
            "content_type in ('text', 'image', 'file', 'audio', 'video')", name="messages_content_type_chk"
        ),
        CheckConstraint(
            "status in ('pending', 'processing', 'completed', 'failed', 'cancelled')", name="messages_status_chk"
        ),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="messages_metadata_chk"),
        # Phân trang: WHERE conversation_id = $1 AND (created_at, id) < ($2, $3) ORDER BY created_at DESC, id DESC
        Index("idx_messages_conversation_created", "conversation_id", text("created_at DESC"), text("id DESC")),
        Index("idx_messages_user_created", "user_id", text("created_at DESC")),
        Index(
            "idx_messages_idempotency",
            "user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key is not null"),
        ),
        # Mỗi conversation chỉ một câu trả lời AI đang chạy
        Index(
            "uq_messages_one_inflight_reply",
            "conversation_id",
            unique=True,
            postgresql_where=text("role = 'assistant' and status in ('pending', 'processing')"),
        ),
        Index(
            "idx_messages_reply_to", "reply_to_message_id", postgresql_where=text("reply_to_message_id is not null")
        ),
        # Tìm kiếm không dấu (gin trigram trên f_unaccent(content))
        Index(
            "idx_messages_content_search",
            literal_column("f_unaccent(content)").label("content_unaccent"),
            postgresql_using="gin",
            postgresql_ops={"content_unaccent": "gin_trgm_ops"},  # schema extensions nằm sẵn trong search_path
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(30), server_default=text("'text'"))
    goclaw_message_id: Mapped[str | None] = mapped_column(String(255))
    reply_to_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'pending'"))
    idempotency_key: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    # "metadata" là tên dành riêng của SQLAlchemy nên thuộc tính Python đặt là meta. Chứa tokens, model, tools.
    meta: Mapped[dict] = mapped_column("metadata", JSONB, server_default=text("'{}'::jsonb"))
    favorited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # clock_timestamp, không phải now(): now() giống hệt nhau trong một transaction nên 2 tin sẽ không có thứ tự
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("clock_timestamp()"))
    updated_at: Mapped[datetime] = updated_at()

    conversation: Mapped[Conversation] = relationship(
        primaryjoin=lambda: and_(Conversation.id == foreign(Message.conversation_id),
                                 Conversation.user_id == foreign(Message.user_id)),
        viewonly=True,
    )
    attachments: Mapped[list["MessageAttachment"]] = relationship(back_populates="message", passive_deletes=True)


class MessageAttachment(Base):
    __tablename__ = "message_attachments"
    __table_args__ = (
        UniqueConstraint("file_path", name="message_attachments_file_path_key"),
        CheckConstraint("file_size >= 0", name="message_attachments_size_chk"),
        Index("idx_attachments_message", "message_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(Text)
    file_url: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = created_at()

    message: Mapped[Message] = relationship(back_populates="attachments")


# ==================== Supabase - Lịch hẹn ====================

class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["conversation_id", "user_id"],
            ["conversations.id", "conversations.user_id"],
            name="scheduled_tasks_conversation_owner_fk",
            ondelete="SET NULL (conversation_id)",
        ),
        CheckConstraint(
            "task_type in ('send_message', 'execute_agent', 'execute_workflow', 'publish_post')",
            name="scheduled_tasks_type_chk",
        ),
        CheckConstraint(
            "status in ('scheduled', 'processing', 'completed', 'failed', 'cancelled', 'retrying')",
            name="scheduled_tasks_status_chk",
        ),
        CheckConstraint("attempts >= 0", name="scheduled_tasks_attempts_chk"),
        CheckConstraint("max_attempts between 1 and 10", name="scheduled_tasks_max_attempts_chk"),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="scheduled_tasks_payload_chk"),
        CheckConstraint("status <> 'retrying' or next_retry_at is not null", name="scheduled_tasks_retry_chk"),
        Index("idx_scheduled_tasks_due", "scheduled_at", postgresql_where=text("status = 'scheduled'")),
        Index("idx_scheduled_tasks_retry", "next_retry_at", postgresql_where=text("status = 'retrying'")),
        Index("idx_scheduled_tasks_processing", "locked_at", postgresql_where=text("status = 'processing'")),
        Index("idx_scheduled_tasks_user", "user_id", text("scheduled_at DESC")),
        Index(
            "idx_scheduled_tasks_conversation", "conversation_id", postgresql_where=text("conversation_id is not null")
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    task_name: Mapped[str] = mapped_column(String(255))
    task_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(100), server_default=text("'Asia/Ho_Chi_Minh'"))
    recurrence_rule: Mapped[str | None] = mapped_column(Text)  # RRULE (RFC 5545), NULL = chạy một lần
    status: Mapped[str] = mapped_column(String(20), server_default=text("'scheduled'"))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, server_default=text("3"))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    locked_by: Mapped[str | None] = mapped_column(String(100))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    user: Mapped[AppUser] = relationship(back_populates="scheduled_tasks")
    agent: Mapped[Agent | None] = relationship()
    conversation: Mapped[Conversation | None] = relationship(
        primaryjoin=lambda: and_(Conversation.id == foreign(ScheduledTask.conversation_id),
                                 Conversation.user_id == foreign(ScheduledTask.user_id)),
        viewonly=True,
    )
    logs: Mapped[list["ScheduledTaskLog"]] = relationship(back_populates="task", passive_deletes=True)


class ScheduledTaskLog(Base):
    __tablename__ = "scheduled_task_logs"
    __table_args__ = (
        UniqueConstraint("task_id", "attempt_number", name="scheduled_task_logs_attempt_key"),
        CheckConstraint("attempt_number >= 1", name="scheduled_task_logs_attempt_chk"),
        CheckConstraint(
            "status in ('processing', 'completed', 'failed', 'cancelled')", name="scheduled_task_logs_status_chk"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scheduled_tasks.id", ondelete="CASCADE"))
    attempt_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    request_payload: Mapped[dict | None] = mapped_column(JSONB)  # KHÔNG ghi token/API key vào đây
    response_payload: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()

    task: Mapped[ScheduledTask] = relationship(back_populates="logs")
__all__ = [
    "Base",
    "LocalBase",
    "AppUser",
    "UserSetting",
    "Agent",
    "Conversation",
    "Message",
    "MessageAttachment",
    "ScheduledTask",
    "ScheduledTaskLog",
]
