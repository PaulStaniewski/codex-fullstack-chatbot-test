def _register_and_login(client, email):
    client.post(
        "/register",
        json={"email": email, "password": "password123"},
    )
    login_response = client.post(
        "/login",
        json={"email": email, "password": "password123"},
    )
    return login_response.json()["access_token"]


def _create_conversation(client, token, title="Original title"):
    response = client.post(
        "/conversations",
        json={"title": title},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()


def test_owner_can_rename_conversation(client):
    token = _register_and_login(client, "owner@example.com")
    conversation = _create_conversation(client, token)

    response = client.patch(
        f"/conversations/{conversation['id']}",
        json={"title": "Updated title"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"


def test_non_owner_cannot_rename_conversation(client):
    owner_token = _register_and_login(client, "owner@example.com")
    other_token = _register_and_login(client, "other@example.com")
    conversation = _create_conversation(client, owner_token)

    response = client.patch(
        f"/conversations/{conversation['id']}",
        json={"title": "Not allowed"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def test_owner_can_delete_conversation_and_related_messages(client, monkeypatch):
    async def fake_stream(_openai_input):
        yield "Assistant reply"

    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", fake_stream)
    token = _register_and_login(client, "owner@example.com")
    conversation = _create_conversation(client, token)

    client.get(
        "/chat-stream",
        params={"conversation_id": conversation["id"], "message": "hello", "token": token},
    )

    response = client.delete(
        f"/conversations/{conversation['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    messages_response = client.get(
        "/messages",
        params={"conversation_id": conversation["id"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert messages_response.status_code == 404


def test_non_owner_cannot_delete_conversation(client):
    owner_token = _register_and_login(client, "owner@example.com")
    other_token = _register_and_login(client, "other@example.com")
    conversation = _create_conversation(client, owner_token)

    response = client.delete(
        f"/conversations/{conversation['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def test_default_conversation_mode_is_chat(client):
    token = _register_and_login(client, "owner@example.com")

    conversation = _create_conversation(client, token)

    assert conversation["mode"] == "chat"


def test_owner_can_update_conversation_mode_to_learn(client):
    token = _register_and_login(client, "owner@example.com")
    conversation = _create_conversation(client, token)

    response = client.patch(
        f"/conversations/{conversation['id']}/mode",
        json={"mode": "learn"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "learn"


def test_invalid_conversation_mode_returns_400(client):
    token = _register_and_login(client, "owner@example.com")
    conversation = _create_conversation(client, token)

    response = client.patch(
        f"/conversations/{conversation['id']}/mode",
        json={"mode": "invalid"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


def test_non_owner_cannot_update_conversation_mode(client):
    owner_token = _register_and_login(client, "owner@example.com")
    other_token = _register_and_login(client, "other@example.com")
    conversation = _create_conversation(client, owner_token)

    response = client.patch(
        f"/conversations/{conversation['id']}/mode",
        json={"mode": "learn"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404
