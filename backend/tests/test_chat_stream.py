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


async def _fake_openai_stream(_openai_input):
    for chunk in ["This ", "is ", "a streamed assistant response."]:
        yield chunk


async def _failing_openai_stream(_openai_input):
    raise RuntimeError("stream failed")
    yield


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


def test_chat_stream_returns_sse_data(client, monkeypatch):
    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", _fake_openai_stream)
    token, conversation_id = _create_authenticated_conversation(client)

    response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "hello", "token": token},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data: This " in response.text
    assert "data: a streamed assistant response." in response.text


def test_chat_stream_persists_user_and_assistant_messages(client, monkeypatch):
    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", _fake_openai_stream)
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


def test_chat_stream_returns_safe_error_when_openai_key_missing(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    token, conversation_id = _create_authenticated_conversation(client)

    stream_response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "hello", "token": token},
    )

    assert stream_response.status_code == 200
    assert "data: Error: Unable to generate response." in stream_response.text

    messages_response = client.get(
        "/messages",
        params={"conversation_id": conversation_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    messages = messages_response.json()
    assert [message["role"] for message in messages] == ["user"]


def test_chat_stream_returns_safe_error_and_skips_assistant_on_stream_failure(
    client, monkeypatch
):
    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", _failing_openai_stream)
    token, conversation_id = _create_authenticated_conversation(client)

    stream_response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "hello", "token": token},
    )

    assert stream_response.status_code == 200
    assert "data: Error: Unable to generate response." in stream_response.text
    assert "stream failed" not in stream_response.text

    messages_response = client.get(
        "/messages",
        params={"conversation_id": conversation_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    messages = messages_response.json()
    assert [message["role"] for message in messages] == ["user"]
