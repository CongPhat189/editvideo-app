def test_health(client):
    assert client.get("/api/health").json()["ok"] is True


def test_login_demo_account(client):
    res = client.post("/api/auth/login", json={"email": "abc@gmail.com", "password": "123456"})
    assert res.status_code == 200
    assert res.json()["token"]


def test_login_wrong_password(client):
    res = client.post("/api/auth/login", json={"email": "abc@gmail.com", "password": "sai-mat-khau"})
    assert res.status_code == 401


def test_register_then_login(client):
    res = client.post("/api/auth/register", json={"full_name": "Test", "email": "test@example.com", "password": "123456"})
    assert res.status_code == 200
    res = client.post("/api/auth/login", json={"email": "test@example.com", "password": "123456"})
    assert res.status_code == 200
