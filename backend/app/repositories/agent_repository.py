from __future__ import annotations

import uuid
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent


async def get_by_id(session: AsyncSession, agent_id: uuid.UUID) -> Agent | None:
    """Lấy agent theo id."""
    return await session.get(Agent, agent_id)


async def list_by_user(session: AsyncSession, user_id: uuid.UUID) -> list[Agent]:
    """Lấy danh sách agent của người dùng kèm các agent mặc định của hệ thống (user_id IS NULL)."""
    query = (
        select(Agent)
        .where(or_(Agent.user_id == user_id, Agent.user_id.is_(None)))
        .order_by(Agent.name)
    )
    result = await session.scalars(query)
    return list(result.all())


async def get_by_user_id(session: AsyncSession, user_id: uuid.UUID) -> list[Agent]:
    """Lấy danh sách các agent thuộc riêng về một user_id cụ thể."""
    query = select(Agent).where(Agent.user_id == user_id).order_by(Agent.name)
    result = await session.scalars(query)
    return list(result.all())


async def create(session: AsyncSession, agent: Agent) -> Agent:
    """Thêm agent mới vào database."""
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def update(session: AsyncSession, agent: Agent) -> Agent:
    """Cập nhật thông tin agent."""
    await session.commit()
    await session.refresh(agent)
    return agent


async def delete(session: AsyncSession, agent: Agent) -> None:
    """Xóa agent khỏi database."""
    await session.delete(agent)
    await session.commit()

