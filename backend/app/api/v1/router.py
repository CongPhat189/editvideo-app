from fastapi import APIRouter

from app.api.v1.endpoints import analytics, auth, dashboard, platforms, publishing, schedule, users, videos

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(dashboard.router)
api_router.include_router(videos.router)
api_router.include_router(schedule.router)
api_router.include_router(analytics.router)
api_router.include_router(platforms.router)
api_router.include_router(publishing.router)
