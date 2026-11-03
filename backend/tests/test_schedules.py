"""Đặt lịch gửi tin cho agent: API và worker. Gọi trực tiếp các bước của worker, không chờ vòng lặp."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock
from zoneinfo import ZoneInfo

import httpx

from app.core.config import get_settings
from app.core.crypto import encrypt_secret
from app.integrations import goclaw
from app.services import schedule_worker
from tests.conftest import Client, new_user, sql
from tests.test_api import GENERAL, _conversation

VN = ZoneInfo("Asia/Ho_Chi_Minh")


def _future(minutes=60):
    return (datetime.now(VN) + timedelta(minutes=minutes)).replace(tzinfo=None, microsecond=0).isoformat()


async def _setup(agents):
    user = await new_user()
    return user, await _conversation(user, agents[GENERAL])


async def _schedule(user, conv, content="Viết bài cho tôi", **body):
    async with Client(user) as c:
        r = await c.post(
            "/schedules",
            json={"conversation_id": conv["id"], "content": content, "scheduled_at": _future(), **body},
        )
    assert r.status_code == 201, r.text
    return r.json()


async def _make_due(schedule_id):
    await sql("update scheduled_tasks set scheduled_at = now() - interval '1 second' where id = :i", i=schedule_id)


async def _run_worker():
    ids = await schedule_worker.claim_due(50)
    await asyncio.gather(*(schedule_worker.run_task(i) for i in ids))
    return [str(i) for i in ids]


async def _get(user, schedule_id):
    async with Client(user) as c:
        r = await c.get(f"/schedules/{schedule_id}")
    assert r.status_code == 200, r.text
    return r.json()


async def test_time_without_zone_is_read_in_given_timezone(agents):
    user, conv = await _setup(agents)
    local = (datetime.now(VN) + timedelta(days=2)).replace(hour=20, minute=0, second=0, microsecond=0, tzinfo=None)
    s = await _schedule(user, conv, scheduled_at=local.isoformat(timespec="minutes"))
    assert datetime.fromisoformat(s["scheduled_at"]) == local.replace(tzinfo=VN)
    assert s["scheduled_at"].endswith("+07:00")
    assert (s["status"], s["timezone"], s["task_name"]) == ("scheduled", "Asia/Ho_Chi_Minh", "Viết bài cho tôi")

    tokyo = await _schedule(user, conv, scheduled_at=local.isoformat(timespec="minutes"), timezone="Asia/Tokyo")
    assert datetime.fromisoformat(tokyo["scheduled_at"]) == local.replace(tzinfo=ZoneInfo("Asia/Tokyo"))
    await sql("delete from scheduled_tasks where user_id = :u", u=user)


async def test_date_only_is_saved_and_never_sent(agents):
    user, conv = await _setup(agents)
    today = datetime.now(VN).date()
    next_year = today.replace(year=today.year + 1, day=5)
    url, cid = "/schedules", conv["id"]
    async with Client(user) as c:
        iso = await c.post(url, json={"conversation_id": cid, "scheduled_at": next_year.isoformat()})
        vn = await c.post(url, json={"conversation_id": cid, "scheduled_at": next_year.strftime("%d/%m/%Y")})
        same_day = await c.post(url, json={"conversation_id": cid, "scheduled_at": today.isoformat()})
    for r in (iso, vn, same_day):
        assert r.status_code == 201, r.text
    assert iso.json()["scheduled_at"] == vn.json()["scheduled_at"]
    assert iso.json()["scheduled_at"].startswith(f"{next_year.isoformat()}T00:00:00")
    assert iso.json()["task_name"] == f"Lịch {next_year.strftime('%d/%m/%Y')}"
    assert (iso.json()["status"], iso.json()["conversation_id"], iso.json()["content"]) == ("scheduled", cid, None)
    assert iso.json()["agent_id"] == str(agents[GENERAL])

    async with Client(user) as c:
        assert len((await c.get("/schedules")).json()) == 3  # tin báo ngầm không hiện như một lịch

    await _make_due(iso.json()["id"])
    assert iso.json()["id"] not in await _run_worker()
    assert (await _get(user, iso.json()["id"]))["status"] == "scheduled"
    await sql("delete from scheduled_tasks where user_id = :u", u=user)


async def test_date_only_requires_conversation_and_rejects_past(agents):
    user, conv = await _setup(agents)
    cid = conv["id"]
    yesterday = datetime.now(VN).date() - timedelta(days=1)
    async with Client(user) as c:
        past = {"conversation_id": cid, "scheduled_at": yesterday.isoformat()}
        assert (await c.post("/schedules", json=past)).status_code == 422
        assert (await c.post("/schedules", json={"conversation_id": cid})).status_code == 422
        assert (await c.post("/schedules", json={"scheduled_at": _future()})).status_code == 422
        unknown = {"conversation_id": str(uuid.uuid4()), "scheduled_at": _future()}
        assert (await c.post("/schedules", json=unknown)).status_code == 404


async def test_schedule_sends_notice_to_chosen_conversation_in_background(agents):
    user, conv = await _setup(agents)
    other = await _conversation(user, agents[GENERAL])
    day = (datetime.now(VN) + timedelta(days=2)).strftime("%d/%m/%Y")
    async with Client(user) as c:
        r = await c.post("/schedules", json={"conversation_id": conv["id"], "scheduled_at": f"{day} 20:00"})
        assert r.status_code == 201, r.text
        s = r.json()
        # API trả về ngay, chưa gửi gì cho agent
        assert (await c.get(f"/conversations/{conv['id']}/messages")).json()["items"] == []

    claimed = await _run_worker()
    assert s["id"] not in claimed and len(claimed) == 1
    async with Client(user) as c:
        items = (await c.get(f"/conversations/{conv['id']}/messages")).json()["items"]
        assert (await c.get(f"/conversations/{other['id']}/messages")).json()["items"] == []
    # Tin ngầm không hiện, câu trả lời của agent thì có
    assert [(m["role"], m["status"]) for m in items] == [("assistant", "completed")]
    sent = await sql("select id, content from messages where conversation_id = :c and role = 'user'", c=conv["id"])
    assert [x["content"] for x in sent] == [f"hẹn lịch đăng vào {day} 20:00"]
    assert items[0]["reply_to_message_id"] == str(sent[0]["id"])
    async with Client(user) as c:
        hits = (await c.get("/search", params={"q": "hen lich dang"})).json()
        title = (await c.get(f"/conversations/{conv['id']}")).json()["title"]
    assert str(sent[0]["id"]) not in [h["message_id"] for h in hits]
    assert title is None
    assert s["task_name"] == f"Lịch {day} 20:00"
    assert (await _get(user, s["id"]))["status"] == "scheduled"  # lịch vẫn giữ nguyên

    assert await _run_worker() == []  # không gửi lần hai
    await _make_due(s["id"])
    assert await _run_worker() == []  # đến ngày cũng không gửi thêm
    await sql("delete from scheduled_tasks where user_id = :u", u=user)


async def test_platforms_are_saved_and_named_in_notice(agents):
    user, conv = await _setup(agents)
    day = (datetime.now(VN) + timedelta(days=2)).strftime("%d/%m/%Y")
    body = {
        "conversation_id": conv["id"],
        "scheduled_at": f"{day} 20:00",
        "platforms": ["facebook", " TIKTOK ", "Facebook"],
    }
    async with Client(user) as c:
        r = await c.post("/schedules", json=body)
        assert r.status_code == 201, r.text
        assert r.json()["platforms"] == ["Facebook", "TikTok"]
        assert (await c.get("/schedules")).json()[0]["platforms"] == ["Facebook", "TikTok"]
    row = await sql("select platforms, payload from scheduled_tasks where id = :i", i=r.json()["id"])
    assert (row[0]["platforms"], row[0]["payload"]) == (["Facebook", "TikTok"], {})  # nằm ở cột riêng
    await _run_worker()
    sent = await sql("select content, metadata from messages where conversation_id = :c and role = 'user'", c=conv["id"])
    assert [x["content"] for x in sent] == [f"hẹn lịch đăng lên Facebook, TikTok vào {day} 20:00"]
    assert sent[0]["metadata"].get("hidden") is True
    await sql("delete from scheduled_tasks where user_id = :u", u=user)


async def test_schedule_without_platforms_defaults_to_empty(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv)
    assert s["platforms"] == []
    await sql("delete from scheduled_tasks where user_id = :u", u=user)


async def test_invalid_platforms_rejected_and_nothing_saved(agents):
    user, conv = await _setup(agents)
    async with Client(user) as c:
        for platforms in (["Zalo"], ["Facebook", "Zalo"], "Facebook", [1], ["Facebook"] * 6):
            body = {"conversation_id": conv["id"], "scheduled_at": _future(), "platforms": platforms}
            assert (await c.post("/schedules", json=body)).status_code == 422, platforms
    assert await sql("select id from scheduled_tasks where user_id = :u", u=user) == []


async def test_platforms_stay_on_schedule_with_content_and_are_still_sent_at_due_time(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv, content="Viết bài", platforms=["YouTube"])
    assert (s["platforms"], s["content"]) == (["YouTube"], "Viết bài")
    assert s["id"] not in await _run_worker()
    await _make_due(s["id"])
    assert s["id"] in await _run_worker()
    assert (await _get(user, s["id"]))["status"] == "completed"


async def test_notice_without_time_shows_date_only(agents):
    user, conv = await _setup(agents)
    day = (datetime.now(VN) + timedelta(days=2)).strftime("%d/%m/%Y")
    async with Client(user) as c:
        await c.post("/schedules", json={"conversation_id": conv["id"], "scheduled_at": day})
    await _run_worker()
    sent = await sql("select content from messages where conversation_id = :c and role = 'user'", c=conv["id"])
    assert [x["content"] for x in sent] == [f"hẹn lịch đăng vào {day}"]
    await sql("delete from scheduled_tasks where user_id = :u", u=user)


async def test_failed_notice_still_shows_reply_error_and_later_chat_is_normal(agents):
    user, conv = await _setup(agents)
    async with Client(user) as c:
        body = {"conversation_id": conv["id"], "scheduled_at": _future()}
        assert (await c.post("/schedules", json=body)).status_code == 201
    with mock.patch.object(goclaw, "send_message", side_effect=goclaw.GoClawError("Agent phản hồi quá lâu")):
        await _run_worker()
    async with Client(user) as c:
        items = (await c.get(f"/conversations/{conv['id']}/messages")).json()["items"]
        assert [(m["role"], m["status"]) for m in items] == [("assistant", "failed")]
        r = await c.post(f"/conversations/{conv['id']}/messages", json={"content": "tin thường"})
        assert r.status_code == 201, r.text
        items = (await c.get(f"/conversations/{conv['id']}/messages")).json()["items"]
    assert [m["role"] for m in items] == ["assistant", "user", "assistant"]
    assert items[1]["content"] == "tin thường"
    await sql("delete from scheduled_tasks where user_id = :u", u=user)


async def test_notice_retries_when_agent_busy(agents):
    user, conv = await _setup(agents)
    await sql(
        "insert into messages (conversation_id, user_id, role, status) values (:c, :u, 'assistant', 'processing')",
        c=conv["id"], u=user,
    )
    async with Client(user) as c:
        body = {"conversation_id": conv["id"], "scheduled_at": _future()}
        assert (await c.post("/schedules", json=body)).status_code == 201
    await _run_worker()
    rows = await sql("select status from scheduled_tasks where user_id = :u and payload ? 'kind'", u=user)
    assert [x["status"] for x in rows] == ["retrying"]
    await sql("update messages set status = 'failed' where conversation_id = :c", c=conv["id"])
    await sql("delete from scheduled_tasks where user_id = :u", u=user)


async def test_schedule_fails_fast_when_agent_not_configured(agents):
    user, conv = await _setup(agents)
    body = {"conversation_id": conv["id"], "scheduled_at": _future()}
    with mock.patch.object(get_settings(), "goclaw_mode", "live"):
        async with Client(user) as c:
            assert (await c.post("/schedules", json=body)).status_code == 503
    assert await sql("select id from scheduled_tasks where user_id = :u", u=user) == []


async def test_past_time_today_rejected_but_today_date_allowed(agents):
    user, conv = await _setup(agents)
    now = datetime.now(VN)
    earlier = (now - timedelta(minutes=5)).strftime("%d/%m/%Y %H:%M")
    if (now - timedelta(minutes=5)).date() == now.date():
        async with Client(user) as c:
            body = {"conversation_id": conv["id"], "scheduled_at": earlier}
            assert (await c.post("/schedules", json=body)).status_code == 422


async def test_rejects_bad_input(agents):
    user, conv = await _setup(agents)
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    bad = [
        {"scheduled_at": past},
        {"scheduled_at": "31/02/2030"},
        {"scheduled_at": "ngày mai"},
        {"timezone": "Sao/Hoa"},
        {"timezone": "../../etc/passwd"},
        {"content": "   "},
    ]
    async with Client(user) as c:
        for override in bad:
            body = {"conversation_id": conv["id"], "content": "alo", "scheduled_at": _future(), **override}
            assert (await c.post("/schedules", json=body)).status_code == 422, override
    async with Client() as c:
        body = {"conversation_id": conv["id"], "content": "alo", "scheduled_at": _future()}
        assert (await c.post("/schedules", json=body)).status_code == 401


async def test_cannot_touch_other_users_schedule(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv)
    other = await new_user()
    async with Client(other) as c:
        assert (await c.get(f"/schedules/{s['id']}")).status_code == 404
        assert (await c.delete(f"/schedules/{s['id']}")).status_code == 404
        assert (await c.get("/schedules")).json() == []
        body = {"conversation_id": conv["id"], "content": "alo", "scheduled_at": _future()}
        assert (await c.post("/schedules", json=body)).status_code == 404
    await sql("delete from scheduled_tasks where user_id = :u", u=user)


async def test_archived_conversation_rejected(agents):
    user, conv = await _setup(agents)
    async with Client(user) as c:
        await c.patch(f"/conversations/{conv['id']}", json={"archived": True})
        body = {"conversation_id": conv["id"], "content": "alo", "scheduled_at": _future()}
        assert (await c.post("/schedules", json=body)).status_code == 409


async def test_live_mode_rejects_agent_without_agent_key_when_scheduling(agents):
    user, conv = await _setup(agents)
    with mock.patch.object(get_settings(), "goclaw_mode", "live"):
        async with Client(user) as c:
            body = {"conversation_id": conv["id"], "content": "alo", "scheduled_at": _future()}
            assert (await c.post("/schedules", json=body)).status_code == 503


async def test_worker_sends_due_message_once_and_reply_lands_in_conversation(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv, content="Viết bài lúc 8 giờ")
    assert s["id"] not in await _run_worker()  # chưa tới giờ

    await _make_due(s["id"])
    assert s["id"] in await _run_worker()
    done = await _get(user, s["id"])
    assert (done["status"], done["attempts"], done["last_error"]) == ("completed", 1, None)
    assert done["completed_at"] and done["executed_at"]

    async with Client(user) as c:
        items = (await c.get(f"/conversations/{conv['id']}/messages")).json()["items"]
    assert [(m["role"], m["status"]) for m in items] == [("assistant", "completed"), ("user", "completed")]
    assert items[1]["content"] == "Viết bài lúc 8 giờ"
    assert "Viết bài lúc 8 giờ" in items[0]["content"]

    logs = await sql("select attempt_number, status, response_payload from scheduled_task_logs where task_id = :i", i=s["id"])
    assert [(x["attempt_number"], x["status"]) for x in logs] == [(1, "completed")]
    assert logs[0]["response_payload"]["assistant_message_id"] == items[0]["id"]

    assert s["id"] not in await _run_worker()  # không gửi lần hai


async def test_worker_calls_goclaw_with_conversation_session_in_live_mode(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv)
    await _make_due(s["id"])
    await sql(
        "update agents set agent_key = :a, api_key = :k, domain = 'https://goclaw.test' where id = :i",
        a=encrypt_secret("facebook"), k=encrypt_secret("goclaw_secret"), i=agents[GENERAL],
    )
    seen = {}
    real_client = httpx.AsyncClient

    def handler(request):
        seen.update(url=str(request.url), headers=request.headers, body=request.content)
        return httpx.Response(200, json={"content": "Đã làm", "run_id": "run-1"})

    def fake_client(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    try:
        with mock.patch.object(get_settings(), "goclaw_mode", "live"), \
                mock.patch.object(goclaw.httpx, "AsyncClient", fake_client):
            await _run_worker()
    finally:
        await sql(
            "update agents set agent_key = null, api_key = null, domain = 'https://REPLACE_ME.goclaw.local' where id = :i",
            i=agents[GENERAL],
        )
    assert (await _get(user, s["id"]))["status"] == "completed"
    assert seen["url"] == "https://goclaw.test/v1/agents/facebook/wake"
    assert seen["headers"]["x-goclaw-user-id"] == str(user)
    assert f"agent:facebook:app:direct:{conv['id']}".encode() in seen["body"]


async def test_cancel_stops_sending_and_cannot_cancel_twice(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv)
    async with Client(user) as c:
        r = await c.delete(f"/schedules/{s['id']}")
        assert (r.status_code, r.json()["status"]) == (200, "cancelled")
        assert (await c.delete(f"/schedules/{s['id']}")).status_code == 409
    await _make_due(s["id"])
    assert s["id"] not in await _run_worker()


async def test_retries_when_goclaw_surely_did_not_receive(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv)
    await _make_due(s["id"])
    down = goclaw.GoClawError("Không kết nối được tới agent", retryable=True)
    with mock.patch.object(goclaw, "send_message", side_effect=down):
        await _run_worker()
    first = await _get(user, s["id"])
    assert (first["status"], first["attempts"]) == ("retrying", 1)
    assert "kết nối" in first["last_error"]
    assert s["id"] not in await _run_worker()  # chưa tới giờ gửi lại

    await sql("update scheduled_tasks set next_retry_at = now() - interval '1 second' where id = :i", i=s["id"])
    assert s["id"] in await _run_worker()
    second = await _get(user, s["id"])
    assert (second["status"], second["attempts"], second["last_error"]) == ("completed", 2, None)
    logs = await sql("select status from scheduled_task_logs where task_id = :i order by attempt_number", i=s["id"])
    assert [x["status"] for x in logs] == ["failed", "completed"]


async def test_stops_after_max_attempts(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv)
    await _make_due(s["id"])
    await sql("update scheduled_tasks set max_attempts = 1 where id = :i", i=s["id"])
    down = goclaw.GoClawError("Không kết nối được tới agent", retryable=True)
    with mock.patch.object(goclaw, "send_message", side_effect=down):
        await _run_worker()
    assert (await _get(user, s["id"]))["status"] == "failed"


async def test_no_retry_when_agent_may_have_received(agents):
    """Hết giờ chờ: agent có thể đã đăng bài, gửi lại sẽ thành đăng hai lần."""
    user, conv = await _setup(agents)
    s = await _schedule(user, conv)
    await _make_due(s["id"])
    with mock.patch.object(goclaw, "send_message", side_effect=goclaw.GoClawError("Agent phản hồi quá lâu")) as sent:
        await _run_worker()
    done = await _get(user, s["id"])
    assert (done["status"], done["attempts"]) == ("failed", 1)
    assert sent.call_count == 1


async def test_timeout_from_goclaw_is_not_retryable_but_connect_error_is():
    target = goclaw.GoClawTarget("A", "facebook", "https://goclaw.test", None)
    real_client = httpx.AsyncClient

    async def attempt(error):
        def handler(request):
            raise error

        def fake_client(**kwargs):
            return real_client(transport=httpx.MockTransport(handler), **kwargs)

        with mock.patch.object(get_settings(), "goclaw_mode", "live"), \
                mock.patch.object(goclaw.httpx, "AsyncClient", fake_client):
            try:
                await goclaw.send_message(target, session_key="s", user_id=uuid.uuid4(), content="alo")
            except goclaw.GoClawError as e:
                return e.retryable
        raise AssertionError("phải báo lỗi")

    assert await attempt(httpx.ReadTimeout("chậm")) is False
    assert await attempt(httpx.ConnectError("từ chối")) is True


async def test_busy_conversation_is_retried_not_failed(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv)
    await _make_due(s["id"])
    await sql(
        "insert into messages (conversation_id, user_id, role, status) values (:c, :u, 'assistant', 'processing')",
        c=conv["id"], u=user,
    )
    await _run_worker()
    assert (await _get(user, s["id"]))["status"] == "retrying"
    await sql("update messages set status = 'failed' where conversation_id = :c", c=conv["id"])
    await sql("update scheduled_tasks set status = 'cancelled', next_retry_at = null where id = :i", i=s["id"])


async def test_deleted_conversation_fails_with_clear_error(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv)
    await _make_due(s["id"])
    async with Client(user) as c:
        await c.delete(f"/conversations/{conv['id']}")
    await _run_worker()
    done = await _get(user, s["id"])
    assert done["status"] == "failed" and "không còn tồn tại" in done["last_error"]


async def test_stuck_task_is_marked_failed_and_not_resent(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv)
    await _make_due(s["id"])
    assert s["id"] in [str(i) for i in await schedule_worker.claim_due(50)]  # worker chết ngay sau khi nhận
    await schedule_worker.recover_stuck()
    assert (await _get(user, s["id"]))["status"] == "processing"  # chưa quá hạn thì không đụng

    await sql("update scheduled_tasks set locked_at = now() - interval '1 day' where id = :i", i=s["id"])
    await schedule_worker.recover_stuck()
    done = await _get(user, s["id"])
    assert done["status"] == "failed" and "không rõ agent" in done["last_error"]
    assert s["id"] not in await _run_worker()


async def test_two_workers_never_claim_the_same_task(agents):
    user, conv = await _setup(agents)
    s = await _schedule(user, conv)
    await _make_due(s["id"])
    first, second = await asyncio.gather(schedule_worker.claim_due(50), schedule_worker.claim_due(50))
    claimed = [str(i) for i in first + second]
    assert claimed.count(s["id"]) == 1
    await asyncio.gather(*(schedule_worker.run_task(i) for i in first + second))
