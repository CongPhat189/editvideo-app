"""Lịch hẹn & tích hợp: social_accounts, scheduled_tasks, scheduled_task_runs, scheduled_task_logs, outbox_events."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.models.base import Base, created_at, updated_at, uuid_pk
from app.models.agents import Agent
from app.models.chat import Conversation
from app.models.users import Profile


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="social_accounts_id_user_key"),
        UniqueConstraint("user_id", "platform", "external_account_id", name="social_accounts_external_key"),
        CheckConstraint(
            "platform in ('facebook', 'instagram', 'threads', 'tiktok', 'youtube', 'x', 'linkedin', 'zalo')",
            name="social_accounts_platform_chk",
        ),
        CheckConstraint("status in ('active', 'expired', 'revoked', 'error')", name="social_accounts_status_chk"),
        Index(
            "idx_social_accounts_expiring",
            "token_expires_at",
            postgresql_where=text("status = 'active' and token_expires_at is not null"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(String(30))
    external_account_id: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    access_token_secret_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))   # vault.secrets.id
    refresh_token_secret_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # vault.secrets.id
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    user: Mapped[Profile] = relationship(back_populates="social_accounts")


class ScheduledTask(Base):
    """ĐỊNH NGHĨA lịch hẹn. Đăng một bài lên nhiều nền tảng = nhiều task cùng group_id."""

    __tablename__ = "scheduled_tasks"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="scheduled_tasks_id_user_key"),
        ForeignKeyConstraint(
            ["conversation_id", "user_id"],
            ["conversations.id", "conversations.user_id"],
            name="scheduled_tasks_conversation_owner_fk",
            ondelete="SET NULL (conversation_id)",
        ),
        ForeignKeyConstraint(
            ["social_account_id", "user_id"],
            ["social_accounts.id", "social_accounts.user_id"],
            name="scheduled_tasks_social_owner_fk",
            ondelete="SET NULL (social_account_id)",
        ),
        CheckConstraint(
            "task_type in ('send_message', 'execute_agent', 'execute_workflow', 'publish_post')",
            name="scheduled_tasks_type_chk",
        ),
        CheckConstraint(
            "status in ('active', 'paused', 'finished', 'cancelled')", name="scheduled_tasks_status_chk"
        ),
        CheckConstraint("max_attempts between 1 and 10", name="scheduled_tasks_attempts_chk"),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="scheduled_tasks_payload_chk"),
        CheckConstraint("ends_at is null or ends_at >= scheduled_at", name="scheduled_tasks_ends_chk"),
        Index(
            "idx_scheduled_tasks_due",
            "next_run_at",
            postgresql_where=text("status = 'active' and next_run_at is not null"),
        ),
        Index("idx_scheduled_tasks_user", "user_id", text("scheduled_at DESC")),
        Index("idx_scheduled_tasks_group", "group_id", postgresql_where=text("group_id is not null")),
        Index(
            "idx_scheduled_tasks_conversation", "conversation_id", postgresql_where=text("conversation_id is not null")
        ),
        Index(
            "idx_scheduled_tasks_social", "social_account_id", postgresql_where=text("social_account_id is not null")
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    social_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    task_name: Mapped[str] = mapped_column(String(255))
    task_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # lần chạy đầu tiên
    timezone: Mapped[str] = mapped_column(String(100), server_default=text("'Asia/Ho_Chi_Minh'"))
    recurrence_rule: Mapped[str | None] = mapped_column(Text)  # RRULE (RFC 5545), NULL = chạy một lần
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    max_attempts: Mapped[int] = mapped_column(Integer, server_default=text("3"))
    run_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    user: Mapped[Profile] = relationship(back_populates="scheduled_tasks")
    agent: Mapped[Agent | None] = relationship()
    conversation: Mapped[Conversation | None] = relationship(
        primaryjoin=lambda: and_(Conversation.id == foreign(ScheduledTask.conversation_id),
                                 Conversation.user_id == foreign(ScheduledTask.user_id)),
        viewonly=True,
    )
    social_account: Mapped[SocialAccount | None] = relationship(
        primaryjoin=lambda: and_(SocialAccount.id == foreign(ScheduledTask.social_account_id),
                                 SocialAccount.user_id == foreign(ScheduledTask.user_id)),
        viewonly=True,
    )
    runs: Mapped[list["ScheduledTaskRun"]] = relationship(
        primaryjoin=lambda: and_(ScheduledTask.id == foreign(ScheduledTaskRun.task_id),
                                 ScheduledTask.user_id == foreign(ScheduledTaskRun.user_id)),
        order_by=lambda: ScheduledTaskRun.scheduled_for,
        viewonly=True,
    )


class ScheduledTaskRun(Base):
    """TỪNG LẦN CHẠY của một task (worker claim bằng claim_due_task_runs)."""

    __tablename__ = "scheduled_task_runs"
    __table_args__ = (
        UniqueConstraint("task_id", "scheduled_for", name="scheduled_task_runs_occurrence_key"),
        UniqueConstraint("idempotency_key", name="scheduled_task_runs_idempotency_key"),
        ForeignKeyConstraint(
            ["task_id", "user_id"],
            ["scheduled_tasks.id", "scheduled_tasks.user_id"],
            name="scheduled_task_runs_task_owner_fk",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "status in ('scheduled', 'processing', 'completed', 'failed', 'cancelled', 'retrying')",
            name="scheduled_task_runs_status_chk",
        ),
        CheckConstraint("attempts >= 0 and max_attempts >= 1", name="scheduled_task_runs_attempts_chk"),
        CheckConstraint("status <> 'retrying' or next_retry_at is not null", name="scheduled_task_runs_retry_chk"),
        Index("idx_task_runs_due", "scheduled_for", postgresql_where=text("status = 'scheduled'")),
        Index("idx_task_runs_retry", "next_retry_at", postgresql_where=text("status = 'retrying'")),
        Index("idx_task_runs_processing", "locked_at", postgresql_where=text("status = 'processing'")),
        Index("idx_task_runs_user", "user_id", text("scheduled_for DESC")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'scheduled'"))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, server_default=text("3"))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(100))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    external_ref: Mapped[str | None] = mapped_column(String(255))  # post id phía ngoài -> có rồi thì KHÔNG đăng lại
    result: Mapped[dict | None] = mapped_column(JSONB)
    last_error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    logs: Mapped[list["ScheduledTaskLog"]] = relationship(back_populates="run", passive_deletes=True)


class ScheduledTaskLog(Base):
    __tablename__ = "scheduled_task_logs"
    __table_args__ = (
        UniqueConstraint("run_id", "attempt_number", name="scheduled_task_logs_attempt_key"),
        CheckConstraint("attempt_number >= 1", name="scheduled_task_logs_attempt_chk"),
        CheckConstraint(
            "status in ('processing', 'completed', 'failed', 'cancelled')", name="scheduled_task_logs_status_chk"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scheduled_task_runs.id", ondelete="CASCADE")
    )
    attempt_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    request_payload: Mapped[dict | None] = mapped_column(JSONB)  # KHÔNG ghi token/API key vào đây
    response_payload: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()

    run: Mapped[ScheduledTaskRun] = relationship(back_populates="logs")


class OutboxEvent(Base):
    """Hàng đợi việc gọi ra ngoài (GoClaw, push...). Không có khóa ngoại: trỏ qua aggregate_type + aggregate_id."""

    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint("status in ('pending', 'processing', 'done', 'failed')", name="outbox_events_status_chk"),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="outbox_events_payload_chk"),
        Index("idx_outbox_pending", "available_at", postgresql_where=text("status = 'pending'")),
        Index("idx_outbox_aggregate", "aggregate_type", "aggregate_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    event_type: Mapped[str] = mapped_column(String(100))
    aggregate_type: Mapped[str] = mapped_column(String(50))
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'pending'"))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    locked_by: Mapped[str | None] = mapped_column(String(100))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
