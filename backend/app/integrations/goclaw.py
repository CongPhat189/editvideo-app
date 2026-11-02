"""Gọi GoClaw để lấy câu trả lời của agent.

Chưa có tài liệu API chính thức của GoClaw, nên client này giả định kiểu
OpenAI-compatible giống OpenClaw gateway:
  POST {agents.domain}/v1/chat/completions  {"model": <GOCLAW_DEFAULT_MODEL>, "messages": [...], "user": <user_id>}
  header <GOCLAW_SESSION_HEADER>: <session key>  -> giữ ngữ cảnh hội thoại phía GoClaw
Kiểm tra lại với GoClaw thật rồi chỉnh hàm _send_openai nếu khác.

GOCLAW_MODE=mock trả lời giả, để chạy app khi chưa có GoClaw.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any
from decimal import Decimal

import httpx

from app.core.config import SupabaseNotConfigured, get_settings, settings
from app.core.crypto import SecretDecryptError, decrypt_secret
from app.integrations.external_api import request_json
from app.models import Agent

log = logging.getLogger(__name__)


class GoClawError(Exception):
    """Lỗi gọi GoClaw. Nội dung được hiển thị cho user nên KHÔNG chứa URL, key hay chi tiết nội bộ."""


@dataclass(frozen=True)
class GoClawTarget:
    agent_name: str
    model: str
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


def resolve_target(agent: Agent) -> GoClawTarget:
    """Gom thông tin của agent trước khi gọi GoClaw, để lúc chờ không cần đụng tới DB."""
    config = get_settings()
    api_key = config.goclaw_api_key
    if config.goclaw_mode != "mock" and agent.key:
        try:
            api_key = decrypt_secret(agent.key)
        except (SecretDecryptError, SupabaseNotConfigured):
            log.exception("Không giải mã được API key của agent %s", agent.id)
            raise GoClawError("Chưa cấu hình xong kết nối tới agent")
    return GoClawTarget(agent.name, config.goclaw_default_model, agent.domain, api_key)


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
        # ngưỡng stale recovery trong api/v1/endpoints/conversations.py
        async with asyncio.timeout(settings.goclaw_timeout_seconds):
            return await _send_openai(target, session_key=session_key, user_id=user_id, content=content)
    except TimeoutError:
        raise GoClawError("Agent phản hồi quá lâu, vui lòng thử lại")


def _clean_text(value: Any, max_length: int | None = None) -> str | None:
    if not isinstance(value, str):
        return None
    return value.replace("\x00", "")[:max_length]


def _count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _parse_reply(data: dict[str, Any], session_key: str) -> GoClawReply:
    """Dữ liệu từ bên ngoài: dọn sạch trước khi ghi DB, sai định dạng thì ném ValueError."""
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, list):  # dạng content parts của OpenAI
        content = "".join(part["text"] for part in content if part.get("type") == "text")
    if content is not None and not isinstance(content, str):
        raise ValueError("content không phải chuỗi")
    usage = data.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    return GoClawReply(
        content=_clean_text(content) or "",
        session_id=session_key,
        message_id=_clean_text(data.get("id"), 255),
        model=_clean_text(data.get("model"), 100),
        input_tokens=_count(usage.get("prompt_tokens")),
        output_tokens=_count(usage.get("completion_tokens")),
    )


async def _send_openai(target: GoClawTarget, *, session_key: str, user_id: uuid.UUID, content: str) -> GoClawReply:
    settings = get_settings()
    headers = {settings.goclaw_session_header: session_key}
    if target.api_key:
        headers["Authorization"] = f"Bearer {target.api_key}"
    body = {"model": target.model, "messages": [{"role": "user", "content": content}], "user": str(user_id)}
    try:
        async with httpx.AsyncClient(timeout=settings.goclaw_timeout_seconds) as client:
            resp = await client.post(f"{target.base_url.rstrip('/')}/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return _parse_reply(data, session_key)
    except httpx.HTTPStatusError as e:
        log.warning("GoClaw trả %s cho agent %s: %s", e.response.status_code, target.model, e)
        raise GoClawError(f"Agent đang gặp lỗi (mã {e.response.status_code}), vui lòng thử lại")
    except httpx.TimeoutException as e:
        log.warning("GoClaw timeout (agent %s): %s", target.model, e)
        raise GoClawError("Agent phản hồi quá lâu, vui lòng thử lại")
    except httpx.HTTPError as e:
        log.warning("Không kết nối được GoClaw (agent %s): %s", target.model, e)
        raise GoClawError("Không kết nối được tới agent, vui lòng thử lại")
    except (AttributeError, KeyError, IndexError, TypeError, ValueError) as e:
        log.warning("GoClaw trả dữ liệu không đúng định dạng (agent %s): %r", target.model, e)
        raise GoClawError("Agent trả về dữ liệu không đọc được")


class GoClawClient:
    """Client kết nối GoClaw API. Bổ sung endpoint thật khi có tài liệu API."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or settings.GOCLAW_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.GOCLAW_API_KEY

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def get(self, path: str) -> dict[str, Any]:
        return request_json("GET", f"{self.base_url}/{path.lstrip('/')}", headers=self._headers())

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return request_json("POST", f"{self.base_url}/{path.lstrip('/')}", payload, headers=self._headers())
