from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.mobile import Content, Title


PLATFORMS = ("Facebook", "YouTube", "TikTok", "Instagram", "Website")


class SchedulePayload(BaseModel):
    user_id: int | None = None
    title: str | None = None
    description: str | None = None
    scheduled_at: str | None = None
    platform: str = "facebook"
    payload: dict | None = None


class ScheduleCreate(BaseModel):
    conversation_id: uuid.UUID = Field(description="Cuộc trò chuyện đang mở")
    content_message_id: uuid.UUID | None = Field(
        default=None,
        description="ID tin nhắn assistant chứa nội dung cần gắn với lịch; phải thuộc conversation_id này",
    )
    scheduled_at: datetime = Field(
        description="Ngày giờ đặt lịch: 05/11/2026 20:00 hoặc 2026-11-05T20:00, có thể chỉ có ngày. "
        "Không kèm múi giờ thì hiểu theo timezone"
    )
    # Có content: chỉ lưu khi đặt lịch; đến giờ worker mới gửi lệnh đăng cho agent.
    content: Content | None = None
    platforms: list[str] = Field(default_factory=list, max_length=len(PLATFORMS), description="Nền tảng cần đăng")
    timezone: str = Field(default="Asia/Ho_Chi_Minh", max_length=100)
    task_name: Title | None = None

    @field_validator("platforms")
    @classmethod
    def _normalize_platforms(cls, value: list[str]) -> list[str]:
        """Không phân biệt hoa thường, bỏ trùng, giữ thứ tự người dùng chọn."""
        names = {name.lower(): name for name in PLATFORMS}
        result: list[str] = []
        for item in value:
            name = names.get(item.strip().lower())
            if name is None:
                raise ValueError(f"nền tảng không hợp lệ, chỉ nhận: {', '.join(PLATFORMS)}")
            if name not in result:
                result.append(name)
        return result

    @field_validator("scheduled_at", mode="before")
    @classmethod
    def _accept_day_month_year(cls, value):
        if isinstance(value, str) and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}( \d{1,2}:\d{2})?", value.strip()):
            pattern = "%d/%m/%Y %H:%M" if " " in value.strip() else "%d/%m/%Y"
            try:
                return datetime.strptime(value.strip(), pattern)
            except ValueError:
                raise ValueError("ngày giờ không hợp lệ") from None
        return value

    @model_validator(mode="after")
    def _check_schedule(self) -> ScheduleCreate:
        try:
            zone = ZoneInfo(self.timezone)
        except (KeyError, ValueError, OSError):  # ZoneInfoNotFoundError là KeyError
            raise ValueError("timezone không hợp lệ") from None
        if self.scheduled_at.tzinfo is None:
            self.scheduled_at = self.scheduled_at.replace(tzinfo=zone)
        local = self.scheduled_at.astimezone(zone)
        if self.content is None and local.time() == time.min:  # chỉ chọn ngày: được chọn hôm nay
            if local.date() < datetime.now(zone).date():
                raise ValueError("Ngày đặt lịch không được ở quá khứ")
        elif self.scheduled_at <= datetime.now(UTC):
            raise ValueError("scheduled_at phải ở tương lai")
        return self


class ScheduleOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID | None
    content_message_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None
    task_name: str
    content: str | None
    platforms: list[str]
    scheduled_at: datetime
    timezone: str
    status: str
    attempts: int
    last_error: str | None
    executed_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    @classmethod
    def from_task(cls, task) -> ScheduleOut:
        return cls(
            id=task.id,
            conversation_id=task.conversation_id,
            content_message_id=task.content_message_id,
            agent_id=task.agent_id,
            task_name=task.task_name,
            content=task.payload.get("content"),
            platforms=task.platforms,
            scheduled_at=task.scheduled_at.astimezone(ZoneInfo(task.timezone)),
            timezone=task.timezone,
            status=task.status,
            attempts=task.attempts,
            last_error=task.last_error,
            executed_at=task.executed_at,
            completed_at=task.completed_at,
            created_at=task.created_at,
        )
