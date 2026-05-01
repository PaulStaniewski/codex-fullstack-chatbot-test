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


def test_protected_endpoint_requires_authentication(client):
    response = client.get("/conversations")

    assert response.status_code == 401
