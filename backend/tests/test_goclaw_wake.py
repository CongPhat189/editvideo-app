"""Client GoClaw: gọi đúng /wake, tách session theo conversation, không lộ chi tiết nội bộ khi lỗi."""

import asyncio
import io
import json
import uuid
from unittest import mock

import httpx
import pytest
import websockets
from websockets.exceptions import ConnectionClosedError

from app.core.config import get_settings
from app.core.crypto import encrypt_secret
from app.integrations import goclaw, supabase_storage
from app.models import Agent

USER_ID = uuid.uuid4()
TARGET = goclaw.GoClawTarget("Facebook Agent", "facebook", "https://goclaw.test/", "goclaw_secret")


def _send(handler, target=TARGET):
    real_client = httpx.AsyncClient

    def fake_client(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    with mock.patch.object(get_settings(), "goclaw_mode", "live"), \
            mock.patch.object(goclaw.httpx, "AsyncClient", fake_client):
        return asyncio.run(goclaw.send_message(target, session_key="s-1", user_id=USER_ID, content="alo"))


def test_request_shape_and_reply_parsing():
    seen = {}

    def handler(request):
        seen.update(url=str(request.url), headers=request.headers, body=json.loads(request.content))
        return httpx.Response(200, json={
            "content": "Chào bạn!", "run_id": "run-1", "usage": {"prompt_tokens": 11, "completion_tokens": 3},
        })

    reply = _send(handler)
    assert seen["url"] == "https://goclaw.test/v1/agents/facebook/wake"
    assert seen["headers"]["authorization"] == "Bearer goclaw_secret"
    assert seen["headers"]["x-goclaw-user-id"] == str(USER_ID)
    assert seen["body"] == {"message": "alo", "session_key": "s-1"}
    assert (reply.content, reply.message_id, reply.session_id) == ("Chào bạn!", "run-1", "s-1")
    assert (reply.input_tokens, reply.output_tokens) == (11, 3)


def test_domain_without_scheme_gets_https():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"content": "ok"})

    _send(handler, goclaw.GoClawTarget("A", "facebook", "goclaw.test", None))
    assert seen["url"] == "https://goclaw.test/v1/agents/facebook/wake"


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(401, json={"error": "bad key goclaw_secret"}),
        lambda request: httpx.Response(200, json={"unexpected": True}),
        lambda request: httpx.Response(200, json=["không phải object"]),
        lambda request: httpx.Response(200, json={"content": 123}),
        lambda request: (_ for _ in ()).throw(httpx.ConnectError("refused http://10.0.0.5:8080")),
    ],
)
def test_errors_do_not_leak_internal_details(handler):
    with pytest.raises(goclaw.GoClawError) as e:
        _send(handler)
    assert "http" not in str(e.value) and "goclaw_secret" not in str(e.value)


def test_session_key_is_separate_per_conversation():
    first, second = uuid.uuid4(), uuid.uuid4()
    assert goclaw.session_key_for(TARGET, first) == f"agent:facebook:app:direct:{first}"
    assert goclaw.session_key_for(TARGET, first) != goclaw.session_key_for(TARGET, second)


def _agent(**kwargs):
    return Agent(id=uuid.uuid4(), name="A", domain="https://goclaw.test", **kwargs)


def test_resolve_target_decrypts_both_keys_in_live_mode():
    agent = _agent(api_key=encrypt_secret("goclaw_secret"), agent_key=encrypt_secret("facebook"))
    with mock.patch.object(get_settings(), "goclaw_mode", "live"):
        target = goclaw.resolve_target(agent)
    assert (target.api_key, target.agent_key) == ("goclaw_secret", "facebook")


def test_resolve_target_requires_agent_key_in_live_mode():
    with mock.patch.object(get_settings(), "goclaw_mode", "live"), pytest.raises(goclaw.GoClawError):
        goclaw.resolve_target(_agent(api_key=encrypt_secret("goclaw_secret")))


def test_mock_mode_needs_no_keys():
    target = goclaw.resolve_target(_agent())
    conversation_id = uuid.uuid4()
    assert goclaw.session_key_for(target, conversation_id) == str(conversation_id)


# ---------------------------------------------------------------- tin kèm file
class _FakeWebSocket:
    """GoClaw giả: trả event trước, rồi mới đến res đúng id."""

    def __init__(self, chat_frame=None, connect_frame=None):
        self.sent, self._queue = [], []
        self._chat_frame = chat_frame or {
            "ok": True,
            "payload": {"content": "Ảnh màu đỏ", "runId": "run-9", "usage": {"prompt_tokens": 2, "completion_tokens": 5}},
        }
        self._connect_frame = connect_frame or {"ok": True, "payload": {}}

    async def send(self, raw):
        frame = json.loads(raw)
        self.sent.append(frame)
        template = self._connect_frame if frame["method"] == "connect" else self._chat_frame
        self._queue.append({"type": "event", "event": "agent", "payload": {}})
        self._queue.append({"type": "res", "id": "khac", "ok": False})
        self._queue.append({"type": "res", "id": frame["id"], **template})

    async def recv(self):
        return json.dumps(self._queue.pop(0))


class _FakeConnect:
    def __init__(self, ws):
        self.ws, self.url = ws, None

    def __call__(self, url, **kwargs):
        self.url = url
        return self

    async def __aenter__(self):
        return self.ws

    async def __aexit__(self, *exc):
        return False


def _send_media(handler, ws, target=TARGET):
    real_client = httpx.AsyncClient
    connect = _FakeConnect(ws)

    def fake_client(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    media = [goclaw.GoClawMedia("anh.png", "image/png", io.BytesIO(b"du-lieu-anh"))]
    with mock.patch.object(get_settings(), "goclaw_mode", "live"), \
            mock.patch.object(goclaw.httpx, "AsyncClient", fake_client), \
            mock.patch.object(goclaw.websockets, "connect", connect):
        reply = asyncio.run(goclaw.send_message(target, session_key="s-1", user_id=USER_ID, content="alo", media=media))
    return reply, connect


def _upload_ok(request):
    return httpx.Response(200, json={"path": "/tmp/ws_upload_1.png", "mime_type": "image/png", "filename": "anh.png"})


def test_media_uploads_then_sends_over_websocket():
    seen = {}

    def handler(request):
        seen.update(url=str(request.url), headers=request.headers, body=request.content)
        return _upload_ok(request)

    ws = _FakeWebSocket()
    reply, connect = _send_media(handler, ws)
    assert seen["url"] == "https://goclaw.test/v1/media/upload"
    assert seen["headers"]["authorization"] == "Bearer goclaw_secret"
    assert seen["headers"]["x-goclaw-user-id"] == str(USER_ID)
    assert b"du-lieu-anh" in seen["body"] and b'filename="anh.png"' in seen["body"]
    assert connect.url == "wss://goclaw.test/ws"

    login, chat = ws.sent
    assert (login["method"], login["params"]) == ("connect", {"token": "goclaw_secret", "user_id": str(USER_ID)})
    assert chat["method"] == "chat.send"
    assert chat["params"] == {
        "agentId": "facebook",
        "sessionKey": "s-1",
        "message": "alo",
        "media": [{"path": "/tmp/ws_upload_1.png", "filename": "anh.png"}],
    }
    assert (reply.content, reply.message_id, reply.input_tokens, reply.output_tokens) == ("Ảnh màu đỏ", "run-9", 2, 5)


def test_http_domain_uses_plain_websocket():
    target = goclaw.GoClawTarget("A", "facebook", "http://10.0.0.5:8080/", "k")
    _, connect = _send_media(_upload_ok, _FakeWebSocket(), target)
    assert connect.url == "ws://10.0.0.5:8080/ws"


@pytest.mark.parametrize(
    "ws",
    [
        _FakeWebSocket(chat_frame={"ok": False, "error": {"code": "INTERNAL", "message": "chi tiết http://10.0.0.5"}}),
        _FakeWebSocket(connect_frame={"ok": False, "error": {"code": "UNAUTHORIZED", "message": "token goclaw_secret"}}),
        _FakeWebSocket(chat_frame={"ok": True, "payload": {"injected": True}}),
    ],
)
def test_media_errors_do_not_leak_details(ws):
    with pytest.raises(goclaw.GoClawError) as e:
        _send_media(_upload_ok, ws)
    assert "http" not in str(e.value) and "goclaw_secret" not in str(e.value)


def test_media_upload_failure_never_opens_websocket():
    ws = _FakeWebSocket()
    with pytest.raises(goclaw.GoClawError):
        _send_media(lambda request: httpx.Response(400, json={"error": "file too large"}), ws)
    assert ws.sent == []


def test_connection_lost_mid_reply_is_not_retryable():
    """Agent có thể đã nhận file và làm xong, gửi lại sẽ thành làm hai lần."""

    class Closing(_FakeWebSocket):
        async def recv(self):
            if self.sent[-1]["method"] == "chat.send":
                raise ConnectionClosedError(None, None)
            return await super().recv()

    with pytest.raises(goclaw.GoClawError) as e:
        _send_media(_upload_ok, Closing())
    assert e.value.retryable is False


# ---------------------------------------------------------------- Supabase Storage
def _storage(handler, coroutine_factory, key="sb_secret_test"):
    real_client = httpx.AsyncClient

    def fake_client(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    with mock.patch.object(get_settings(), "supabase_url", "https://proj.supabase.co/"), \
            mock.patch.object(get_settings(), "supabase_secret_key", key), \
            mock.patch.object(supabase_storage.httpx, "AsyncClient", fake_client):
        return asyncio.run(coroutine_factory())


def test_storage_upload_request_shape():
    seen = {}

    def handler(request):
        seen.update(url=str(request.url), headers=request.headers, body=request.content)
        return httpx.Response(200, json={"Key": "x"})

    _storage(handler, lambda: supabase_storage.upload("u/c/f.png", b"du-lieu", "image/png"))
    assert seen["url"] == "https://proj.supabase.co/storage/v1/object/chat-attachments/u/c/f.png"
    assert seen["headers"]["authorization"] == "Bearer sb_secret_test"
    assert seen["headers"]["apikey"] == "sb_secret_test"
    assert seen["headers"]["content-type"] == "image/png"
    assert seen["headers"]["x-upsert"] == "false"
    assert seen["body"] == b"du-lieu"


@pytest.mark.parametrize(
    "status, body, rejected",
    [
        (400, {"statusCode": "415", "error": "invalid_mime_type"}, True),
        (400, {"statusCode": "413", "error": "Payload too large"}, True),
        (400, {"statusCode": "403", "error": "Unauthorized"}, False),
        (500, {"error": "lỗi"}, False),
    ],
)
def test_storage_upload_errors(status, body, rejected):
    with pytest.raises(supabase_storage.StorageError) as e:
        _storage(lambda request: httpx.Response(status, json=body), lambda: supabase_storage.upload("p", b"x", "image/png"))
    assert e.value.rejected is rejected
    assert "supabase" not in str(e.value) and "sb_secret" not in str(e.value)


def test_storage_sign_builds_full_urls_and_skips_failed_paths():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=[
            {"path": "a.png", "signedURL": "/object/sign/chat-attachments/a.png?token=t", "error": None},
            {"path": "b.png", "signedURL": None, "error": "Not found"},
        ])

    urls = _storage(handler, lambda: supabase_storage.sign(["a.png", "b.png"]))
    assert seen["body"] == {"expiresIn": 3600, "paths": ["a.png", "b.png"]}
    assert urls == {"a.png": "https://proj.supabase.co/storage/v1/object/sign/chat-attachments/a.png?token=t"}


def test_storage_delete_failure_is_only_logged():
    _storage(lambda request: httpx.Response(500), lambda: supabase_storage.delete(["a.png"]))
