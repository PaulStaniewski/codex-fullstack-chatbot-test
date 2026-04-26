def _register_and_login(client, email="progress@example.com"):
    client.post(
        "/register",
        json={"email": email, "password": "password123"},
    )
    login_response = client.post(
        "/login",
        json={"email": email, "password": "password123"},
    )
    return login_response.json()["access_token"]


async def _fake_openai_stream(_openai_input):
    yield "Assistant reply"


def test_progress_defaults(client):
    token = _register_and_login(client)

    response = client.get("/progress", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["sessions_count"] == 0
    assert data["messages_count"] == 0
    assert data["correct_answers"] == 0
    assert data["incorrect_answers"] == 0
    assert data["time_spent_seconds"] == 0
    assert data["achievements"] == []


def test_progress_tracks_sessions_messages_and_achievements(client, monkeypatch):
    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", _fake_openai_stream)
    token = _register_and_login(client)

    conversation_response = client.post(
        "/conversations",
        json={"title": "Practice"},
        headers={"Authorization": f"Bearer {token}"},
    )
    conversation_id = conversation_response.json()["id"]
    client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "hello", "token": token},
    )

    response = client.get("/progress", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    achievement_names = {achievement["name"] for achievement in data["achievements"]}
    assert data["sessions_count"] == 1
    assert data["messages_count"] == 1
    assert data["last_activity_at"] is not None
    assert "First Session" in achievement_names
    assert "Conversation Starter" in achievement_names


def test_progress_requires_auth(client):
    response = client.get("/progress")

    assert response.status_code == 401
