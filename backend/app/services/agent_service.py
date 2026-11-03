from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret
from app.integrations.goclaw import test_connection as goclaw_test_conn
from app.models import Agent
from app.repositories import agent_repository
from app.schemas.agent import (
    AgentCreate,
    AgentDetailOut,
    AgentOut,
    AgentTestConnectionIn,
    AgentTestConnectionOut,
    AgentUpdate,
)


def mask_key(secret: str | None) -> str | None:
    """Che mờ khóa bảo mật dạng sk-****1234 hoặc ****."""
    if not secret:
        return None
    try:
        decrypted = decrypt_secret(secret)
    except Exception:
        return "********"
    if len(decrypted) <= 8:
        return "****"
    return f"{decrypted[:3]}****{decrypted[-4:]}"


def to_detail_out(agent: Agent) -> AgentDetailOut:
    """Chuyển model Agent thành schema trả về cho client."""
    return AgentDetailOut(
        id=agent.id,
        user_id=getattr(agent, "user_id", None),
        name=agent.name,
        domain=agent.domain,
        has_api_key=bool(agent.api_key),
        has_agent_key=bool(agent.agent_key),
        masked_api_key=mask_key(agent.api_key),
        masked_agent_key=mask_key(agent.agent_key),
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


async def list_agents(session: AsyncSession, user_id: uuid.UUID) -> list[AgentOut]:
    """Lấy danh sách agent cho người dùng."""
    agents = await agent_repository.list_by_user(session, user_id)
    return [AgentOut.model_validate(a) for a in agents]


async def list_agents_by_user_id(session: AsyncSession, user_id: uuid.UUID) -> list[AgentDetailOut]:
    """Lấy danh sách chi tiết các agent thuộc riêng về một user_id (kèm thông tin domain, key đã che mờ)."""
    agents = await agent_repository.get_by_user_id(session, user_id)
    return [to_detail_out(a) for a in agents]


async def create_agent(session: AsyncSession, user_id: uuid.UUID, payload: AgentCreate) -> AgentDetailOut:
    """Nghiệp vụ tạo agent: mã hóa API Key & Agent Key trước khi lưu DB qua repository."""
    encrypted_api_key = encrypt_secret(payload.api_key) if payload.api_key else None
    encrypted_agent_key = encrypt_secret(payload.agent_key) if payload.agent_key else None

    now = datetime.now(timezone.utc)
    agent = Agent(
        id=uuid.uuid4(),
        user_id=user_id,
        name=payload.name,
        domain=payload.domain,
        api_key=encrypted_api_key,
        agent_key=encrypted_agent_key,
        created_at=now,
        updated_at=now,
    )
    saved_agent = await agent_repository.create(session, agent)
    return to_detail_out(saved_agent)


async def get_agent(session: AsyncSession, agent_id: uuid.UUID, user_id: uuid.UUID) -> AgentDetailOut:
    """Lấy thông tin chi tiết của agent."""
    agent = await agent_repository.get_by_id(session, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy agent"},
        )
    return to_detail_out(agent)


async def update_agent(
    session: AsyncSession,
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: AgentUpdate,
) -> AgentDetailOut:
    """Cập nhật thông tin agent hoặc thay đổi/xoay vòng API key."""
    agent = await agent_repository.get_by_id(session, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy agent"},
        )

    if payload.name is not None:
        agent.name = payload.name
    if payload.domain is not None:
        agent.domain = payload.domain
    if payload.api_key is not None:
        agent.api_key = encrypt_secret(payload.api_key) if payload.api_key else None
    if payload.agent_key is not None:
        agent.agent_key = encrypt_secret(payload.agent_key) if payload.agent_key else None

    agent.updated_at = datetime.now(timezone.utc)
    updated_agent = await agent_repository.update(session, agent)
    return to_detail_out(updated_agent)


async def delete_agent(session: AsyncSession, agent_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
    """Xóa agent khỏi hệ thống."""
    agent = await agent_repository.get_by_id(session, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy agent"},
        )

    await agent_repository.delete(session, agent)
    return {"ok": True, "message": "Đã xóa agent thành công", "id": str(agent_id)}


async def test_connection(payload: AgentTestConnectionIn) -> AgentTestConnectionOut:
    """Kiểm tra kết nối trực tiếp tới GoClaw mà không cần lưu vào DB trước."""
    if not payload.domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Thiếu thông tin domain để kiểm tra kết nối"},
        )
    result = await goclaw_test_conn(
        domain=payload.domain,
        api_key=payload.api_key,
        agent_key=payload.agent_key,
    )
    return AgentTestConnectionOut(**result)


async def test_saved_agent_connection(
    session: AsyncSession,
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
) -> AgentTestConnectionOut:
    """Kiểm tra kết nối của agent đã lưu trong hệ thống bằng cách giải mã key đã lưu."""
    agent = await agent_repository.get_by_id(session, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy agent"},
        )

    plain_api_key = decrypt_secret(agent.api_key) if agent.api_key else None
    plain_agent_key = decrypt_secret(agent.agent_key) if agent.agent_key else None

    result = await goclaw_test_conn(
        domain=agent.domain,
        api_key=plain_api_key,
        agent_key=plain_agent_key,
    )
    return AgentTestConnectionOut(**result)

