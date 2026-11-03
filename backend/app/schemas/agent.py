from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


def _no_nul(value: str) -> str:
    """Postgres không lưu được ký tự NUL (\x00)."""
    if "\x00" in value:
        raise ValueError("chứa ký tự không hợp lệ")
    return value


Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
    AfterValidator(_no_nul),
]

Domain = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    AfterValidator(_no_nul),
]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ==================== Request Schemas ====================

class AgentCreate(BaseModel):
    """Schema dữ liệu đầu vào khi người dùng tạo mới Agent."""
    name: Name = Field(..., description="Tên hiển thị của agent (1-150 ký tự)")
    domain: Domain = Field(..., description="Địa chỉ máy chủ GoClaw (vd: https://goclaw.abc.com)")
    api_key: str | None = Field(default=None, description="API Key kết nối GoClaw (được mã hóa tự động)")
    agent_key: str | None = Field(default=None, description="Agent Key của GoClaw (được mã hóa tự động)")


class AgentUpdate(BaseModel):
    """Schema dữ liệu đầu vào khi người dùng cập nhật Agent."""
    name: Name | None = Field(default=None, description="Tên hiển thị mới")
    domain: Domain | None = Field(default=None, description="Domain máy chủ mới")
    api_key: str | None = Field(default=None, description="API Key mới (nếu muốn thay đổi)")
    agent_key: str | None = Field(default=None, description="Agent Key mới (nếu muốn thay đổi)")


class AgentTestConnectionIn(BaseModel):
    """Schema dữ liệu đầu vào khi kiểm tra thử kết nối tới GoClaw."""
    domain: str | None = Field(default=None, description="Domain máy chủ GoClaw cần kiểm tra")
    api_key: str | None = Field(default=None, description="API Key cần kiểm tra")
    agent_key: str | None = Field(default=None, description="Agent Key cần kiểm tra")


# ==================== Response Schemas ====================

class AgentOut(ORM):
    """Schema danh sách rút gọn trả về cho dropdown (chỉ id và name)."""
    id: uuid.UUID
    name: str


class AgentDetailOut(ORM):
    """Schema chi tiết đầy đủ của Agent trả về cho client (key đã được che mờ bảo mật)."""
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    name: str
    domain: str
    has_api_key: bool = False
    has_agent_key: bool = False
    masked_api_key: str | None = None
    masked_agent_key: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentTestConnectionOut(BaseModel):
    """Schema kết quả kiểm tra kết nối tới GoClaw."""
    ok: bool
    message: str
    details: dict | None = None


# Aliases thân thiện theo chuẩn Request / Response
AgentCreateRequest = AgentCreate
AgentUpdateRequest = AgentUpdate
AgentTestConnectionRequest = AgentTestConnectionIn
AgentListResponse = AgentOut
AgentDetailResponse = AgentDetailOut
AgentTestConnectionResponse = AgentTestConnectionOut

__all__ = [
    "AgentCreate",
    "AgentUpdate",
    "AgentTestConnectionIn",
    "AgentOut",
    "AgentDetailOut",
    "AgentTestConnectionOut",
    "AgentCreateRequest",
    "AgentUpdateRequest",
    "AgentTestConnectionRequest",
    "AgentListResponse",
    "AgentDetailResponse",
    "AgentTestConnectionResponse",
]

