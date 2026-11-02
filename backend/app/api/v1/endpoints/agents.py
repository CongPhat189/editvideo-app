from fastapi import APIRouter
from sqlalchemy import select

from app.api.supabase_deps import CurrentUser, Session
from app.models import Agent
from app.schemas.mobile import AgentOut

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
async def list_agents(user: CurrentUser, session: Session):
    """Danh sách agent. Không trả key và domain cho app."""
    return (await session.scalars(select(Agent).order_by(Agent.name))).all()
