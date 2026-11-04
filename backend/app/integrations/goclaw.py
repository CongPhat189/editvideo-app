"""Gọi GoClaw để lấy câu trả lời của agent.

  POST {agents.domain}/v1/agents/{agent_key}/wake  {"message": ..., "session_key": ...}
  Authorization: Bearer <api_key>
  X-GoClaw-User-Id: <user_id>
  -> {"content": ..., "run_id": ..., "usage": {"prompt_tokens": ..., "completion_tokens": ...}}

Dùng /wake thay vì /v1/chat/completions vì chat/completions gộp mọi hội thoại của cùng user + agent
vào một session, còn app cần mỗi conversation có ngữ cảnh riêng (session_key).

Tin có file: /wake chỉ nhận văn bản, nên tải file lên POST /v1/media/upload rồi gửi chat.send qua WebSocket /ws,
cùng session_key nên agent vẫn nhớ ngữ cảnh. Câu trả lời nằm trong frame res của chat.send.

GOCLAW_MODE=mock trả lời giả, để chạy app khi chưa có GoClaw.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, BinaryIO
from decimal import Decimal
from urllib.parse import quote

import httpx
import websockets
from websockets.exceptions import WebSocketException

from app.core.config import SupabaseNotConfigured, get_settings, settings
from app.core.crypto import SecretDecryptError, decrypt_secret
from app.integrations.external_api import request_json
from app.models import Agent

log = logging.getLogger(__name__)


class GoClawError(Exception):
    """Lỗi gọi GoClaw. Nội dung được hiển thị cho user nên KHÔNG chứa URL, key hay chi tiết nội bộ.

    retryable: chắc chắn GoClaw chưa xử lý tin, gửi lại không có nguy cơ agent làm hai lần.
    """

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class GoClawTarget:
    agent_name: str
    agent_key: str | None  # chỉ None ở chế độ mock
    base_url: str
    api_key: str | None


@dataclass(frozen=True)
class GoClawMedia:
    filename: str
    mime_type: str
    file: BinaryIO


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
    api_key, agent_key = config.goclaw_api_key, None
    if config.goclaw_mode != "mock":
        try:
            if agent.api_key:
                api_key = decrypt_secret(agent.api_key)
            if agent.agent_key:
                agent_key = decrypt_secret(agent.agent_key)
        except (SecretDecryptError, SupabaseNotConfigured):
            log.exception("Không giải mã được key của agent %s", agent.id)
            raise GoClawError("Chưa cấu hình xong kết nối tới agent")
        if not agent_key:
            raise GoClawError("Agent chưa được cấu hình agent_key của GoClaw")
    return GoClawTarget(agent.name, agent_key, agent.domain, api_key)


def session_key_for(target: GoClawTarget, conversation_id: uuid.UUID) -> str:
    """Mỗi conversation một session bên GoClaw, theo định dạng agent:{agent}:{channel}:{kind}:{chat}."""
    if target.agent_key is None:
        return str(conversation_id)
    return f"agent:{target.agent_key}:app:direct:{conversation_id}"


def _base_url(domain: str) -> str:
    domain = domain.strip().rstrip("/")
    return domain if domain.startswith(("http://", "https://")) else f"https://{domain}"


async def test_connection(
    domain: str,
    api_key: str | None = None,
    agent_key: str | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Kiểm tra kết nối tới GoClaw qua domain và API key cá nhân."""
    try:
        config = get_settings()
        is_mock_mode = config.goclaw_mode == "mock"
    except (SupabaseNotConfigured, Exception):
        is_mock_mode = False

    is_mock = is_mock_mode and (
        "mock" in domain.lower()
        or domain.endswith(".goclaw.ai")
        or domain.endswith(".local")
        or domain.endswith(".test")
        or domain in ("https://api.goclaw.ai", "https://goclaw.ai")
    )

    if is_mock:
        return {
            "ok": True,
            "message": "Kết nối GoClaw thành công (Chế độ Mock)",
            "details": {
                "mode": "mock",
                "domain": domain,
                "has_api_key": bool(api_key),
                "has_agent_key": bool(agent_key),
            },
        }

    domain_clean = _base_url(domain)

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if agent_key:
        headers["x-agent-key"] = agent_key

    endpoints_to_try = ["/health", "/v1/models", "/api/ping", "/"]
    last_error: Exception | None = None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for endpoint in endpoints_to_try:
                try:
                    resp = await client.get(f"{domain_clean}{endpoint}", headers=headers)
                    if resp.status_code in (200, 204):
                        return {
                            "ok": True,
                            "message": "Kết nối GoClaw thành công",
                            "details": {"status_code": resp.status_code, "endpoint": endpoint},
                        }
                    elif resp.status_code in (401, 403):
                        return {
                            "ok": False,
                            "message": f"Xác thực thất bại: API Key hoặc Agent Key không hợp lệ (mã {resp.status_code})",
                            "details": {"status_code": resp.status_code},
                        }
                except httpx.HTTPError as e:
                    last_error = e

            return {
                "ok": False,
                "message": f"Không kết nối được tới máy chủ GoClaw: {last_error or 'Không có phản hồi'}",
                "details": {"error": str(last_error) if last_error else None},
            }
    except Exception as e:
        return {
            "ok": False,
            "message": f"Lỗi kiểm tra kết nối GoClaw: {e}",
            "details": {"error": str(e)},
        }


async def send_message(
    target: GoClawTarget, *, session_key: str, user_id: uuid.UUID, content: str, media: list[GoClawMedia] | None = None
) -> GoClawReply:
    settings = get_settings()
    if settings.goclaw_mode == "mock":
        files = f" kèm {len(media)} file" if media else ""
        return GoClawReply(
            content=f"(mock {target.agent_name}) Mình đã nhận{files}: {content}",
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
            if media:
                return await _send_with_media(target, session_key=session_key, user_id=user_id, content=content, media=media)
            return await _send_wake(target, session_key=session_key, user_id=user_id, content=content)
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
    content = data["content"]
    if content is not None and not isinstance(content, str):
        raise ValueError("content không phải chuỗi")
    usage = data.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    return GoClawReply(
        content=_clean_text(content) or "",
        session_id=session_key,
        message_id=_clean_text(data.get("run_id"), 255),
        input_tokens=_count(usage.get("prompt_tokens")),
        output_tokens=_count(usage.get("completion_tokens")),
    )


@contextmanager
def _translate_errors(target: GoClawTarget) -> Iterator[None]:
    """Đổi lỗi kết nối và dữ liệu lạ thành GoClawError, không để lộ URL hay chi tiết nội bộ cho user."""
    try:
        yield
    except httpx.HTTPStatusError as e:
        log.warning("GoClaw trả %s cho agent %s: %s", e.response.status_code, target.agent_key, e)
        raise GoClawError(
            f"Agent đang gặp lỗi (mã {e.response.status_code}), vui lòng thử lại",
            retryable=e.response.status_code in (429, 503),
        )
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        log.warning("Không kết nối được GoClaw (agent %s): %s", target.agent_key, e)
        raise GoClawError("Không kết nối được tới agent, vui lòng thử lại", retryable=True)
    except httpx.TimeoutException as e:
        log.warning("GoClaw timeout (agent %s): %s", target.agent_key, e)
        raise GoClawError("Agent phản hồi quá lâu, vui lòng thử lại")
    except (httpx.HTTPError, WebSocketException, OSError) as e:
        log.warning("Không kết nối được GoClaw (agent %s): %s", target.agent_key, e)
        raise GoClawError("Không kết nối được tới agent, vui lòng thử lại")
    except (AttributeError, KeyError, IndexError, TypeError, ValueError) as e:
        log.warning("GoClaw trả dữ liệu không đúng định dạng (agent %s): %r", target.agent_key, e)
        raise GoClawError("Agent trả về dữ liệu không đọc được")


def _http_headers(target: GoClawTarget, user_id: uuid.UUID) -> dict[str, str]:
    headers = {"X-GoClaw-User-Id": str(user_id)}
    if target.api_key:
        headers["Authorization"] = f"Bearer {target.api_key}"
    return headers


async def _send_wake(target: GoClawTarget, *, session_key: str, user_id: uuid.UUID, content: str) -> GoClawReply:
    settings = get_settings()
    url = f"{_base_url(target.base_url)}/v1/agents/{quote(target.agent_key or '', safe='')}/wake"
    body = {"message": content, "session_key": session_key}
    with _translate_errors(target):
        async with httpx.AsyncClient(timeout=settings.goclaw_timeout_seconds) as client:
            resp = await client.post(url, json=body, headers=_http_headers(target, user_id))
            resp.raise_for_status()
            data = resp.json()
        return _parse_reply(data, session_key)


async def _ws_request(ws, request_id: str, method: str, params: dict) -> dict:
    """Gửi một request rồi đợi đúng frame res của nó. Bỏ qua các frame event (trạng thái, chữ đang gõ)."""
    await ws.send(json.dumps({"type": "req", "id": request_id, "method": method, "params": params}))
    while True:
        frame = json.loads(await ws.recv())
        if frame.get("type") != "res" or frame.get("id") != request_id:
            continue
        if not frame.get("ok"):
            error = frame.get("error") or {}
            log.warning("GoClaw từ chối %s: %s", method, error.get("code"))
            raise GoClawError("Agent đang gặp lỗi, vui lòng thử lại")
        return frame.get("payload") or {}


async def _send_with_media(
    target: GoClawTarget, *, session_key: str, user_id: uuid.UUID, content: str, media: list[GoClawMedia]
) -> GoClawReply:
    settings = get_settings()
    base = _base_url(target.base_url)
    with _translate_errors(target):
        items = []
        async with httpx.AsyncClient(timeout=settings.goclaw_timeout_seconds) as client:
            for item in media:
                item.file.seek(0)
                resp = await client.post(
                    f"{base}/v1/media/upload",
                    files={"file": (item.filename, item.file, item.mime_type)},
                    headers=_http_headers(target, user_id),
                )
                resp.raise_for_status()
                items.append({"path": resp.json()["path"], "filename": item.filename})

        ws_url = "ws" + base.removeprefix("http") + "/ws"
        async with websockets.connect(ws_url, max_size=None, open_timeout=30) as ws:
            await _ws_request(ws, "connect", "connect", {"token": target.api_key, "user_id": str(user_id)})
            payload = await _ws_request(
                ws,
                "send",
                "chat.send",
                {"agentId": target.agent_key, "sessionKey": session_key, "message": content, "media": items},
            )
        return _parse_reply(
            {"content": payload["content"], "run_id": payload.get("runId"), "usage": payload.get("usage")}, session_key
        )


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
