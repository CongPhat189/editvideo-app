from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


# Tạo khi cần chứ không tạo lúc import, để API demo vẫn chạy khi chưa cấu hình Supabase
@lru_cache
def get_engine() -> AsyncEngine:
    # hide_parameters: lỗi DB ghi ra log không kèm giá trị câu lệnh (password_hash, nội dung chat...)
    return create_async_engine(
        get_settings().sqlalchemy_url, pool_pre_ping=True, pool_size=5, max_overflow=5, hide_parameters=True
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
