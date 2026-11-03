import uuid
from unittest import mock

import jwt

from app.integrations import goclaw
from tests.conftest import Client, make_token, new_user, sql

GENERAL = "Trợ lý chung"
WRITER = "Content Writer"
EDITOR = "Video Editor"


async def _conversation(user, agent_id, **body):
    async with Client(user) as c:
        r = await c.post("/conversations", json={"agent_id": str(agent_id), **body})
        assert r.status_code == 201, r.text
        return r.json()


async def _send(c, conv_id, content, key=None):
    return await c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": content, "idempotency_key": str(key or uuid.uuid4())},
    )


# ---------------------------------------------------------------- auth
async def test_health():
    async with Client() as c:
        r = await c.get("/health")
    assert r.json() == {"status": "ok", "database": "ok"}


async def test_auth_rejects_bad_tokens():
    user = await new_user()
    bad_tokens = {
        "rác": "not-a-jwt",
        "hết hạn": make_token(user, exp_in=-10),
        "không có exp": make_token(user, exp_in=None),
        "sai audience": make_token(user, aud="anon"),
        "sai issuer": make_token(user, iss="https://evil.example"),
        "sai khóa ký": make_token(user, secret="khoa-cua-ke-gian-dai-hon-32-ky-tu-0000"),
        "thuật toán khác": make_token(user, algorithm="HS384"),
        "refresh token dùng gọi API": make_token(user, token_type="refresh"),
        "user không tồn tại": make_token(uuid.uuid4()),
        "sub không phải uuid": make_token("abc"),
        "dấu vân tay mật khẩu cũ": make_token(user, password_hash="hash-cu"),
    }
    async with Client() as c:
        assert (await c.get("/me")).status_code == 401
    for name, token in bad_tokens.items():
        async with Client(token=token) as c:
            assert (await c.get("/me")).status_code == 401, name
    # đủ mọi claim hợp lệ, chỉ khác là không có chữ ký
    claims = jwt.decode(make_token(user), options={"verify_signature": False})
    none_alg = jwt.encode(claims, "", algorithm="none")
    async with Client(token=none_alg) as c:
        assert (await c.get("/me")).status_code == 401


async def test_suspended_user_forbidden():
    user = await new_user()
    await sql("update users set status = 'suspended' where id = :id", id=user)
    async with Client(user) as c:
        assert (await c.get("/me")).status_code == 403
    await sql("update users set status = 'deleted', deleted_at = now() where id = :id", id=user)
    async with Client(user) as c:
        assert (await c.get("/me")).status_code == 401


# ---------------------------------------------------------------- me
async def test_me_profile_and_settings():
    user = await new_user("Nguyễn Văn A")
    async with Client(user) as c:
        me = (await c.get("/me")).json()
        assert me["full_name"] == "Nguyễn Văn A"
        assert me["settings"]["timezone"] == "Asia/Ho_Chi_Minh"

        r = await c.patch("/me", json={"full_name": "  Trần B  "})
        assert r.json()["full_name"] == "Trần B"
        assert (await c.patch("/me", json={"full_name": "   "})).status_code == 422
        assert me["phone"].startswith("+84") and "password_hash" not in me and "phone_verified" not in me
        for bad in ["javascript:alert(1)", "http://a.com/a.jpg", "https://a b.jpg"]:
            assert (await c.patch("/me", json={"avatar_url": bad})).status_code == 422, bad
        r = await c.patch("/me", json={"avatar_url": "https://cdn.abc.com/a.jpg"})
        assert r.json()["avatar_url"] == "https://cdn.abc.com/a.jpg"
        assert (await c.patch("/me", json={"avatar_url": None})).json()["avatar_url"] is None

        assert (await c.patch("/me/settings", json={"timezone": "Asia/Saigonn"})).status_code == 422
        assert (await c.patch("/me/settings", json={"theme": "pink"})).status_code == 422
        r = await c.patch("/me/settings", json={"theme": "dark", "timezone": "Asia/Bangkok"})
        assert r.status_code == 200
        assert (r.json()["theme"], r.json()["timezone"]) == ("dark", "Asia/Bangkok")


# ---------------------------------------------------------------- agents
async def test_agents_list_hides_key_and_domain(agents):
    user = await new_user()
    await sql("update agents set key = 'ban-ma-hoa' where name = :n", n=GENERAL)
    async with Client(user) as c:
        r = await c.get("/agents")
    assert [a["name"] for a in r.json()] == sorted([GENERAL, WRITER, EDITOR])
    assert set(r.json()[0]) == {"id", "name"}
    await sql("update agents set key = null where name = :n", n=GENERAL)


async def test_create_conversation_agent_rules(agents):
    user = await new_user()
    async with Client(user) as c:
        r = await c.post("/conversations", json={"agent_id": str(uuid.uuid4())})
        assert r.status_code == 404
        r = await c.post("/conversations", json={"agent_id": str(agents[EDITOR]), "title": "Kế hoạch"})
        assert r.status_code == 201
        assert r.json()["title"] == "Kế hoạch"


# ---------------------------------------------------------------- conversations
async def test_list_order_pin_archive_delete(agents):
    user = await new_user()
    a = await _conversation(user, agents[GENERAL], title="A")
    b = await _conversation(user, agents[GENERAL], title="B")
    c_ = await _conversation(user, agents[WRITER], title="C")
    async with Client(user) as c:
        await _send(c, a["id"], "tin mới nhất ở A")
        ids = [x["id"] for x in (await c.get("/conversations")).json()]
        assert ids == [a["id"], c_["id"], b["id"]]  # A có tin mới nhất, rồi C, B theo created_at

        await c.patch(f"/conversations/{b['id']}", json={"pinned": True})
        ids = [x["id"] for x in (await c.get("/conversations")).json()]
        assert ids[0] == b["id"]

        r = await c.patch(f"/conversations/{c_['id']}", json={"archived": True})
        assert r.json()["status"] == "archived"
        assert c_["id"] not in [x["id"] for x in (await c.get("/conversations")).json()]
        assert [x["id"] for x in (await c.get("/conversations?status=archived")).json()] == [c_["id"]]
        assert (await _send(c, c_["id"], "hello")).status_code == 409
        await c.patch(f"/conversations/{c_['id']}", json={"archived": False})
        assert (await _send(c, c_["id"], "hello")).status_code == 201

        assert (await c.delete(f"/conversations/{a['id']}")).status_code == 204
        assert (await c.get(f"/conversations/{a['id']}")).status_code == 404
        assert a["id"] not in [x["id"] for x in (await c.get("/conversations")).json()]
        assert (await _send(c, a["id"], "hello")).status_code == 404


async def test_cannot_touch_other_users_data(agents):
    owner, intruder = await new_user(), await new_user()
    conv = await _conversation(owner, agents[GENERAL])
    async with Client(owner) as c:
        await _send(c, conv["id"], "bí mật Đà Nẵng")
    async with Client(intruder) as c:
        cid = conv["id"]
        assert (await c.get(f"/conversations/{cid}")).status_code == 404
        assert (await c.patch(f"/conversations/{cid}", json={"title": "x"})).status_code == 404
        assert (await c.delete(f"/conversations/{cid}")).status_code == 404
        assert (await c.get(f"/conversations/{cid}/messages")).status_code == 404
        assert (await _send(c, cid, "chen ngang")).status_code == 404
        assert (await c.get("/conversations")).json() == []
        assert (await c.get("/search", params={"q": "da nang"})).json() == []


# ---------------------------------------------------------------- chat
async def test_send_without_idempotency_key_creates_new_message_each_time(agents):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    url = f"/conversations/{conv['id']}/messages"
    async with Client(user) as c:
        first = await c.post(url, json={"content": "giống nhau"})
        second = await c.post(url, json={"content": "giống nhau"})
    assert (first.status_code, second.status_code) == (201, 201), first.text
    assert first.json()["user_message"]["id"] != second.json()["user_message"]["id"]


async def test_send_message_flow(agents):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    key = uuid.uuid4()
    async with Client(user) as c:
        r = await _send(c, conv["id"], "Xin chào bạn, hôm nay thế nào?", key)
        assert r.status_code == 201, r.text
        body = r.json()
        um, am = body["user_message"], body["assistant_message"]
        assert (um["role"], um["status"]) == ("user", "completed")
        assert (am["role"], am["status"]) == ("assistant", "completed")
        assert am["reply_to_message_id"] == um["id"]
        assert am["created_at"] > um["created_at"]
        assert "Xin chào bạn" in am["content"] and am["metadata"]["model"] == "mock"

        detail = (await c.get(f"/conversations/{conv['id']}")).json()
        assert detail["message_count"] == 2
        assert detail["title"] == "Xin chào bạn, hôm nay thế nào?"  # tự đặt tên theo tin đầu
        assert detail["last_message_at"] is not None
        session_id = (await sql("select goclaw_session_id from conversations where id = :id", id=conv["id"]))[0]
        assert session_id["goclaw_session_id"] == conv["id"]

        # gửi lại cùng key -> trả kết quả cũ, không tạo tin mới
        again = await _send(c, conv["id"], "Xin chào bạn, hôm nay thế nào?", key)
        assert again.status_code == 200
        assert again.json()["user_message"]["id"] == um["id"]
        assert again.json()["assistant_message"]["id"] == am["id"]
        assert (await c.get(f"/conversations/{conv['id']}")).json()["message_count"] == 2

        # cùng key nhưng conversation khác -> 409
        other = await _conversation(user, agents[GENERAL])
        assert (await _send(c, other["id"], "x", key)).status_code == 409

        # tên do user đặt thì không bị ghi đè
        await c.patch(f"/conversations/{other['id']}", json={"title": "Tên của tôi"})
        await _send(c, other["id"], "tin đầu tiên")
        assert (await c.get(f"/conversations/{other['id']}")).json()["title"] == "Tên của tôi"


async def test_one_inflight_reply_and_stale_recovery(agents):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    await sql(
        "insert into messages (conversation_id, user_id, role, status) values (:c, :u, 'assistant', 'processing')",
        c=conv["id"], u=user,
    )
    async with Client(user) as c:
        r = await _send(c, conv["id"], "gửi chồng")
        assert r.status_code == 409
        # không để lại tin user mồ côi khi bị từ chối
        assert (await c.get(f"/conversations/{conv['id']}")).json()["message_count"] == 1

        await sql("update messages set created_at = now() - interval '1 hour' where conversation_id = :c", c=conv["id"])
        r = await _send(c, conv["id"], "giờ gửi được rồi")
        assert r.status_code == 201
        stuck = await sql(
            "select status, error_message from messages where conversation_id = :c order by created_at limit 1", c=conv["id"]
        )
        assert stuck[0]["status"] == "failed"


async def test_goclaw_failure_marks_reply_failed(agents):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    with mock.patch.object(goclaw, "send_message", side_effect=goclaw.GoClawError("GoClaw lỗi: timeout")):
        async with Client(user) as c:
            r = await _send(c, conv["id"], "alo")
    assert r.status_code == 201
    am = r.json()["assistant_message"]
    assert am["status"] == "failed" and "timeout" in am["error_message"]
    async with Client(user) as c:
        assert (await _send(c, conv["id"], "thử lại")).json()["assistant_message"]["status"] == "completed"


async def test_message_pagination_and_order(agents):
    user = await new_user()
    conv = await _conversation(user, agents[WRITER])
    other = await _conversation(user, agents[WRITER])
    async with Client(user) as c:
        expected = []
        for i in range(7):
            body = (await _send(c, conv["id"], f"tin {i}")).json()
            expected += [body["user_message"]["id"], body["assistant_message"]["id"]]
        seen, before = [], None
        while True:
            params = {"limit": 5, **({"before": before} if before else {})}
            page = (await c.get(f"/conversations/{conv['id']}/messages", params=params)).json()
            seen += [m["id"] for m in page["items"]]
            before = page["next_before"]
            if before is None:
                break
        # đúng thứ tự, kể cả tin user và câu trả lời ghi trong cùng một transaction
        assert seen == list(reversed(expected))
        # con trỏ của cuộc trò chuyện khác hoặc không tồn tại
        for bad in [expected[0], str(uuid.uuid4())]:
            r = await c.get(f"/conversations/{other['id']}/messages", params={"before": bad})
            assert r.status_code == 422


async def test_order_survives_clock_ties_and_skew(agents):
    """Đồng hồ server chạy lùi so với tin trước: tin mới vẫn phải đứng sau."""
    user = await new_user()
    conv = await _conversation(user, agents[WRITER])
    await sql("update conversations set last_message_at = now() + interval '1 hour' where id = :c", c=conv["id"])
    async with Client(user) as c:
        body = (await _send(c, conv["id"], "alo")).json()
        um, am = body["user_message"], body["assistant_message"]
        page = (await c.get(f"/conversations/{conv['id']}/messages")).json()
    rows = await sql("select last_message_at from conversations where id = :c", c=conv["id"])
    assert um["created_at"] > (rows[0]["last_message_at"].isoformat()[:13])  # sau mốc tương lai, không theo đồng hồ
    assert am["created_at"] > um["created_at"]
    assert [m["id"] for m in page["items"]] == [am["id"], um["id"]]


async def test_stale_reply_resolved_by_same_key_retry_and_listing(agents):
    """Server chết giữa chừng: app chỉ gửi lại cùng key hoặc tải lại danh sách vẫn phải thấy kết thúc."""
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    key = uuid.uuid4()
    async with Client(user) as c:
        await _send(c, conv["id"], "alo", key)
        for run_check in ("retry", "list"):
            await sql("update messages set status = 'processing', created_at = now() - interval '1 hour' "
                      "where conversation_id = :c and role = 'assistant'", c=conv["id"])
            if run_check == "retry":
                r = await _send(c, conv["id"], "alo", key)
                assert r.status_code == 200 and r.json()["assistant_message"]["status"] == "failed"
            else:
                items = (await c.get(f"/conversations/{conv['id']}/messages")).json()["items"]
                assert {m["status"] for m in items if m["role"] == "assistant"} == {"failed"}


async def test_result_write_failure_closes_reply(agents):
    """Ghi kết quả của agent bị lỗi: không được kẹt 'processing' chặn cả cuộc trò chuyện."""
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    bad = goclaw.GoClawReply(content="có NUL \x00 ở đây", session_id=conv["id"])
    with mock.patch.object(goclaw, "send_message", return_value=bad):
        async with Client(user, raise_app_exceptions=False) as c:
            assert (await _send(c, conv["id"], "alo")).status_code == 500
    rows = await sql("select status from messages where conversation_id = :c and role = 'assistant'", c=conv["id"])
    assert [x["status"] for x in rows] == ["failed"]
    async with Client(user) as c:
        assert (await _send(c, conv["id"], "gửi tiếp được")).status_code == 201


async def test_send_and_create_rate_limits(agents):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    key = uuid.uuid4()
    async with Client(user) as c:
        assert (await _send(c, conv["id"], "tin", key)).status_code == 201
        for _ in range(19):
            assert (await _send(c, conv["id"], "tin")).status_code == 201
        assert (await _send(c, conv["id"], "tin")).status_code == 429
        assert (await _send(c, conv["id"], "tin", key)).status_code == 200  # gửi lại cùng key không bị tính
    other = await new_user()  # giới hạn theo từng user
    conv2 = await _conversation(other, agents[GENERAL])
    async with Client(other) as c:
        assert (await _send(c, conv2["id"], "tin")).status_code == 201
        for _ in range(29):
            await c.post("/conversations", json={"agent_id": str(agents[GENERAL])})
        assert (await c.post("/conversations", json={"agent_id": str(agents[GENERAL])})).status_code == 429


async def test_search_accent_insensitive(agents):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    async with Client(user) as c:
        await _send(c, conv["id"], "Mai đi Đà Nẵng chơi 50% giá")
        hits = (await c.get("/search", params={"q": "da nang"})).json()
        assert {h["role"] for h in hits} == {"user", "assistant"}
        assert all(h["conversation_id"] == conv["id"] for h in hits)
        assert len((await c.get("/search", params={"q": "50%"})).json()) == 2
        assert (await c.get("/search", params={"q": "5_%"})).json() == []  # ký tự đặc biệt không thành wildcard
        await _send(c, conv["id"], "duong dan C:\\thu muc")
        assert len((await c.get("/search", params={"q": "c:\\thu"})).json()) == 2  # dấu \\ tìm đúng nghĩa đen
        assert (await c.get("/search", params={"q": "c:thu"})).json() == []
        await c.delete(f"/conversations/{conv['id']}")
        assert (await c.get("/search", params={"q": "da nang"})).json() == []


async def test_idempotency_race_returns_first_result(agents):
    """Request thứ 2 cùng key đến khi request 1 chưa commit: insert đụng unique -> trả kết quả của request 1."""
    from app.api.v1.endpoints import conversations as conv_router

    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    other = await _conversation(user, agents[GENERAL])
    key = uuid.uuid4()
    async with Client(user) as c:
        first = (await _send(c, conv["id"], "lần 1", key)).json()

        real = conv_router._existing_send
        calls = {"n": 0}

        async def not_yet_visible(*args):
            calls["n"] += 1
            return None if calls["n"] == 1 else await real(*args)

        with mock.patch.object(conv_router, "_existing_send", side_effect=not_yet_visible):
            r = await _send(c, conv["id"], "lần 1", key)
        assert r.status_code == 200, r.text
        assert r.json()["user_message"]["id"] == first["user_message"]["id"]

        calls["n"] = 0
        with mock.patch.object(conv_router, "_existing_send", side_effect=not_yet_visible):
            assert (await _send(c, other["id"], "lần 1", key)).status_code == 409
        assert (await c.get(f"/conversations/{conv['id']}")).json()["message_count"] == 2


async def test_unexpected_error_still_closes_reply(agents):
    user = await new_user()
    conv = await _conversation(user, agents[GENERAL])
    with mock.patch.object(goclaw, "send_message", side_effect=RuntimeError("bug")):
        async with Client(user, raise_app_exceptions=False) as c:
            r = await _send(c, conv["id"], "alo")
    assert r.status_code == 500
    rows = await sql("select status from messages where conversation_id = :c and role = 'assistant'", c=conv["id"])
    assert [x["status"] for x in rows] == ["failed"]
    async with Client(user) as c:
        assert (await _send(c, conv["id"], "gửi tiếp được")).status_code == 201
