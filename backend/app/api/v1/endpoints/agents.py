from __future__ import annotations

import uuid
from fastapi import APIRouter, status

from app.api.supabase_deps import CurrentUser, Session
from app.schemas.mobile import (
    AgentCreate,
    AgentDetailOut,
    AgentOut,
    AgentTestConnectionIn,
    AgentTestConnectionOut,
    AgentUpdate,
)
from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])

# Aliases cho service helpers
_mask_key = agent_service.mask_key
_to_detail_out = agent_service.to_detail_out


@router.get("", response_model=list[AgentOut])
async def list_agents(user: CurrentUser, session: Session):
    """Danh sách agent (chỉ trả id và name cho dropdown)."""
    return await agent_service.list_agents(session, user.id)


@router.post("", response_model=AgentDetailOut, status_code=status.HTTP_201_CREATED)
async def create_agent(payload: AgentCreate, user: CurrentUser, session: Session):
    """Tạo agent mới với domain và API Key / Agent Key cá nhân (được mã hóa bảo mật)."""
    return await agent_service.create_agent(session, user.id, payload)


@router.post("/test-connection", response_model=AgentTestConnectionOut)
async def test_agent_connection(payload: AgentTestConnectionIn, user: CurrentUser):
    """Kiểm tra kết nối trực tiếp tới GoClaw với domain và key tùy chọn."""
    return await agent_service.test_connection(payload)


@router.get("/{agent_id}", response_model=AgentDetailOut)
async def get_agent(agent_id: uuid.UUID, user: CurrentUser, session: Session):
    """Xem chi tiết thông tin agent, che một phần key bảo mật."""
    return await agent_service.get_agent(session, agent_id, user.id)


@router.put("/{agent_id}", response_model=AgentDetailOut)
async def update_agent(agent_id: uuid.UUID, payload: AgentUpdate, user: CurrentUser, session: Session):
    """Cập nhật thông tin agent hoặc thay đổi/xoay vòng API key."""
    return await agent_service.update_agent(session, agent_id, user.id, payload)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: uuid.UUID, user: CurrentUser, session: Session):
    """Xóa agent khỏi hệ thống."""
    return await agent_service.delete_agent(session, agent_id, user.id)


@router.post("/{agent_id}/test", response_model=AgentTestConnectionOut)
async def test_saved_agent_connection(agent_id: uuid.UUID, user: CurrentUser, session: Session):
    """Kiểm tra kết nối của agent đã lưu trong hệ thống."""
    return await agent_service.test_saved_agent_connection(session, agent_id, user.id)
