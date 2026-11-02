"""Chat: conversations, messages, message_attachments."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    and_,
    literal_column,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.models.base import Base, created_at, updated_at, uuid_pk
from app.models.agents import Agent
from app.models.users import Profile


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="conversations_id_user_key"),
        CheckConstraint("title_source in ('auto', 'user')", name="conversations_title_src_chk"),
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
        Index("idx_conversations_purge", "deleted_at", postgresql_where=text("deleted_at is not null")),
        Index(
            "uq_conversations_agent_session",
            "agent_id",
            "goclaw_session_id",
            unique=True,
            postgresql_where=text("goclaw_session_id is not null"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"))
    title: Mapped[str | None] = mapped_column(String(255))
    title_source: Mapped[str] = mapped_column(String(10), server_default=text("'auto'"))
    goclaw_session_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    message_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[Profile] = relationship(back_populates="conversations")
    agent: Mapped[Agent] = relationship()
    messages: Mapped[list["Message"]] = relationship(
        primaryjoin=lambda: and_(Conversation.id == foreign(Message.conversation_id),
                                 Conversation.user_id == foreign(Message.user_id)),
        order_by=lambda: Message.seq,
        viewonly=True,
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("seq", name="messages_seq_key"),
        UniqueConstraint("id", "conversation_id", name="messages_id_conversation_key"),
        UniqueConstraint("id", "user_id", name="messages_id_user_key"),
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
        CheckConstraint(
            "coalesce(input_tokens, 0) >= 0 and coalesce(output_tokens, 0) >= 0 and coalesce(cost_usd, 0) >= 0",
            name="messages_usage_chk",
        ),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="messages_metadata_chk"),
        Index("idx_messages_conversation_seq", "conversation_id", "seq"),
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
            "idx_messages_goclaw_message",
            "conversation_id",
            "goclaw_message_id",
            postgresql_where=text("goclaw_message_id is not null"),
        ),
        Index(
            "idx_messages_reply_to", "reply_to_message_id", postgresql_where=text("reply_to_message_id is not null")
        ),
        Index(
            "idx_messages_user_favorited",
            "user_id",
            text("favorited_at DESC"),
            postgresql_where=text("favorited_at is not null"),
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
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True))  # thứ tự tuyệt đối, dùng cho cursor
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
    model: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    # "metadata" là tên dành riêng của SQLAlchemy nên thuộc tính Python đặt là meta
    meta: Mapped[dict] = mapped_column("metadata", JSONB, server_default=text("'{}'::jsonb"))
    favorited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    conversation: Mapped[Conversation] = relationship(
        primaryjoin=lambda: and_(Conversation.id == foreign(Message.conversation_id),
                                 Conversation.user_id == foreign(Message.user_id)),
        viewonly=True,
    )
    attachments: Mapped[list["MessageAttachment"]] = relationship(
        primaryjoin=lambda: and_(Message.id == foreign(MessageAttachment.message_id),
                                 Message.user_id == foreign(MessageAttachment.user_id)),
        viewonly=True,
    )


class MessageAttachment(Base):
    """File đính kèm. Có thể tồn tại trước khi gửi tin (message_id NULL, status pending_upload/uploaded)."""

    __tablename__ = "message_attachments"
    __table_args__ = (
        UniqueConstraint("file_path", name="message_attachments_file_path_key"),
        ForeignKeyConstraint(
            ["message_id", "user_id"],
            ["messages.id", "messages.user_id"],
            name="message_attachments_message_fk",
            ondelete="CASCADE",
        ),
        CheckConstraint("file_path like user_id::text || '/%'", name="message_attachments_path_chk"),
        CheckConstraint("file_size >= 0", name="message_attachments_size_chk"),
        CheckConstraint(
            "status in ('pending_upload', 'uploaded', 'attached')", name="message_attachments_status_chk"
        ),
        CheckConstraint("(status = 'attached') = (message_id is not null)", name="message_attachments_attached_chk"),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="message_attachments_metadata_chk"),
        Index("idx_attachments_message", "message_id", postgresql_where=text("message_id is not null")),
        Index("idx_attachments_orphans", "created_at", postgresql_where=text("status <> 'attached'")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'pending_upload'"))
    meta: Mapped[dict] = mapped_column("metadata", JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at()
    attached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
