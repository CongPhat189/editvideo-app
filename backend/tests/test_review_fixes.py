"""Test cho các lỗi tìm được khi review (mỗi test ứng với một lỗi)."""

import json
import uuid
from contextlib import contextmanager
from unittest import mock

import httpx
from alembic import command
from alembic.config import Config

from app import goclaw
from app.config import get_settings
from app.db import engine
from tests.conftest import Client, make_token, new_user, sql
from tests.test_api import GENERAL, _conversation, _send


@contextmanager
def openai_mode(handler):
    """GOCLAW_MODE=openai, mọi request HTTP tới GoClaw đi vào handler (không ra mạng)."""
    real_client = httpx.AsyncClient

    def fake_client(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    with mock.patch.object(get_settings(), "goclaw_mode", "openai"), \
            mock.patch.object(goclaw.httpx, "AsyncClient", fake_client):
        yield


def ok_reply(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={
        "id": "chatcmpl-1", "model": "gpt-x",
        "choices": [{"message": {"role": "assistant", "content": "Chào bạn!"}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 3},
    })


async def test_openai_request_shape_and_no_db_connection_held(agents):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["headers"] = request.headers
        seen["db_connections_in_use"] = engine.sync_engine.pool.checkedout()
        return ok_reply(request)

    with openai_mode(handler):
        async with Client(user) as c:
            r = await _send(c, conv["id"], "alo")
    am = r.json()["assistant_message"]
    assert (am["status"], am["content"], am["input_tokens"], am["output_tokens"]) == ("completed", "Chào bạn!", 11, 3)
    assert seen["body"]["model"] == "REPLACE_ME_general_assistant"
    assert seen["headers"]["x-openclaw-session-key"] == conv["id"]
    assert seen["db_connections_in_use"] == 0  # lỗi #2: không giữ kết nối/transaction lúc chờ GoClaw


async def test_vault_failure_does_not_block_conversation(agents):
    """Lỗi #1: đọc Vault lỗi -> báo 503, không để lại câu trả lời kẹt 'processing'."""
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    await sql("update goclaw_workspaces set api_key_secret_id = gen_random_uuid() where name = 'default'")
    try:
        with openai_mode(ok_reply):
            async with Client(user) as c:
                r = await _send(c, conv["id"], "alo")
        assert r.status_code == 503
        assert await sql("select status from messages where conversation_id = :c", c=conv["id"]) == []
    finally:
        await sql("update goclaw_workspaces set api_key_secret_id = null where name = 'default'")
    async with Client(user) as c:
        assert (await _send(c, conv["id"], "giờ được chưa")).status_code == 201


async def test_vault_key_is_sent_as_bearer(agents):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    secret_id = uuid.uuid4()
    await sql("create schema if not exists vault")
    await sql("create table vault.decrypted_secrets (id uuid primary key, decrypted_secret text)")
    await sql("insert into vault.decrypted_secrets values (:id, 'sk-test-123')", id=secret_id)
    await sql("update goclaw_workspaces set api_key_secret_id = :id where name = 'default'", id=secret_id)
    seen = {}
    try:
        with openai_mode(lambda req: (seen.update(auth=req.headers.get("authorization")), ok_reply(req))[1]):
            async with Client(user) as c:
                assert (await _send(c, conv["id"], "alo")).status_code == 201
        assert seen["auth"] == "Bearer sk-test-123"
    finally:
        await sql("update goclaw_workspaces set api_key_secret_id = null where name = 'default'")
        await sql("drop schema vault cascade")


async def test_goclaw_errors_do_not_leak_internal_url(agents):
    """Lỗi #3: thông báo lỗi trả cho user không chứa base_url."""
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    cases = [
        lambda req: httpx.Response(401, json={"error": "bad key"}),
        lambda req: (_ for _ in ()).throw(httpx.ConnectError("connection refused to http://10.0.0.5:8080")),
        lambda req: httpx.Response(200, json={"unexpected": True}),
    ]
    for handler in cases:
        with openai_mode(handler):
            async with Client(user) as c:
                r = await _send(c, conv["id"], "alo")
        am = r.json()["assistant_message"]
        assert am["status"] == "failed"
        assert "REPLACE_ME" not in am["error_message"] and "10.0.0.5" not in am["error_message"]
        assert "http" not in am["error_message"]


def test_autogenerate_never_drops_unmodelled_tables():
    """Lỗi #4: bảng tạo ngoài Python (Dashboard, extension) không bị sinh lệnh drop_table."""
    from sqlalchemy import create_engine, text

    sync = create_engine(get_settings().sqlalchemy_url)
    with sync.begin() as c:
        c.execute(text("create table public.zz_made_in_dashboard (id int primary key)"))
    try:
        command.check(Config("alembic.ini"))  # ném AutogenerateDiffsDetected nếu có khác biệt
    finally:
        with sync.begin() as c:
            c.execute(text("drop table public.zz_made_in_dashboard"))
        sync.dispose()


async def test_title_set_elsewhere_during_reply_is_kept(agents):
    """Lỗi #5: đổi tên trên máy khác lúc agent đang trả lời -> không bị tên tự động đè."""
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    real = goclaw.send_message

    async def rename_meanwhile(*args, **kwargs):
        await sql("update conversations set title = 'Tên từ iPad', title_source = 'user' where id = :c", c=conv["id"])
        return await real(*args, **kwargs)

    with mock.patch.object(goclaw, "send_message", side_effect=rename_meanwhile):
        async with Client(user) as c:
            await _send(c, conv["id"], "tin đầu tiên")
            detail = (await c.get(f"/conversations/{conv['id']}")).json()
    assert (detail["title"], detail["title_source"]) == ("Tên từ iPad", "user")


async def test_reply_closed_by_stale_recovery_stays_failed(agents):
    """Agent trả lời quá trễ, sau khi đã bị đánh dấu failed -> không lật lại thành completed."""
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    real = goclaw.send_message

    async def closed_meanwhile(*args, **kwargs):
        await sql("update messages set status = 'failed' where conversation_id = :c and role = 'assistant'",
                  c=conv["id"])
        return await real(*args, **kwargs)

    with mock.patch.object(goclaw, "send_message", side_effect=closed_meanwhile):
        async with Client(user) as c:
            r = await _send(c, conv["id"], "alo")
    assert r.json()["assistant_message"]["status"] == "failed"


async def test_blank_content_and_titles_rejected(agents):
    """Lỗi #6."""
    user = await new_user()
    async with Client(user) as c:
        r = await c.post("/conversations", json={"agent_id": str(agents[GENERAL]), "title": "  Kế hoạch  "})
        conv = r.json()
        assert conv["title"] == "Kế hoạch"
        assert (await c.post("/conversations", json={"agent_id": str(agents[GENERAL]), "title": "   "})).status_code == 422
        assert (await c.patch(f"/conversations/{conv['id']}", json={"title": "   "})).status_code == 422
        assert (await _send(c, conv["id"], "   \n  ")).status_code == 422
        assert (await c.patch("/me", json={"full_name": "   "})).status_code == 422
        r = await _send(c, conv["id"], "  dòng 1\n  dòng 2")
        assert r.json()["user_message"]["content"] == "  dòng 1\n  dòng 2"  # giữ nguyên nội dung


async def test_only_iana_timezones():
    """Lỗi #7: 'UTC+7' theo POSIX là UTC-7 -> từ chối; chỉ nhận tên IANA."""
    user = await new_user()
    async with Client(user) as c:
        for bad in ["UTC+7", "+07", "ICT", "asia/ho_chi_minh", "XYZ-7"]:
            assert (await c.patch("/me/settings", json={"timezone": bad})).status_code == 422, bad
        for good in ["Asia/Ho_Chi_Minh", "UTC", "Europe/London"]:
            assert (await c.patch("/me/settings", json={"timezone": good})).status_code == 200, good


async def test_token_hardening():
    user = await new_user()
    async with Client(token=make_token(user, exp_in=None)) as c:  # thiếu exp
        assert (await c.get("/me")).status_code == 401
    async with Client(token=make_token(user, is_anonymous=True)) as c:
        assert (await c.get("/me")).status_code == 403


async def test_avatar_path_must_be_a_file_in_own_folder():
    user = await new_user()
    async with Client(user) as c:
        for bad in [f"{user}/../{uuid.uuid4()}/a.jpg", f"{user}/sub/a.jpg", f"{user}/", f"{user}/.hidden"]:
            assert (await c.patch("/me", json={"avatar_path": bad})).status_code == 422, bad
        assert (await c.patch("/me", json={"avatar_path": f"{user}/{uuid.uuid4()}.jpg"})).status_code == 200
        assert (await c.patch("/me", json={"avatar_path": None})).json()["avatar_path"] is None
