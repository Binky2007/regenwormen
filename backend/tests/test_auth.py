def test_signup_creates_user_and_returns_token(client):
    res = client.post("/api/auth/signup", json={
        "email": "carlos@example.com", "password": "hunter22", "display_name": "Carlos",
    })
    assert res.status_code == 201
    body = res.get_json()
    assert body["user"]["email"] == "carlos@example.com"
    assert "token" in body


def test_signup_rejects_duplicate_email(client, make_user):
    make_user(email="dup@example.com")
    res = client.post("/api/auth/signup", json={
        "email": "dup@example.com", "password": "hunter22", "display_name": "Someone",
    })
    assert res.status_code == 409


def test_login_with_correct_password_returns_token(client, make_user):
    make_user(email="login@example.com", password="correct-horse")
    res = client.post("/api/auth/login", json={"email": "login@example.com", "password": "correct-horse"})
    assert res.status_code == 200
    assert "token" in res.get_json()


def test_login_with_wrong_password_is_rejected(client, make_user):
    make_user(email="login2@example.com", password="correct-horse")
    res = client.post("/api/auth/login", json={"email": "login2@example.com", "password": "wrong"})
    assert res.status_code == 401


def test_me_requires_auth(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_returns_current_user(client, make_user):
    make_user(email="me@example.com", password="hunter22", display_name="Me")
    login = client.post("/api/auth/login", json={"email": "me@example.com", "password": "hunter22"})
    token = login.get_json()["token"]
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.get_json()["display_name"] == "Me"
