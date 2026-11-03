"""Gửi tin kèm file: API, lưu Storage, ghi database. Storage và GoClaw đều được giả lập."""

import uuid
from unittest import mock

import pytest

from app.core.config import get_settings
from app.integrations import goclaw, supabase_storage
from app.services import attachment_service
from tests.conftest import Client, new_user, sql
from tests.test_api import GENERAL, _conversation

PNG = ("anh.png", b"\x89PNG-du-lieu", "image/png")
MP4 = ("video.mp4", b"du-lieu-video", "video/mp4")
PDF = ("tai lieu.pdf", b"%PDF-du-lieu", "application/pdf")


@pytest.fixture
def storage():
    """Storage trong bộ nhớ."""
    saved: dict[str, tuple[bytes, str]] = {}

    async def upload(path, data, mime_type):
        saved[path] = (data, mime_type)

    async def sign(paths):
        return {p: f"https://storage.test/{p}?token=abc" for p in paths}

    async def delete(paths):
        for p in paths:
            saved.pop(p, None)

    with mock.patch.object(supabase_storage, "upload", upload), \
            mock.patch.object(supabase_storage, "sign", sign), \
            mock.patch.object(supabase_storage, "delete", delete):
        yield saved


async def _setup(agents):
    user = await new_user()
    return user, await _conversation(user, agents[GENERAL])


async def _post(user, conv, files, **data):
    async with Client(user) as c:
        return await c.post(
            f"/conversations/{conv['id']}/messages/upload",
            files=[("files", f) for f in files],
            data=data,
        )


async def test_send_files_saves_rows_and_returns_signed_urls(agents, storage):
    user, conv = await _setup(agents)
    r = await _post(user, conv, [PNG, MP4, PDF], content="Viết bài từ các file này")
    assert r.status_code == 201, r.text
    um, am = r.json()["user_message"], r.json()["assistant_message"]
    assert (um["content"], um["content_type"]) == ("Viết bài từ các file này", "file")
    assert (am["status"], am["attachments"]) == ("completed", [])
    assert "kèm 3 file" in am["content"]
    assert [(a["file_name"], a["mime_type"], a["file_size"]) for a in um["attachments"]] == [
        ("anh.png", "image/png", len(PNG[1])),
        ("video.mp4", "video/mp4", len(MP4[1])),
        ("tai lieu.pdf", "application/pdf", len(PDF[1])),
    ]
    assert all(a["url"].startswith("https://storage.test/") for a in um["attachments"])

    rows = await sql("select file_path from message_attachments where message_id = :m", m=um["id"])
    assert {x["file_path"] for x in rows} == set(storage)
    for path in storage:
        # Đường dẫn gắn với user, không chứa tên file do client gửi
        assert path.startswith(f"{user}/{conv['id']}/") and "tai lieu" not in path
    assert PNG[1] in [data for data, _ in storage.values()]

    async with Client(user) as c:
        items = (await c.get(f"/conversations/{conv['id']}/messages")).json()["items"]
    assert len(items[1]["attachments"]) == 3 and items[1]["attachments"][0]["url"]
    assert items[0]["attachments"] == []


@pytest.mark.parametrize(
    "files, expected",
    [([PNG], "image"), ([MP4], "video"), ([PDF], "file"), ([("a.mp3", b"x", "audio/mpeg")], "audio"), ([PNG, MP4], "file")],
)
async def test_content_type_follows_files(agents, storage, files, expected):
    user, conv = await _setup(agents)
    r = await _post(user, conv, files)
    assert r.status_code == 201, r.text
    assert r.json()["user_message"]["content_type"] == expected


async def test_files_without_text_are_allowed_and_name_conversation(agents, storage):
    user, conv = await _setup(agents)
    r = await _post(user, conv, [MP4], content="   ")
    assert r.status_code == 201, r.text
    assert r.json()["user_message"]["content"] is None
    async with Client(user) as c:
        assert (await c.get(f"/conversations/{conv['id']}")).json()["title"] == "video.mp4"


async def test_goclaw_receives_media_outside_any_transaction(agents, storage):
    from app.db.supabase import get_engine

    user, conv = await _setup(agents)
    seen = {}

    async def fake_send(target, **kwargs):
        kwargs["media"][0].file.seek(0)
        seen.update(kwargs, connections=get_engine().sync_engine.pool.checkedout(), body=kwargs["media"][0].file.read())
        return goclaw.GoClawReply(content="Đã xem", session_id=kwargs["session_key"], message_id="run-1")

    with mock.patch.object(goclaw, "send_message", side_effect=fake_send):
        r = await _post(user, conv, [PNG], content="Xem giúp")
    assert r.json()["assistant_message"]["content"] == "Đã xem"
    assert seen["content"] == "Xem giúp" and seen["body"] == PNG[1]
    assert (seen["media"][0].filename, seen["media"][0].mime_type) == ("anh.png", "image/png")
    assert seen["connections"] == 0


async def test_rejects_invalid_requests_without_storing(agents, storage):
    user, conv = await _setup(agents)
    assert (await _post(user, conv, [], content="không có file")).status_code == 422
    assert (await _post(user, conv, [("rong.png", b"", "image/png")])).status_code == 422
    assert (await _post(user, conv, [PNG], idempotency_key="khong-phai-uuid")).status_code == 422
    assert (await _post(user, conv, [PNG] * 6)).status_code in (400, 422)
    with mock.patch.object(attachment_service, "MAX_FILE_BYTES", 3):
        assert (await _post(user, conv, [PNG])).status_code == 413
    with mock.patch.object(attachment_service, "MAX_REQUEST_BYTES", 10):
        assert (await _post(user, conv, [PNG])).status_code == 413
    assert storage == {}


async def test_auth_and_ownership(agents, storage):
    user, conv = await _setup(agents)
    other = await new_user()
    assert (await _post(other, conv, [PNG])).status_code == 404
    async with Client() as c:
        r = await c.post(f"/conversations/{conv['id']}/messages/upload", files=[("files", PNG)])
    assert r.status_code == 401
    assert storage == {}


async def test_rejected_file_type_returns_415_and_cleans_earlier_files(agents, storage):
    user, conv = await _setup(agents)
    real_upload = supabase_storage.upload

    async def reject_exe(path, data, mime_type):
        if mime_type == "application/x-msdownload":
            raise supabase_storage.StorageError("Loại file không được hỗ trợ", rejected=True)
        await real_upload(path, data, mime_type)

    with mock.patch.object(supabase_storage, "upload", reject_exe):
        r = await _post(user, conv, [PNG, ("x.exe", b"MZ", "application/x-msdownload")])
    assert r.status_code == 415
    assert storage == {}
    assert await sql("select id from messages where conversation_id = :c", c=conv["id"]) == []


async def test_storage_down_returns_503_and_saves_no_message(agents, storage):
    user, conv = await _setup(agents)

    async def down(path, data, mime_type):
        raise supabase_storage.StorageError("Không lưu được file, vui lòng thử lại")

    with mock.patch.object(supabase_storage, "upload", down):
        assert (await _post(user, conv, [PNG])).status_code == 503
    assert await sql("select id from messages where conversation_id = :c", c=conv["id"]) == []


async def test_busy_conversation_rejected_before_uploading(agents, storage):
    user, conv = await _setup(agents)
    await sql(
        "insert into messages (conversation_id, user_id, role, status) values (:c, :u, 'assistant', 'processing')",
        c=conv["id"], u=user,
    )
    assert (await _post(user, conv, [PNG])).status_code == 409
    assert storage == {}
    await sql("update messages set status = 'failed' where conversation_id = :c", c=conv["id"])


async def test_same_idempotency_key_returns_first_result_and_uploads_once(agents, storage):
    user, conv = await _setup(agents)
    key = str(uuid.uuid4())
    first = await _post(user, conv, [PNG], idempotency_key=key)
    second = await _post(user, conv, [PNG], idempotency_key=key)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["user_message"]["id"] == second.json()["user_message"]["id"]
    assert len(second.json()["user_message"]["attachments"]) == 1
    assert len(storage) == 1


async def test_goclaw_failure_keeps_files_and_marks_reply_failed(agents, storage):
    user, conv = await _setup(agents)
    with mock.patch.object(goclaw, "send_message", side_effect=goclaw.GoClawError("Agent phản hồi quá lâu")):
        r = await _post(user, conv, [PNG])
    assert r.status_code == 201
    assert r.json()["assistant_message"]["status"] == "failed"
    assert len(r.json()["user_message"]["attachments"]) == 1 and len(storage) == 1


async def test_messages_still_readable_when_signing_fails(agents, storage):
    user, conv = await _setup(agents)
    await _post(user, conv, [PNG])

    async def down(paths):
        raise supabase_storage.StorageError("Không tạo được đường dẫn xem file")

    with mock.patch.object(supabase_storage, "sign", down):
        async with Client(user) as c:
            r = await c.get(f"/conversations/{conv['id']}/messages")
    assert r.status_code == 200
    assert r.json()["items"][1]["attachments"][0]["url"] is None


async def test_filename_cannot_escape_or_inject(agents, storage):
    user, conv = await _setup(agents)
    r = await _post(user, conv, [("../../etc/passwd.png", b"x", "image/png")])
    assert r.status_code == 201, r.text
    assert r.json()["user_message"]["attachments"][0]["file_name"] == "passwd.png"
    assert all(".." not in path for path in storage)
    assert attachment_service._safe_name("C:\\tmp\\pass\x07wd..png") == "passwd.png"
    assert attachment_service._safe_name("\x00") == "file"


async def test_plain_text_endpoint_unchanged(agents):
    user, conv = await _setup(agents)
    async with Client(user) as c:
        r = await c.post(f"/conversations/{conv['id']}/messages", json={"content": "alo"})
    assert r.status_code == 201
    um = r.json()["user_message"]
    assert (um["content_type"], um["attachments"]) == ("text", [])


async def test_storage_not_configured_is_clear_error(agents):
    user, conv = await _setup(agents)
    with mock.patch.object(get_settings(), "supabase_secret_key", None):
        assert (await _post(user, conv, [PNG])).status_code == 503
