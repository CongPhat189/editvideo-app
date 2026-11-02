from fastapi import APIRouter
from sqlalchemy import exists, func, or_, select

from app.auth import CurrentUser, Session
from app.models import Agent, GoclawWorkspace, UserAgentAccess
from app.schemas import AgentOut

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
async def list_agents(user: CurrentUser, session: Session):
    """Các agent user được dùng: đang hoạt động và (public hoặc đã được cấp quyền còn hạn)."""
    granted = exists().where(
        UserAgentAccess.agent_id == Agent.id,
        UserAgentAccess.user_id == user.id,
        or_(UserAgentAccess.expires_at.is_(None), UserAgentAccess.expires_at > func.now()),
    )
    rows = await session.scalars(
        select(Agent)
        .join(GoclawWorkspace, GoclawWorkspace.id == Agent.workspace_id)
        .where(Agent.is_active, GoclawWorkspace.is_active, or_(Agent.visibility == "public", granted))
        .order_by(Agent.sort_order, Agent.name)
    )
    return rows.all()
