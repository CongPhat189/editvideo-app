import json
import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, AliasChoices, BaseModel, ConfigDict, Field, StringConstraints

from app.core.config import get_settings


def _no_nul(value: str) -> str:
    # Postgres không lưu được ký tự NUL trong text
    if "\x00" in value:
        raise ValueError("chứa ký tự không hợp lệ")
    return value


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("không được để trống")
    return _no_nul(value)


def _settings_json(value: dict) -> dict:
    encoded = json.dumps(value, ensure_ascii=True)
    if len(encoded) > 16_384:
        raise ValueError("settings_json quá lớn")
    if "\\u0000" in encoded:
        raise ValueError("chứa ký tự không hợp lệ")
    return value


# Bỏ khoảng trắng đầu/cuối rồi mới kiểm tra độ dài
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255), AfterValidator(_no_nul)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150), AfterValidator(_no_nul)]
# Giữ nguyên nội dung tin nhắn (xuống dòng, thụt lề) nhưng không cho toàn khoảng trắng
Content = Annotated[str, Field(min_length=1, max_length=20000), AfterValidator(_not_blank)]


_VN_PHONE = re.compile(r"(?:\+?84|0)0?([35789][0-9]{8})")
_INTL_PHONE = re.compile(r"\+(?!84)[1-9][0-9]{7,14}")


def _normalize_phone(value: str) -> str:
    """0912345678, 84912345678, +84 912 345 678 -> +84912345678 (định dạng E.164)."""
    phone = re.sub(r"[\s.\-()]", "", value)
    if match := _VN_PHONE.fullmatch(phone):
        return f"+84{match.group(1)}"
    if get_settings().allow_international_phones and _INTL_PHONE.fullmatch(phone):
        return phone
    raise ValueError("số điện thoại không hợp lệ")


Phone = Annotated[str, Field(max_length=30), AfterValidator(_normalize_phone)]
NewPassword = Annotated[str, Field(min_length=8, max_length=128)]
AvatarUrl = Annotated[str, StringConstraints(pattern=r"^https://\S+$", max_length=2048)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SettingsOut(ORM):
    theme: str
    language: str
    timezone: str
    notification_enabled: bool
    settings_json: dict


class MeOut(ORM):
    id: uuid.UUID
    full_name: str
    phone: str
    avatar_url: str | None
    status: str
    created_at: datetime
    settings: SettingsOut | None


class MeUpdate(BaseModel):
    full_name: Name | None = None
    avatar_url: AvatarUrl | None = None


class SettingsUpdate(BaseModel):
    theme: Literal["light", "dark", "system"] | None = None
    language: Annotated[str, Field(max_length=10), AfterValidator(_no_nul)] | None = None
    timezone: Annotated[str, Field(max_length=100), AfterValidator(_no_nul)] | None = None
    notification_enabled: bool | None = None
    settings_json: Annotated[dict, AfterValidator(_settings_json)] | None = None


class AgentOut(ORM):
    id: uuid.UUID
    name: str


class AgentCreate(BaseModel):
    name: Name
    domain: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255), AfterValidator(_no_nul)]
    api_key: str | None = None
    agent_key: str | None = None


class AgentUpdate(BaseModel):
    name: Name | None = None
    domain: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255), AfterValidator(_no_nul)] | None = None
    api_key: str | None = None
    agent_key: str | None = None


class AgentDetailOut(ORM):
    id: uuid.UUID
    name: str
    domain: str
    has_api_key: bool = False
    has_agent_key: bool = False
    masked_api_key: str | None = None
    masked_agent_key: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentTestConnectionIn(BaseModel):
    domain: str | None = None
    api_key: str | None = None
    agent_key: str | None = None


class AgentTestConnectionOut(BaseModel):
    ok: bool
    message: str
    details: dict | None = None


class ConversationCreate(BaseModel):
    agent_id: uuid.UUID
    title: Title | None = None


class ConversationUpdate(BaseModel):
    title: Title | None = None
    pinned: bool | None = None
    archived: bool | None = None


class ConversationOut(ORM):
    id: uuid.UUID
    agent_id: uuid.UUID
    title: str | None
    status: str
    message_count: int
    last_message_at: datetime | None
    pinned_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MessageOut(ORM):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str | None
    content_type: str
    status: str
    reply_to_message_id: uuid.UUID | None
    error_message: str | None
    # Cột DB tên metadata, thuộc tính ORM tên meta (metadata là tên dành riêng của SQLAlchemy)
    metadata: dict = Field(validation_alias=AliasChoices("meta", "metadata"))
    favorited_at: datetime | None
    created_at: datetime


class MessagePage(BaseModel):
    items: list[MessageOut]
    next_before: uuid.UUID | None = Field(None, description="Gửi lại làm tham số before để tải trang cũ hơn")


class SendMessage(BaseModel):
    content: Content
    # App tự sinh mỗi lần bấm gửi; gửi lại cùng key (mất mạng, bấm 2 lần) sẽ không tạo tin trùng
    idempotency_key: uuid.UUID


class SendMessageOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut | None


class SearchHit(BaseModel):
    message_id: uuid.UUID
    conversation_id: uuid.UUID
    conversation_title: str | None
    role: str
    content: str | None
    created_at: datetime


class RegisterIn(BaseModel):
    phone: Phone
    password: NewPassword
    full_name: Name


class LoginIn(BaseModel):
    phone: Phone
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: NewPassword


class AuthUser(BaseModel):
    id: uuid.UUID
    phone: str
    full_name: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Số giây access token còn hiệu lực")
    expires_at: int = Field(description="Thời điểm access token hết hạn (Unix time)")
    user: AuthUser


# ==================== Scheduled Tasks (Lịch hẹn / Lịch đăng bài) ====================

TaskType = Literal["send_message", "execute_agent", "execute_workflow", "publish_post"]
TaskStatus = Literal["scheduled", "processing", "completed", "failed", "cancelled", "retrying"]


class ScheduledTaskCreate(BaseModel):
    task_name: Name
    task_type: TaskType
    agent_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    payload: dict = Field(default_factory=dict)
    scheduled_at: datetime
    timezone: Annotated[str, Field(max_length=100), AfterValidator(_no_nul)] = "Asia/Ho_Chi_Minh"
    recurrence_rule: Annotated[str, Field(max_length=255), AfterValidator(_no_nul)] | None = None
    max_attempts: int = Field(default=3, ge=1, le=10)


class ScheduledTaskUpdate(BaseModel):
    task_name: Name | None = None
    task_type: TaskType | None = None
    agent_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    payload: dict | None = None
    scheduled_at: datetime | None = None
    timezone: Annotated[str, Field(max_length=100), AfterValidator(_no_nul)] | None = None
    recurrence_rule: Annotated[str, Field(max_length=255), AfterValidator(_no_nul)] | None = None
    status: Literal["scheduled", "cancelled"] | None = None


class ScheduledTaskLogOut(ORM):
    id: uuid.UUID
    task_id: uuid.UUID
    attempt_number: int
    status: str
    request_payload: dict | None = None
    response_payload: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class ScheduledTaskOut(ORM):
    id: uuid.UUID
    user_id: uuid.UUID
    conversation_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    task_name: str
    task_type: str
    payload: dict
    scheduled_at: datetime
    timezone: str
    recurrence_rule: str | None = None
    status: str
    attempts: int
    max_attempts: int
    next_retry_at: datetime | None = None
    last_error: str | None = None
    executed_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ScheduledTaskDetailOut(ScheduledTaskOut):
    logs: list[ScheduledTaskLogOut] = []


class ScheduledTaskPage(BaseModel):
    items: list[ScheduledTaskOut]
    total: int
    limit: int
    offset: int


class ScheduledTaskExecuteOut(BaseModel):
    task_id: uuid.UUID
    status: str
    attempt_number: int
    result: dict | None = None
    error: str | None = None
