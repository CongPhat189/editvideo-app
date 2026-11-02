import uuid
from unittest import mock

from cryptography.hazmat.primitives.asymmetric import ec

from app import goclaw
from tests.conftest import Client, make_token, new_user, sql

GENERAL = "Trợ lý chung"
WRITER = "Content Writer"
RESTRICTED = "Video Editor"


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
    other_key = ec.generate_private_key(ec.SECP256R1())
    bad_tokens = [
        "not-a-jwt",
        make_token(user, exp_in=-10),                       # hết hạn
        make_token(user, aud="anon"),                       # sai audience
        make_token(user, iss="https://evil.example/auth/v1"),  # sai issuer
        make_token(uuid.uuid4()),                           # user không tồn tại
    ]
    async with Client() as c:
        assert (await c.get("/me")).status_code == 401
    for token in bad_tokens:
        async with Client(token=token) as c:
            assert (await c.get("/me")).status_code == 401, token
    # chữ ký bằng khóa khác: _signing_key trả khóa công khai thật -> sai chữ ký
    async with Client(token=make_token(user, key=other_key)) as c:
        assert (await c.get("/me")).status_code == 401


async def test_suspended_user_forbidden():
    user = await new_user()
    await sql("update profiles set status = 'suspended' where id = :id", id=user)
    async with Client(user) as c:
        assert (await c.get("/me")).status_code == 403


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
        assert (await c.patch("/me", json={"avatar_path": f"{uuid.uuid4()}/a.jpg"})).status_code == 422
        r = await c.patch("/me", json={"avatar_path": f"{user}/a.jpg"})
        assert r.json()["avatar_path"] == f"{user}/a.jpg"

        assert (await c.patch("/me/settings", json={"timezone": "Asia/Saigonn"})).status_code == 422
        assert (await c.patch("/me/settings", json={"theme": "pink"})).status_code == 422
        r = await c.patch("/me/settings", json={"theme": "dark", "timezone": "Asia/Bangkok"})
        assert r.status_code == 200
        assert (r.json()["theme"], r.json()["timezone"]) == ("dark", "Asia/Bangkok")


# ---------------------------------------------------------------- agents
async def test_agents_visibility(agents):
    user = await new_user()
    async with Client(user) as c:
        names = [a["name"] for a in (await c.get("/agents")).json()]
        assert names == [GENERAL, WRITER]
        assert "goclaw_agent_id" not in (await c.get("/agents")).json()[0]

        await sql("insert into user_agent_access (user_id, agent_id) values (:u, :a)", u=user, a=agents[RESTRICTED])
        assert [a["name"] for a in (await c.get("/agents")).json()] == [GENERAL, WRITER, RESTRICTED]

        await sql("update user_agent_access set expires_at = now() - interval '1 minute' where user_id = :u", u=user)
        assert RESTRICTED not in [a["name"] for a in (await c.get("/agents")).json()]


async def test_create_conversation_agent_rules(agents):
    user = await new_user()
    async with Client(user) as c:
        r = await c.post("/conversations", json={"agent_id": str(agents[RESTRICTED])})
        assert r.status_code == 403
        r = await c.post("/conversations", json={"agent_id": str(uuid.uuid4())})
        assert r.status_code == 403
        r = await c.post("/conversations", json={"agent_id": str(agents[GENERAL]), "title": "Kế hoạch"})
        assert r.status_code == 201
        assert (r.json()["title"], r.json()["title_source"]) == ("Kế hoạch", "user")


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
        assert am["seq"] > um["seq"]
        assert "Xin chào bạn" in am["content"] and am["model"] == "mock"

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
            "select status, error_message from messages where conversation_id = :c order by seq limit 1", c=conv["id"]
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


async def test_agent_disabled_after_conversation(agents):
    user = await new_user()
    await sql("insert into user_agent_access (user_id, agent_id) values (:u, :a)", u=user, a=agents[RESTRICTED])
    conv = await _conversation(user, agents[RESTRICTED])
    await sql("delete from user_agent_access where user_id = :u", u=user)
    async with Client(user) as c:
        assert (await _send(c, conv["id"], "còn dùng được không?")).status_code == 403


async def test_message_pagination(agents):
    user = await new_user()
    conv = await _conversation(user, agents[WRITER])
    async with Client(user) as c:
        for i in range(7):
            assert (await _send(c, conv["id"], f"tin {i}")).status_code == 201
        seen, before = [], None
        while True:
            params = {"limit": 5, **({"before_seq": before} if before else {})}
            page = (await c.get(f"/conversations/{conv['id']}/messages", params=params)).json()
            seen += [m["seq"] for m in page["items"]]
            before = page["next_before_seq"]
            if before is None:
                break
    assert len(seen) == 14 and len(set(seen)) == 14
    assert seen == sorted(seen, reverse=True)


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
        await c.delete(f"/conversations/{conv['id']}")
        assert (await c.get("/search", params={"q": "da nang"})).json() == []


async def test_idempotency_race_returns_first_result(agents):
    """Request thứ 2 cùng key đến khi request 1 chưa commit: insert đụng unique -> trả kết quả của request 1."""
    from app.routers import conversations as conv_router

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
