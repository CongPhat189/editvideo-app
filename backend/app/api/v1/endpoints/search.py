from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import text

from app.api.supabase_deps import CurrentUser, Session
from app.schemas.mobile import SearchHit

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchHit])
async def search_messages(
    user: CurrentUser,
    session: Session,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    """Tìm không dấu trong lịch sử chat: 'da nang' ra 'Đà Nẵng'."""
    if "\x00" in q:
        return []
    rows = await session.execute(
        # Tin hệ thống gửi ngầm (metadata.hidden) không hiện trong khung chat nên cũng không được tìm thấy
        text(
            "select s.* from public.search_messages(:user_id, :q, :limit) s "
            "join public.messages m on m.id = s.message_id "
            "where not jsonb_exists(m.metadata, 'hidden')"
        ),
        {"user_id": user.id, "q": q, "limit": limit},
    )
    return [SearchHit(**row) for row in rows.mappings()]
