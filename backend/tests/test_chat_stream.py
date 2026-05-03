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
    assert "event: done" in response.text


def test_chat_stream_normal_streaming_still_works(client, monkeypatch):
    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", _fake_openai_stream)
    token, conversation_id = _create_authenticated_conversation(client)

    response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "hello", "token": token},
    )

    assert response.status_code == 200
    assert "data: This " in response.text
    assert "event: done" in response.text
    assert "Error:" not in response.text


def test_chat_stream_uses_interview_system_prompt(client, monkeypatch):
    captured_input = None

    async def capture_openai_input(openai_input):
        nonlocal captured_input
        captured_input = openai_input
        yield "Interview question"

    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", capture_openai_input)
    token, conversation_id = _create_authenticated_conversation(client)
    mode_response = client.patch(
        f"/conversations/{conversation_id}/mode",
        json={"mode": "interview"},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        "/chat-stream",
        params={
            "conversation_id": conversation_id,
            "message": "Practice FastAPI interviews",
            "token": token,
        },
    )

    assert mode_response.status_code == 200
    assert response.status_code == 200
    assert captured_input[0]["role"] == "system"
    assert "You are a technical interviewer." in captured_input[0]["content"]
    assert "Do not reveal ideal answers before the candidate attempts to answer." in (
        captured_input[0]["content"]
    )


def test_chat_stream_limits_openai_history_by_recent_messages(client, monkeypatch):
    captured_input = None

    async def capture_openai_input(openai_input):
        nonlocal captured_input
        captured_input = openai_input
        yield "ok"

    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", capture_openai_input)
    monkeypatch.setattr("app.services.chat_service.CHAT_HISTORY_MAX_MESSAGES", 4)
    monkeypatch.setattr("app.services.chat_service.CHAT_HISTORY_MAX_CHARS", 1000)
    monkeypatch.setattr("app.routes.chat_routes._rate_limit_buckets", {})
    token, conversation_id = _create_authenticated_conversation(client)
    for index in range(6):
        client.post(
            "/messages",
            json={
                "conversation_id": conversation_id,
                "role": "user" if index % 2 == 0 else "assistant",
                "content": f"history-{index}",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "current", "token": token},
    )

    assert response.status_code == 200
    prompt_contents = [message["content"] for message in captured_input]
    assert "history-0" not in prompt_contents
    assert "history-1" not in prompt_contents
    assert prompt_contents[-5:] == ["history-2", "history-3", "history-4", "history-5", "current"]


def test_chat_stream_limits_openai_history_by_character_budget(client, monkeypatch):
    captured_input = None

    async def capture_openai_input(openai_input):
        nonlocal captured_input
        captured_input = openai_input
        yield "ok"

    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", capture_openai_input)
    monkeypatch.setattr("app.services.chat_service.CHAT_HISTORY_MAX_MESSAGES", 10)
    monkeypatch.setattr("app.services.chat_service.CHAT_HISTORY_MAX_CHARS", 12)
    monkeypatch.setattr("app.routes.chat_routes._rate_limit_buckets", {})
    token, conversation_id = _create_authenticated_conversation(client)
    client.post(
        "/messages",
        json={
            "conversation_id": conversation_id,
            "role": "user",
            "content": "old-message-too-long",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/messages",
        json={
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": "recent",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "current", "token": token},
    )

    assert response.status_code == 200
    prompt_contents = [message["content"] for message in captured_input]
    assert "old-message-too-long" not in prompt_contents
    assert "recent" in prompt_contents
    assert prompt_contents[-1] == "current"


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
    assert "event: error" in stream_response.text
    assert "data: Error: Unable to generate response." in stream_response.text
    assert "event: done" not in stream_response.text

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
    assert "event: error" in stream_response.text
    assert "data: Error: Unable to generate response." in stream_response.text
    assert "stream failed" not in stream_response.text
    assert "event: done" not in stream_response.text

    messages_response = client.get(
        "/messages",
        params={"conversation_id": conversation_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    messages = messages_response.json()
    assert [message["role"] for message in messages] == ["user"]


def test_chat_stream_rejects_message_that_is_too_long(client, monkeypatch):
    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", _fake_openai_stream)
    token, conversation_id = _create_authenticated_conversation(client)

    response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "x" * 2001, "token": token},
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "data: Error: Message is too long." in response.text

    messages_response = client.get(
        "/messages",
        params={"conversation_id": conversation_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert messages_response.json() == []


def test_chat_stream_rate_limit_exceeded(client, monkeypatch):
    calls = 0

    async def counted_stream(_openai_input):
        nonlocal calls
        calls += 1
        yield "ok"

    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", counted_stream)
    monkeypatch.setattr("app.routes.chat_routes.CHAT_STREAM_RATE_LIMIT", 2)
    monkeypatch.setattr("app.routes.chat_routes.CHAT_STREAM_RATE_WINDOW_SECONDS", 60)
    monkeypatch.setattr("app.routes.chat_routes._rate_limit_buckets", {})
    token, conversation_id = _create_authenticated_conversation(client)

    first_response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "one", "token": token},
    )
    second_response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "two", "token": token},
    )
    limited_response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "three", "token": token},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert limited_response.status_code == 200
    assert "event: done" in first_response.text
    assert "event: done" in second_response.text
    assert "event: error" in limited_response.text
    assert "data: Error: Too many requests. Please wait a moment." in limited_response.text
    assert calls == 2


def test_chat_stream_generates_title_for_empty_conversation_title(client, monkeypatch):
    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", _fake_openai_stream)
    client.post(
        "/register",
        json={"email": "title@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/login",
        json={"email": "title@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]
    conversation_response = client.post(
        "/conversations",
        json={"title": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    conversation_id = conversation_response.json()["id"]

    stream_response = client.get(
        "/chat-stream",
        params={
            "conversation_id": conversation_id,
            "message": "explain Docker networking!",
            "token": token,
        },
    )
    conversations_response = client.get(
        "/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert stream_response.status_code == 200
    conversation = conversations_response.json()[0]
    assert conversation["id"] == conversation_id
    assert conversation["title"] == "Explain Docker networking"
