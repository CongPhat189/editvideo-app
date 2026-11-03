from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.supabase_deps import CurrentUser, Session
from app.core.crypto import decrypt_secret, encrypt_secret
from app.integrations.goclaw import test_connection
from app.models import Agent
from app.schemas.mobile import (
    AgentCreate,
    AgentDetailOut,
    AgentOut,
    AgentTestConnectionIn,
    AgentTestConnectionOut,
    AgentUpdate,
)

router = APIRouter(prefix="/agents", tags=["agents"])


def _mask_key(secret: str | None) -> str | None:
    if not secret:
        return None
    try:
        decrypted = decrypt_secret(secret)
    except Exception:
        return "********"
    if len(decrypted) <= 8:
        return "****"
    return f"{decrypted[:3]}****{decrypted[-4:]}"


def _to_detail_out(agent: Agent) -> AgentDetailOut:
    return AgentDetailOut(
        id=agent.id,
        name=agent.name,
        domain=agent.domain,
        has_api_key=bool(agent.api_key),
        has_agent_key=bool(agent.agent_key),
        masked_api_key=_mask_key(agent.api_key),
        masked_agent_key=_mask_key(agent.agent_key),
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.get("", response_model=list[AgentOut])
async def list_agents(user: CurrentUser, session: Session):
    """Danh sách agent. Chỉ trả id và name cho app."""
    return (await session.scalars(select(Agent).order_by(Agent.name))).all()


@router.post("", response_model=AgentDetailOut, status_code=status.HTTP_201_CREATED)
async def create_agent(payload: AgentCreate, user: CurrentUser, session: Session):
    """Tạo agent mới với domain và API Key cá nhân GoClaw (được mã hóa bảo mật)."""
    encrypted_api_key = encrypt_secret(payload.api_key) if payload.api_key else None
    encrypted_agent_key = encrypt_secret(payload.agent_key) if payload.agent_key else None

    now = datetime.now(timezone.utc)
    agent = Agent(
        id=uuid.uuid4(),
        name=payload.name,
        domain=payload.domain,
        api_key=encrypted_api_key,
        agent_key=encrypted_agent_key,
        created_at=now,
        updated_at=now,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return _to_detail_out(agent)


@router.post("/test-connection", response_model=AgentTestConnectionOut)
async def test_agent_connection(payload: AgentTestConnectionIn, user: CurrentUser):
    """Kiểm tra kết nối trực tiếp tới GoClaw mà không cần lưu vào DB trước."""
    if not payload.domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Thiếu thông tin domain để kiểm tra kết nối"},
        )
    result = await test_connection(
        domain=payload.domain,
        api_key=payload.api_key,
        agent_key=payload.agent_key,
    )
    return AgentTestConnectionOut(**result)


@router.get("/{agent_id}", response_model=AgentDetailOut)
async def get_agent(agent_id: uuid.UUID, user: CurrentUser, session: Session):
    """Xem chi tiết thông tin agent, che một phần key bảo mật."""
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy agent"},
        )
    return _to_detail_out(agent)


@router.put("/{agent_id}", response_model=AgentDetailOut)
async def update_agent(agent_id: uuid.UUID, payload: AgentUpdate, user: CurrentUser, session: Session):
    """Cập nhật thông tin agent hoặc thay đổi API key."""
    agent = await session.get(Agent, agent_id)
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

    await session.commit()
    await session.refresh(agent)
    return _to_detail_out(agent)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: uuid.UUID, user: CurrentUser, session: Session):
    """Xóa agent khỏi hệ thống."""
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy agent"},
        )

    await session.delete(agent)
    await session.commit()
    return {"ok": True, "message": "Đã xóa agent thành công", "id": str(agent_id)}


@router.post("/{agent_id}/test", response_model=AgentTestConnectionOut)
async def test_saved_agent_connection(agent_id: uuid.UUID, user: CurrentUser, session: Session):
    """Kiểm tra kết nối của agent đã lưu trong hệ thống."""
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy agent"},
        )

    plain_api_key = decrypt_secret(agent.api_key) if agent.api_key else None
    plain_agent_key = decrypt_secret(agent.agent_key) if agent.agent_key else None

    result = await test_connection(
        domain=agent.domain,
        api_key=plain_api_key,
        agent_key=plain_agent_key,
    )
    return AgentTestConnectionOut(**result)
