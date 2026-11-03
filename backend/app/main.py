import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.supabase_deps import Session
from app.api.v1.router import api_router
from app.core.config import SupabaseNotConfigured, settings
from app.core.logging import logger, setup_logging
from app.db.init_db import init_db
from app.services import schedule_worker

setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.ENABLE_DEMO_API:
        try:
            init_db()
        except Exception:
            # Database demo hỏng thì chỉ các API /api/* bị ảnh hưởng, API mobile vẫn phải chạy
            logger.exception("Không khởi tạo được database demo")
    worker = asyncio.create_task(schedule_worker.run_forever())
    yield
    worker.cancel()


app = FastAPI(title=settings.APP_TITLE, version=settings.APP_VERSION, lifespan=lifespan)

# Đăng nhập bằng header Authorization, không dùng cookie, nên không bật allow_credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Mặc định FastAPI trả lại cả giá trị đã gửi, có thể là mật khẩu
    detail = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(SupabaseNotConfigured)
async def supabase_not_configured(request: Request, exc: SupabaseNotConfigured) -> JSONResponse:
    logger.error("%s", exc)
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": "Chưa cấu hình Supabase"})


app.include_router(api_router)


@app.get("/api/health")
def api_health() -> dict:
    return {"ok": True, "message": "Backend đang chạy"}


@app.get("/health", tags=["health"], name="health")
async def database_health(session: Session):
    await session.execute(text("select 1"))
    return {"status": "ok", "database": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
