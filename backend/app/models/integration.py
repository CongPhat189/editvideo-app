from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class IntegrationConfig(Base):
    __tablename__ = "integration_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config_json: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_integration_user_provider"),
    )

    user: Mapped["User"] = relationship(back_populates="integrations")
