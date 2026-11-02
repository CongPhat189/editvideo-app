"""Các lỗi đã tìm được khi review, mỗi test ứng với một lỗi."""

import json
import uuid
from contextlib import contextmanager
from unittest import mock

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.db.supabase import get_engine
from app.integrations import goclaw
import manage
from tests.conftest import Client, new_user, sql
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


async def _set_agent(agent_id, *, key=None, domain="https://goclaw.test"):
    await sql("update agents set key = :k, domain = :d where id = :i", k=key, d=domain, i=agent_id)


async def _reset_agent(agent_id):
    await _set_agent(agent_id, domain="https://REPLACE_ME.goclaw.local")


async def test_openai_request_shape_and_no_db_connection_held(agents):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    await _set_agent(agents[GENERAL], key=encrypt_secret("sk-test-123"))
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        seen["headers"] = request.headers
        seen["db_connections_in_use"] = get_engine().sync_engine.pool.checkedout()
        return ok_reply(request)

    try:
        with openai_mode(handler):
            async with Client(user) as c:
                r = await _send(c, conv["id"], "alo")
    finally:
        await _reset_agent(agents[GENERAL])
    am = r.json()["assistant_message"]
    assert (am["status"], am["content"]) == ("completed", "Chào bạn!")
    assert am["metadata"] == {"model": "gpt-x", "input_tokens": 11, "output_tokens": 3}
    assert seen["url"] == "https://goclaw.test/v1/chat/completions"
    assert seen["body"]["model"] == "default"
    assert seen["headers"]["x-openclaw-session-key"] == conv["id"]
    assert seen["headers"]["authorization"] == "Bearer sk-test-123"  # đã giải mã trước khi gửi
    assert seen["db_connections_in_use"] == 0  # không giữ kết nối/transaction lúc chờ GoClaw


def test_manage_agent_stores_ciphertext_and_rejects_bad_input():
    name = f"agent-{uuid.uuid4().hex[:8]}"
    with mock.patch("getpass.getpass", return_value="sk-bi-mat"):
        assert manage.agent(name, "https://goclaw.test", True) == 0
    sync = create_engine(get_settings().sqlalchemy_url)

    def stored():
        with sync.connect() as c:
            return c.execute(text("select key from agents where name = :n"), {"n": name}).scalar()

    first = stored()
    assert "sk-bi-mat" not in first and decrypt_secret(first) == "sk-bi-mat"
    with mock.patch("getpass.getpass", return_value="   "):
        assert manage.agent(name, None, True) == 1
    assert stored() == first  # key trống không ghi đè key thật
    assert manage.agent(name, "http://goclaw.test", False) == 1
    assert manage.agent(name, "http://goclaw.test", False, allow_http=True) == 0
    with sync.begin() as c:
        c.execute(text("delete from agents where name = :n"), {"n": name})
    sync.dispose()


async def test_manage_set_password_changes_login():
    assert manage.set_password("khong-phai-so") == 1
    phone = "+84999999990"
    await sql("delete from users where phone = :p", p=phone)
    with mock.patch("getpass.getpass", return_value="ngan"):
        assert manage.set_password(phone) == 1
    with mock.patch("getpass.getpass", return_value="mat-khau-hop-le"):
        assert manage.set_password(phone) == 1  # số chưa có tài khoản
    async with Client() as c:
        r = await c.post("/auth/register", json={"phone": phone, "password": "mat-khau-cu-123", "full_name": "A"})
        old = r.json()
        with mock.patch("getpass.getpass", return_value="mat-khau-hop-le"):
            assert manage.set_password("0999999990") == 0
        assert (await c.post("/auth/login", json={"phone": phone, "password": "mat-khau-cu-123"})).status_code == 401
        assert (await c.post("/auth/login", json={"phone": phone, "password": "mat-khau-hop-le"})).status_code == 200
    async with Client(token=old["access_token"]) as c:
        assert (await c.get("/me")).status_code == 401


@pytest.mark.parametrize(
    "reply, status_expected",
    [
        ({"choices": [{"message": {"content": [{"type": "text", "text": "phần 1 "}, {"type": "text", "text": "phần 2"}]}}]}, "completed"),
        ({"choices": [{"message": {"content": "có\x00NUL"}}], "model": "m\x00", "id": "i\x00", "usage": "lạ"}, "completed"),
        ({"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": "nhiều", "completion_tokens": -1}}, "completed"),
        (["không phải object"], "failed"),
        ({"choices": [{"message": {"content": 123}}]}, "failed"),
    ],
)
async def test_odd_goclaw_replies_never_stick(agents, reply, status_expected):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    with openai_mode(lambda req: httpx.Response(200, json=reply)):
        async with Client(user) as c:
            r = await _send(c, conv["id"], "alo")
    assert r.status_code == 201, r.text
    assert r.json()["assistant_message"]["status"] == status_expected


async def test_undecryptable_key_does_not_block_conversation(agents):
    """Key hỏng -> báo 503, không để lại câu trả lời kẹt 'processing'."""
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    await _set_agent(agents[GENERAL], key="khong-phai-ban-ma-hoa")
    try:
        with openai_mode(ok_reply):
            async with Client(user) as c:
                r = await _send(c, conv["id"], "alo")
        assert r.status_code == 503
        assert await sql("select status from messages where conversation_id = :c", c=conv["id"]) == []
    finally:
        await _reset_agent(agents[GENERAL])
    async with Client(user) as c:
        assert (await _send(c, conv["id"], "giờ được chưa")).status_code == 201


async def test_goclaw_errors_do_not_leak_internal_url(agents):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    await _set_agent(agents[GENERAL], domain="http://10.0.0.5:8080")
    cases = [
        lambda req: httpx.Response(401, json={"error": "bad key"}),
        lambda req: (_ for _ in ()).throw(httpx.ConnectError("connection refused to http://10.0.0.5:8080")),
        lambda req: httpx.Response(200, json={"unexpected": True}),
    ]
    try:
        for handler in cases:
            with openai_mode(handler):
                async with Client(user) as c:
                    r = await _send(c, conv["id"], "alo")
            am = r.json()["assistant_message"]
            assert am["status"] == "failed"
            assert "10.0.0.5" not in am["error_message"] and "http" not in am["error_message"]
    finally:
        await _reset_agent(agents[GENERAL])


def test_models_match_database_and_unmodelled_tables_are_never_dropped():
    """Models khớp database, và bảng tạo ngoài Python (Dashboard, extension) không bị sinh lệnh drop_table."""
    sync = create_engine(get_settings().sqlalchemy_url)
    with sync.begin() as c:
        c.execute(text("create table public.zz_made_in_dashboard (id int primary key)"))
    try:
        command.check(Config("alembic.ini"))  # ném AutogenerateDiffsDetected nếu có khác biệt
    finally:
        with sync.begin() as c:
            c.execute(text("drop table public.zz_made_in_dashboard"))
        sync.dispose()


async def test_schema_is_exactly_the_diagram():
    rows = await sql("""
        select table_name, array_agg(column_name::text order by column_name) cols
          from information_schema.columns
         where table_schema = 'public' and table_name <> 'alembic_version' and table_name <> 'zz_made_in_dashboard'
         group by table_name
    """)
    tables = {r["table_name"]: set(r["cols"]) for r in rows}
    assert tables == {
        "users": {"id", "full_name", "phone", "password_hash", "avatar_url", "status", "created_at", "updated_at",
                  "last_login_at", "deleted_at"},
        "user_settings": {"id", "user_id", "theme", "language", "timezone", "notification_enabled", "settings_json",
                          "created_at", "updated_at"},
        "agents": {"id", "name", "key", "domain", "created_at", "updated_at"},
        "conversations": {"id", "user_id", "agent_id", "title", "goclaw_session_id", "status", "message_count",
                          "last_message_at", "pinned_at", "created_at", "updated_at", "archived_at", "deleted_at"},
        "messages": {"id", "conversation_id", "user_id", "role", "content", "content_type", "goclaw_message_id",
                     "reply_to_message_id", "status", "idempotency_key", "error_message", "metadata", "favorited_at",
                     "created_at", "updated_at"},
        "message_attachments": {"id", "message_id", "file_name", "file_path", "file_url", "mime_type", "file_size",
                                "created_at"},
        "scheduled_tasks": {"id", "user_id", "conversation_id", "agent_id", "task_name", "task_type", "payload",
                            "scheduled_at", "timezone", "recurrence_rule", "status", "attempts", "max_attempts",
                            "next_retry_at", "last_error", "locked_by", "locked_at", "executed_at", "completed_at",
                            "created_at", "updated_at"},
        "scheduled_task_logs": {"id", "task_id", "attempt_number", "status", "request_payload", "response_payload",
                                "error_message", "started_at", "finished_at", "created_at"},
    }


async def test_all_objects_closed_to_data_api():
    tables = await sql("""
        select c.relname, c.relrowsecurity rls,
               has_table_privilege('anon', c.oid, 'select,insert,update,delete') anon,
               has_table_privilege('authenticated', c.oid, 'select,insert,update,delete') auth
          from pg_class c
         where c.relnamespace = 'public'::regnamespace and c.relkind = 'r'
    """)
    assert len(tables) == 9  # 8 bảng + alembic_version
    for r in tables:
        assert r["rls"] and not r["anon"] and not r["auth"], r["relname"]
    assert await sql("select viewname from pg_views where schemaname = 'public'") == []
    functions = await sql("""
        select p.proname from pg_proc p
         where p.pronamespace = 'public'::regnamespace
           and (has_function_privilege('anon', p.oid, 'execute') or has_function_privilege('authenticated', p.oid, 'execute'))
    """)
    assert functions == []
    assert await sql("select pubname from pg_publication_tables where schemaname = 'public'") == []


def test_db_errors_do_not_log_parameters():
    assert get_engine().sync_engine.hide_parameters is True


async def test_composite_fk_blocks_message_in_other_users_conversation(agents):
    owner, other = await new_user(), await new_user()
    conv = await _conversation(owner, agents[GENERAL])
    try:
        await sql("insert into messages (conversation_id, user_id, role) values (:c, :u, 'user')", c=conv["id"], u=other)
    except Exception as e:
        assert "messages_conversation_owner_fk" in str(e)
    else:
        raise AssertionError("phải bị khóa ngoại chặn")


async def test_title_set_elsewhere_during_reply_is_kept(agents):
    """Đổi tên trên máy khác lúc agent đang trả lời -> không bị tên tự động đè."""
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    real = goclaw.send_message

    async def rename_meanwhile(*args, **kwargs):
        await sql("update conversations set title = 'Tên từ iPad' where id = :c", c=conv["id"])
        return await real(*args, **kwargs)

    with mock.patch.object(goclaw, "send_message", side_effect=rename_meanwhile):
        async with Client(user) as c:
            await _send(c, conv["id"], "tin đầu tiên")
            detail = (await c.get(f"/conversations/{conv['id']}")).json()
    assert detail["title"] == "Tên từ iPad"


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
    user = await new_user()
    async with Client(user) as c:
        for bad in ["UTC+7", "+07", "ICT", "asia/ho_chi_minh", "XYZ-7"]:
            assert (await c.patch("/me/settings", json={"timezone": bad})).status_code == 422, bad
        for good in ["Asia/Ho_Chi_Minh", "UTC", "Europe/London"]:
            assert (await c.patch("/me/settings", json={"timezone": good})).status_code == 200, good


