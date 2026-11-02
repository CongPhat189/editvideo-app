from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth import Session
from app.config import get_settings
from app.routers import agents, auth, conversations, me, search

app = FastAPI(title="GoClaw Mobile API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(agents.router)
app.include_router(conversations.router)
app.include_router(search.router)


@app.get("/health", tags=["health"])
async def health(session: Session):
    await session.execute(text("select 1"))
    return {"status": "ok", "database": "ok"}
