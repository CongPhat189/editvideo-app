def test_list_users(client):
    res = client.get("/api/users")
    assert res.status_code == 200
    emails = [u["email"] for u in res.json()["items"]]
    assert "abc@gmail.com" in emails


def test_other_endpoints_still_work(client):
    for path in ["/api/dashboard", "/api/analytics", "/api/platforms", "/api/connectors", "/api/schedule"]:
        assert client.get(path).status_code == 200, path

    res = client.post("/api/schedule", json={"title": "Video test", "scheduled_at": "2026-11-02T08:00:00"})
    assert res.status_code == 200
    res = client.post("/api/publishing", json={"content": "Hello", "platforms": ["Facebook"]})
    assert res.status_code == 200
    res = client.post("/api/videos/generate", json={"prompt": "Video thử"})
    assert res.status_code == 200


def test_login_token_can_be_decoded(client):
    from app.core.security import decode_token

    token = client.post("/api/auth/login", json={"email": "abc@gmail.com", "password": "123456"}).json()["token"]
    assert decode_token(token)["email"] == "abc@gmail.com"
