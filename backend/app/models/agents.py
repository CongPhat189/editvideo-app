"""GoClaw: goclaw_workspaces, agents, user_agent_access."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at, updated_at, uuid_pk


class GoclawWorkspace(Base):
    __tablename__ = "goclaw_workspaces"
    __table_args__ = (UniqueConstraint("name", name="goclaw_workspaces_name_key"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(150))
    base_url: Mapped[str] = mapped_column(Text)
    api_key_secret_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # id trong vault.secrets
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    agents: Mapped[list["Agent"]] = relationship(back_populates="workspace")


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "goclaw_agent_id", name="agents_workspace_goclaw_key"),
        CheckConstraint("visibility in ('public', 'restricted')", name="agents_visibility_chk"),
        Index("idx_agents_active_sort", "sort_order", "name", postgresql_where=text("is_active")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("goclaw_workspaces.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(150))
    goclaw_agent_id: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(20), server_default=text("'public'"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    workspace: Mapped[GoclawWorkspace] = relationship(back_populates="agents")


class UserAgentAccess(Base):
    """Cấp quyền dùng agent 'restricted' cho user (bảng N:M profiles <-> agents)."""

    __tablename__ = "user_agent_access"
    __table_args__ = (Index("idx_user_agent_access_agent", "agent_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agent: Mapped[Agent] = relationship()
