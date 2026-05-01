from app.routes import auth_routes


def test_register_user(client):
    response = client.post(
        "/register",
        json={"email": "user@example.com", "password": "password123"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert "hashed_password" not in body


def test_login_user(client):
    client.post(
        "/register",
        json={"email": "user@example.com", "password": "password123"},
    )

    response = client.post(
        "/login",
        json={"email": "user@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_read_current_user(client):
    client.post(
        "/register",
        json={"email": "profile@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/login",
        json={"email": "profile@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "profile@example.com"
    assert body["id"]
    assert body["created_at"]
    assert "hashed_password" not in body


def test_logout_user(client):
    client.post(
        "/register",
        json={"email": "logout@example.com", "password": "password1234"},
    )
    login_response = client.post(
        "/login",
        json={"email": "logout@example.com", "password": "password1234"},
    )
    token = login_response.json()["access_token"]

    response = client.post("/logout", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"success": True}


def test_logout_requires_authentication(client):
    response = client.post("/logout")

    assert response.status_code == 401


def test_protected_endpoint_requires_authentication(client):
    response = client.get("/conversations")

    assert response.status_code == 401


def test_register_rejects_password_shorter_than_ten_characters(client):
    response = client.post(
        "/register",
        json={"email": "shortpass@example.com", "password": "abc12345"},
    )

    assert response.status_code == 422
    detail_text = str(response.json().get("detail", "")).lower()
    assert "at least 10 characters" in detail_text or "string_too_short" in detail_text


def test_register_rejects_password_without_number(client):
    response = client.post(
        "/register",
        json={"email": "nonumber@example.com", "password": "abcdefghij"},
    )

    assert response.status_code == 422
    detail_text = str(response.json().get("detail", "")).lower()
    assert "letter and one number" in detail_text


def test_register_rejects_password_without_letter(client):
    response = client.post(
        "/register",
        json={"email": "noletter@example.com", "password": "1234567890"},
    )

    assert response.status_code == 422
    detail_text = str(response.json().get("detail", "")).lower()
    assert "letter and one number" in detail_text


def test_login_rate_limit_after_repeated_failed_attempts(client, monkeypatch):
    monkeypatch.setattr("app.routes.auth_routes._failed_login_buckets", {})

    for _ in range(auth_routes.LOGIN_FAILED_ATTEMPT_LIMIT):
        response = client.post(
            "/login",
            json={"email": "missing@example.com", "password": "wrong-password"},
            headers={"X-Forwarded-For": "203.0.113.10"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    limited_response = client.post(
        "/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
        headers={"X-Forwarded-For": "203.0.113.10"},
    )

    assert limited_response.status_code == 429
    assert limited_response.json()["detail"] == auth_routes.LOGIN_RATE_LIMIT_ERROR


def test_login_rate_limit_is_ip_scoped(client, monkeypatch):
    monkeypatch.setattr("app.routes.auth_routes._failed_login_buckets", {})

    for _ in range(auth_routes.LOGIN_FAILED_ATTEMPT_LIMIT):
        client.post(
            "/login",
            json={"email": "missing@example.com", "password": "wrong-password"},
            headers={"X-Forwarded-For": "203.0.113.11"},
        )

    response_other_ip = client.post(
        "/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
        headers={"X-Forwarded-For": "203.0.113.12"},
    )

    assert response_other_ip.status_code == 401
    assert response_other_ip.json()["detail"] == "Invalid credentials"


def test_successful_login_clears_failed_attempt_bucket(client, monkeypatch):
    monkeypatch.setattr("app.routes.auth_routes._failed_login_buckets", {})

    client.post(
        "/register",
        json={"email": "ratelimit@example.com", "password": "password123"},
    )

    limited_ip = "203.0.113.13"
    for _ in range(auth_routes.LOGIN_FAILED_ATTEMPT_LIMIT - 1):
        response = client.post(
            "/login",
            json={"email": "ratelimit@example.com", "password": "wrong-password"},
            headers={"X-Forwarded-For": limited_ip},
        )
        assert response.status_code == 401

    success_response = client.post(
        "/login",
        json={"email": "ratelimit@example.com", "password": "password123"},
        headers={"X-Forwarded-For": limited_ip},
    )
    assert success_response.status_code == 200

    first_failed_after_success = client.post(
        "/login",
        json={"email": "ratelimit@example.com", "password": "wrong-password"},
        headers={"X-Forwarded-For": limited_ip},
    )
    assert first_failed_after_success.status_code == 401
