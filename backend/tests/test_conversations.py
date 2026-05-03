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


def test_owner_can_update_conversation_mode_to_interview(client):
    token = _register_and_login(client, "owner@example.com")
    conversation = _create_conversation(client, token)

    response = client.patch(
        f"/conversations/{conversation['id']}/mode",
        json={"mode": "interview"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "interview"


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


def test_owner_can_export_conversation(client, monkeypatch):
    async def fake_stream(_openai_input):
        yield "Assistant reply"

    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", fake_stream)
    token = _register_and_login(client, "owner@example.com")
    conversation = _create_conversation(client, token, title="Export me")

    client.get(
        "/chat-stream",
        params={"conversation_id": conversation["id"], "message": "hello", "token": token},
    )
    response = client.get(
        f"/conversations/{conversation['id']}/export",
        params={"format": "txt"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == (
        f'attachment; filename="conversation-{conversation["id"]}.txt"'
    )
    assert response.headers["content-type"].startswith("text/plain")
    assert "Export me" in response.text
    assert "User (" in response.text
    assert "hello" in response.text
    assert "Assistant (" in response.text
    assert "Assistant reply" in response.text


def test_non_owner_cannot_export_conversation(client):
    owner_token = _register_and_login(client, "owner@example.com")
    other_token = _register_and_login(client, "other@example.com")
    conversation = _create_conversation(client, owner_token)

    response = client.get(
        f"/conversations/{conversation['id']}/export",
        params={"format": "json"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def test_default_conversation_is_not_pinned(client):
    token = _register_and_login(client, "owner@example.com")

    conversation = _create_conversation(client, token)

    assert conversation["is_pinned"] is False


def test_owner_can_toggle_conversation_pin(client):
    token = _register_and_login(client, "owner@example.com")
    conversation = _create_conversation(client, token)

    pinned_response = client.patch(
        f"/conversations/{conversation['id']}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )
    unpinned_response = client.patch(
        f"/conversations/{conversation['id']}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert pinned_response.status_code == 200
    assert pinned_response.json()["is_pinned"] is True
    assert unpinned_response.status_code == 200
    assert unpinned_response.json()["is_pinned"] is False


def test_non_owner_cannot_toggle_conversation_pin(client):
    owner_token = _register_and_login(client, "owner@example.com")
    other_token = _register_and_login(client, "other@example.com")
    conversation = _create_conversation(client, owner_token)

    response = client.patch(
        f"/conversations/{conversation['id']}/pin",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def test_pinned_conversations_are_listed_first(client):
    token = _register_and_login(client, "owner@example.com")
    first = _create_conversation(client, token, title="First")
    second = _create_conversation(client, token, title="Second")

    client.patch(
        f"/conversations/{first['id']}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )
    response = client.get(
        "/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    conversations = response.json()
    assert conversations[0]["id"] == first["id"]
    assert conversations[0]["is_pinned"] is True
    assert conversations[1]["id"] == second["id"]


def test_conversations_support_limit_and_offset_pagination(client):
    token = _register_and_login(client, "pagination@example.com")
    for title in ["First", "Second", "Third"]:
        _create_conversation(client, token, title=title)

    full_response = client.get(
        "/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    paged_response = client.get(
        "/conversations",
        params={"limit": 2, "offset": 1},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert paged_response.status_code == 200
    assert [item["id"] for item in paged_response.json()] == [
        item["id"] for item in full_response.json()[1:3]
    ]


def test_messages_support_limit_and_offset_pagination(client):
    token = _register_and_login(client, "message-pagination@example.com")
    conversation = _create_conversation(client, token)
    for index in range(5):
        client.post(
            "/messages",
            json={
                "conversation_id": conversation["id"],
                "role": "user",
                "content": f"message-{index}",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    response = client.get(
        "/messages",
        params={"conversation_id": conversation["id"], "limit": 2, "offset": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert [message["content"] for message in response.json()] == ["message-2", "message-3"]


def test_pagination_rejects_limits_over_maximum(client):
    token = _register_and_login(client, "pagination-limit@example.com")

    conversations_response = client.get(
        "/conversations",
        params={"limit": 101},
        headers={"Authorization": f"Bearer {token}"},
    )
    messages_response = client.get(
        "/messages",
        params={"limit": 201},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert conversations_response.status_code == 422
    assert messages_response.status_code == 422
