import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("không được để trống")
    return value


# Bỏ khoảng trắng đầu/cuối rồi mới kiểm tra độ dài
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
# Giữ nguyên nội dung tin nhắn (xuống dòng, thụt lề) nhưng không cho toàn khoảng trắng
Content = Annotated[str, Field(min_length=1, max_length=20000), AfterValidator(_not_blank)]


_VN_PHONE = re.compile(r"(?:\+?84|0)0?([35789]\d{8})")
_INTL_PHONE = re.compile(r"\+(?!84)[1-9]\d{7,14}")


def _normalize_phone(value: str) -> str:
    """0912345678, 84912345678, +84 912 345 678 -> +84912345678 (định dạng E.164)."""
    phone = re.sub(r"[\s.\-()]", "", value)
    if match := _VN_PHONE.fullmatch(phone):
        return f"+84{match.group(1)}"
    if _INTL_PHONE.fullmatch(phone):
        return phone
    raise ValueError("số điện thoại không hợp lệ")


def _password_fits(value: str) -> str:
    if len(value.encode()) > 72:  # giới hạn của bcrypt, tính theo byte
        raise ValueError("mật khẩu quá dài")
    return value


Phone = Annotated[str, Field(max_length=30), AfterValidator(_normalize_phone)]
NewPassword = Annotated[str, Field(min_length=8), AfterValidator(_password_fits)]


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
    avatar_path: str | None
    status: str
    created_at: datetime
    settings: SettingsOut | None


class MeUpdate(BaseModel):
    full_name: Name | None = None
    avatar_path: str | None = None


class SettingsUpdate(BaseModel):
    theme: Literal["light", "dark", "system"] | None = None
    language: str | None = Field(None, max_length=10)
    timezone: str | None = Field(None, max_length=100)
    notification_enabled: bool | None = None
    settings_json: dict | None = None


class AgentOut(ORM):
    id: uuid.UUID
    name: str
    description: str | None
    avatar_url: str | None
    visibility: str
    sort_order: int


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
    title_source: str
    status: str
    message_count: int
    last_message_at: datetime | None
    pinned_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MessageOut(ORM):
    id: uuid.UUID
    seq: int
    conversation_id: uuid.UUID
    role: str
    content: str | None
    content_type: str
    status: str
    reply_to_message_id: uuid.UUID | None
    error_message: str | None
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: Decimal | None
    favorited_at: datetime | None
    created_at: datetime


class MessagePage(BaseModel):
    items: list[MessageOut]
    next_before_seq: int | None = Field(None, description="Gửi lại làm before_seq để tải trang cũ hơn")


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
    password: str = Field(min_length=1, max_length=200)


class VerifyOtpIn(BaseModel):
    phone: Phone
    otp: str = Field(pattern=r"^\d{4,10}$")


class ResendOtpIn(BaseModel):
    phone: Phone


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class AuthUser(BaseModel):
    id: uuid.UUID
    phone: str | None
    full_name: str | None


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int = Field(description="Số giây access token còn hiệu lực")
    expires_at: int | None = Field(None, description="Thời điểm hết hạn (Unix time)")
    user: AuthUser


class RegisterOut(BaseModel):
    phone: str
    otp_required: bool
    session: TokenOut | None = None


class OtpOut(BaseModel):
    phone: str
