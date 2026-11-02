"""Người dùng: profiles, user_settings, devices, notifications, notification_deliveries."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at, updated_at, uuid_pk


class Profile(Base):
    """Hồ sơ người dùng, 1:1 với auth.users (SĐT, mật khẩu, phiên đăng nhập nằm ở Supabase Auth)."""

    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("length(btrim(full_name)) > 0", name="profiles_full_name_chk"),
        CheckConstraint("status in ('active', 'suspended')", name="profiles_status_chk"),
        CheckConstraint("avatar_path is null or avatar_path like id::text || '/%'", name="profiles_avatar_chk"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), primary_key=True
    )
    full_name: Mapped[str] = mapped_column(String(150))
    avatar_path: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"))
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    settings: Mapped["UserSetting"] = relationship(back_populates="user", uselist=False, passive_deletes=True)
    devices: Mapped[list["Device"]] = relationship(back_populates="user", passive_deletes=True)
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", passive_deletes=True)
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", passive_deletes=True)
    social_accounts: Mapped[list["SocialAccount"]] = relationship(back_populates="user", passive_deletes=True)
    scheduled_tasks: Mapped[list["ScheduledTask"]] = relationship(back_populates="user", passive_deletes=True)


class UserSetting(Base):
    __tablename__ = "user_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="user_settings_user_id_key"),
        CheckConstraint("theme in ('light', 'dark', 'system')", name="user_settings_theme_chk"),
        CheckConstraint("jsonb_typeof(settings_json) = 'object'", name="user_settings_settings_chk"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    theme: Mapped[str] = mapped_column(String(20), server_default=text("'system'"))
    language: Mapped[str] = mapped_column(String(10), server_default=text("'vi'"))
    timezone: Mapped[str] = mapped_column(String(100), server_default=text("'Asia/Ho_Chi_Minh'"))
    notification_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    settings_json: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    user: Mapped[Profile] = relationship(back_populates="settings")


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="devices_id_user_key"),
        UniqueConstraint("user_id", "installation_id", name="devices_user_installation_key"),
        CheckConstraint("platform in ('ios', 'android')", name="devices_platform_chk"),
        Index("uq_devices_push_token", "push_token", unique=True, postgresql_where=text("push_token is not null")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    installation_id: Mapped[str] = mapped_column(String(100))
    device_name: Mapped[str | None] = mapped_column(String(150))
    platform: Mapped[str] = mapped_column(String(20))
    os_version: Mapped[str | None] = mapped_column(String(30))
    app_version: Mapped[str | None] = mapped_column(String(30))
    push_token: Mapped[str | None] = mapped_column(Text)
    push_token_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    user: Mapped[Profile] = relationship(back_populates="devices")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("category in ('chat', 'task', 'system')", name="notifications_category_chk"),
        CheckConstraint("jsonb_typeof(data) = 'object'", name="notifications_data_chk"),
        Index("idx_notifications_user_created", "user_id", text("created_at DESC")),
        Index("idx_notifications_user_unread", "user_id", postgresql_where=text("read_at is null")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(30), server_default=text("'system'"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()

    user: Mapped[Profile] = relationship(back_populates="notifications")
    deliveries: Mapped[list["NotificationDelivery"]] = relationship(back_populates="notification", passive_deletes=True)


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        CheckConstraint(
            "status in ('queued', 'sent', 'delivered', 'failed')", name="notification_deliveries_status_chk"
        ),
        Index("idx_deliveries_notification", "notification_id"),
        Index("idx_deliveries_device", "device_id"),
        Index(
            "idx_deliveries_pending_receipt",
            "sent_at",
            postgresql_where=text("status = 'sent' and expo_ticket_id is not null"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.id", ondelete="CASCADE")
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL")
    )
    push_token: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'queued'"))
    expo_ticket_id: Mapped[str | None] = mapped_column(String(100))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    notification: Mapped[Notification] = relationship(back_populates="deliveries")
    device: Mapped[Device | None] = relationship()
