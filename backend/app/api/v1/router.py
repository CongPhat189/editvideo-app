from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    analytics,
    auth,
    conversations,
    dashboard,
    me,
    mobile_auth,
    platforms,
    publishing,
    schedule,
    search,
    users,
    videos,
)
from app.core.config import settings


def build_api_router(enable_demo: bool) -> APIRouter:
    router = APIRouter()

    if enable_demo:
        router.include_router(auth.router)
        router.include_router(users.router)
        router.include_router(dashboard.router)
        router.include_router(videos.router)
        router.include_router(schedule.router)
        router.include_router(analytics.router)
        router.include_router(platforms.router)
        router.include_router(publishing.router)

    # API mobile: tài khoản và dữ liệu nằm trên Supabase Postgres, token do backend tự cấp
    router.include_router(mobile_auth.router)
    router.include_router(me.router)
    router.include_router(agents.router)
    router.include_router(conversations.router)
    router.include_router(search.router)
    return router


api_router = build_api_router(settings.ENABLE_DEMO_API)
