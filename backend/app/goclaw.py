"""Gọi GoClaw để lấy câu trả lời của agent.

Chưa có tài liệu API chính thức của GoClaw, nên client này giả định kiểu
OpenAI-compatible giống OpenClaw gateway:
  POST {base_url}/v1/chat/completions  {"model": <goclaw_agent_id>, "messages": [...], "user": <user_id>}
  header <GOCLAW_SESSION_HEADER>: <session key>  -> giữ ngữ cảnh hội thoại phía GoClaw
Kiểm tra lại với GoClaw thật rồi chỉnh hàm _send_openai nếu khác.

GOCLAW_MODE=mock trả lời giả, để chạy app khi chưa có GoClaw.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

import httpx
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Agent, GoclawWorkspace

log = logging.getLogger(__name__)


class GoClawError(Exception):
    """Lỗi gọi GoClaw. Nội dung được hiển thị cho user nên KHÔNG chứa URL, key hay chi tiết nội bộ."""


@dataclass(frozen=True)
class GoClawTarget:
    agent_name: str
    goclaw_agent_id: str
    base_url: str
    api_key: str | None


@dataclass
class GoClawReply:
    content: str
    session_id: str
    message_id: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: Decimal | None = None


async def resolve_target(session: AsyncSession, *, agent: Agent, workspace: GoclawWorkspace) -> GoClawTarget:
    """Gom mọi thứ cần đọc từ DB (kể cả API key trong Vault) trước khi gọi GoClaw."""
    api_key = get_settings().goclaw_api_key
    if get_settings().goclaw_mode != "mock" and workspace.api_key_secret_id:
        try:
            async with session.begin_nested():
                secret = await session.scalar(
                    text("select decrypted_secret from vault.decrypted_secrets where id = :id"),
                    {"id": workspace.api_key_secret_id},
                )
        except DBAPIError:
            log.exception("Không đọc được GoClaw API key từ Vault (workspace %s)", workspace.id)
            raise GoClawError("Chưa cấu hình xong kết nối tới agent")
        api_key = secret or api_key
    return GoClawTarget(agent.name, agent.goclaw_agent_id, workspace.base_url, api_key)


async def send_message(target: GoClawTarget, *, session_key: str, user_id: uuid.UUID, content: str) -> GoClawReply:
    settings = get_settings()
    if settings.goclaw_mode == "mock":
        return GoClawReply(
            content=f"(mock {target.agent_name}) Mình đã nhận: {content}",
            session_id=session_key,
            message_id=str(uuid.uuid4()),
            model="mock",
            input_tokens=len(content.split()),
            output_tokens=len(content.split()) + 4,
            cost_usd=Decimal("0"),
        )
    try:
        # Giới hạn TỔNG thời gian (httpx timeout chỉ tính từng giai đoạn), để không vượt quá
        # ngưỡng stale recovery trong routers/conversations.py
        async with asyncio.timeout(settings.goclaw_timeout_seconds):
            return await _send_openai(target, session_key=session_key, user_id=user_id, content=content)
    except TimeoutError:
        raise GoClawError("Agent phản hồi quá lâu, vui lòng thử lại")


async def _send_openai(target: GoClawTarget, *, session_key: str, user_id: uuid.UUID, content: str) -> GoClawReply:
    settings = get_settings()
    headers = {settings.goclaw_session_header: session_key}
    if target.api_key:
        headers["Authorization"] = f"Bearer {target.api_key}"
    body = {"model": target.goclaw_agent_id, "messages": [{"role": "user", "content": content}], "user": str(user_id)}
    try:
        async with httpx.AsyncClient(timeout=settings.goclaw_timeout_seconds) as client:
            resp = await client.post(f"{target.base_url.rstrip('/')}/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        usage = data.get("usage") or {}
        return GoClawReply(
            content=data["choices"][0]["message"]["content"] or "",
            session_id=session_key,
            message_id=data.get("id"),
            model=data.get("model"),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )
    except httpx.HTTPStatusError as e:
        log.warning("GoClaw trả %s cho agent %s: %s", e.response.status_code, target.goclaw_agent_id, e)
        raise GoClawError(f"Agent đang gặp lỗi (mã {e.response.status_code}), vui lòng thử lại")
    except httpx.TimeoutException as e:
        log.warning("GoClaw timeout (agent %s): %s", target.goclaw_agent_id, e)
        raise GoClawError("Agent phản hồi quá lâu, vui lòng thử lại")
    except httpx.HTTPError as e:
        log.warning("Không kết nối được GoClaw (agent %s): %s", target.goclaw_agent_id, e)
        raise GoClawError("Không kết nối được tới agent, vui lòng thử lại")
    except (KeyError, IndexError, TypeError, ValueError) as e:
        log.warning("GoClaw trả dữ liệu không đúng định dạng (agent %s): %r", target.goclaw_agent_id, e)
        raise GoClawError("Agent trả về dữ liệu không đọc được")
