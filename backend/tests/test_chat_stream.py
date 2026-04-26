def _create_authenticated_conversation(client):
    client.post(
        "/register",
        json={"email": "stream@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/login",
        json={"email": "stream@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]

    conversation_response = client.post(
        "/conversations",
        json={"title": "Streaming test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    conversation_id = conversation_response.json()["id"]
    return token, conversation_id


def test_chat_stream_requires_token(client):
    response = client.get(
        "/chat-stream",
        params={"conversation_id": 1, "message": "hello"},
    )

    assert response.status_code == 401


def test_chat_stream_invalid_conversation_returns_404(client):
    token, _conversation_id = _create_authenticated_conversation(client)

    response = client.get(
        "/chat-stream",
        params={"conversation_id": 999, "message": "hello", "token": token},
    )

    assert response.status_code == 404


def test_chat_stream_returns_sse_data(client):
    token, conversation_id = _create_authenticated_conversation(client)

    response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "hello", "token": token},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data: This" in response.text
    assert "data: response." in response.text


def test_chat_stream_persists_user_and_assistant_messages(client):
    token, conversation_id = _create_authenticated_conversation(client)

    stream_response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "hello", "token": token},
    )
    assert stream_response.status_code == 200

    messages_response = client.get(
        "/messages",
        params={"conversation_id": conversation_id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "hello"
    assert messages[1]["content"] == "This is a streamed assistant response."
