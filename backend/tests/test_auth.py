from app import models
from app.database import get_db
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
    assert body["refresh_token"]


def test_refresh_access_token(client):
    client.post(
        "/register",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/login",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post("/refresh", json={"refresh_token": refresh_token})

    assert refresh_response.status_code == 200
    body = refresh_response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["refresh_token"]
    assert body["refresh_token"] != refresh_token


def test_stream_token_requires_auth(client):
    response = client.post("/stream-token")

    assert response.status_code == 401


def test_stream_token_endpoint_issues_short_lived_opaque_token(client):
    client.post("/register", json={"email": "stream-token@example.com", "password": "password123"})
    login_response = client.post(
        "/login",
        json={"email": "stream-token@example.com", "password": "password123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post("/stream-token", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["stream_token"]
    assert "." not in body["stream_token"]
    assert body["expires_at"]


def test_login_creates_refresh_session(client):
    client.post(
        "/register",
        json={"email": "session@example.com", "password": "password123"},
    )

    response = client.post(
        "/login",
        json={"email": "session@example.com", "password": "password123"},
    )
    refresh_token = response.json()["refresh_token"]

    db = next(client.app.dependency_overrides[get_db]())
    try:
        sessions = db.query(models.RefreshSession).all()
    finally:
        db.close()

    assert response.status_code == 200
    assert len(sessions) == 1
    assert sessions[0].token_hash
    assert sessions[0].token_hash != refresh_token
    assert sessions[0].revoked_at is None


def test_refresh_rotates_token_and_revokes_old_session(client):
    client.post(
        "/register",
        json={"email": "rotate@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/login",
        json={"email": "rotate@example.com", "password": "password123"},
    )
    old_refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post("/refresh", json={"refresh_token": old_refresh_token})
    new_refresh_token = refresh_response.json()["refresh_token"]

    db = next(client.app.dependency_overrides[get_db]())
    try:
        sessions = db.query(models.RefreshSession).order_by(models.RefreshSession.created_at.asc()).all()
    finally:
        db.close()

    assert refresh_response.status_code == 200
    assert new_refresh_token
    assert new_refresh_token != old_refresh_token
    assert len(sessions) == 2
    assert sessions[0].revoked_at is not None
    assert sessions[0].replaced_by_session_id == sessions[1].id
    assert sessions[1].revoked_at is None


def test_old_refresh_token_cannot_be_reused_after_rotation(client):
    client.post(
        "/register",
        json={"email": "reuse@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/login",
        json={"email": "reuse@example.com", "password": "password123"},
    )
    old_refresh_token = login_response.json()["refresh_token"]

    first_refresh = client.post("/refresh", json={"refresh_token": old_refresh_token})
    second_refresh = client.post("/refresh", json={"refresh_token": old_refresh_token})

    assert first_refresh.status_code == 200
    assert second_refresh.status_code == 401
    assert second_refresh.json()["detail"] == "Could not validate credentials"


def test_refresh_rejects_access_token(client):
    client.post(
        "/register",
        json={"email": "refreshreject@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/login",
        json={"email": "refreshreject@example.com", "password": "password123"},
    )
    access_token = login_response.json()["access_token"]

    refresh_response = client.post("/refresh", json={"refresh_token": access_token})

    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "Could not validate credentials"


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


def test_logout_revokes_refresh_session(client):
    client.post(
        "/register",
        json={"email": "logout-session@example.com", "password": "password1234"},
    )
    login_response = client.post(
        "/login",
        json={"email": "logout-session@example.com", "password": "password1234"},
    )
    token = login_response.json()["access_token"]

    response = client.post("/logout", headers={"Authorization": f"Bearer {token}"})

    db = next(client.app.dependency_overrides[get_db]())
    try:
        session = db.query(models.RefreshSession).one()
    finally:
        db.close()

    assert response.status_code == 200
    assert session.revoked_at is not None


def test_revoked_refresh_token_cannot_refresh_after_logout(client):
    client.post(
        "/register",
        json={"email": "logout-refresh@example.com", "password": "password1234"},
    )
    login_response = client.post(
        "/login",
        json={"email": "logout-refresh@example.com", "password": "password1234"},
    )
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    logout_response = client.post("/logout", headers={"Authorization": f"Bearer {access_token}"})
    refresh_response = client.post("/refresh", json={"refresh_token": refresh_token})

    assert logout_response.status_code == 200
    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "Could not validate credentials"


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
