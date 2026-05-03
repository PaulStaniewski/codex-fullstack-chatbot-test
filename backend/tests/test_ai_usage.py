from types import SimpleNamespace

from app import models
from app.database import get_db
from app.services import chat_service


def _register_and_login(client, email="usage@example.com"):
    client.post("/register", json={"email": email, "password": "password123"})
    login_response = client.post("/login", json={"email": email, "password": "password123"})
    return login_response.json()["access_token"]


def _create_stream_token(client, token):
    response = client.post("/stream-token", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    return response.json()["stream_token"]


def _get_db(client):
    return next(client.app.dependency_overrides[get_db]())


def test_extract_usage_from_openai_completed_event_object():
    event = SimpleNamespace(
        type="response.completed",
        response=SimpleNamespace(
            model="gpt-test",
            usage=SimpleNamespace(input_tokens=123, output_tokens=45, total_tokens=168),
        ),
    )

    usage = chat_service.extract_usage_from_openai_event(event)

    assert usage == chat_service.AIUsage(
        prompt_tokens=123,
        completion_tokens=45,
        total_tokens=168,
        model="gpt-test",
    )


def test_extract_usage_from_openai_event_supports_dict_and_computes_total():
    event = {
        "response": {
            "model": "gpt-dict",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }
    }

    usage = chat_service.extract_usage_from_openai_event(event)

    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 20
    assert usage.total_tokens == 30
    assert usage.model == "gpt-dict"


def test_estimate_usage_cost_uses_configured_model_pricing(monkeypatch):
    monkeypatch.setenv(
        "OPENAI_MODEL_PRICING_JSON",
        '{"gpt-test":{"input_cost_per_1m_tokens":2.0,"output_cost_per_1m_tokens":8.0}}',
    )
    usage = chat_service.AIUsage(
        prompt_tokens=1_000,
        completion_tokens=500,
        total_tokens=1_500,
        model="gpt-test",
    )

    assert chat_service.estimate_usage_cost_usd(usage) == 0.006


def test_chat_stream_records_ai_usage(client, monkeypatch):
    monkeypatch.setenv(
        "OPENAI_MODEL_PRICING_JSON",
        '{"gpt-usage":{"input_cost_per_1m_tokens":1.0,"output_cost_per_1m_tokens":3.0}}',
    )

    async def tracked_stream(_openai_input, usage_callback=None):
        if usage_callback:
            usage_callback(
                chat_service.AIUsage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    model="gpt-usage",
                )
            )
        yield "Tracked response"

    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", tracked_stream)
    token = _register_and_login(client)
    conversation_response = client.post(
        "/conversations",
        json={"title": "Usage"},
        headers={"Authorization": f"Bearer {token}"},
    )
    stream_token = _create_stream_token(client, token)

    response = client.get(
        "/chat-stream",
        params={
            "conversation_id": conversation_response.json()["id"],
            "message": "hello",
            "token": stream_token,
        },
    )

    assert response.status_code == 200
    db = _get_db(client)
    try:
        record = db.query(models.AIUsageRecord).one()
        summary = chat_service.get_ai_usage_summary_for_user(db, record.user_id)
        daily = chat_service.get_daily_ai_usage_for_user(db, record.user_id)
    finally:
        db.close()

    assert record.model == "gpt-usage"
    assert record.prompt_tokens == 100
    assert record.completion_tokens == 50
    assert record.total_tokens == 150
    assert record.estimated_cost_usd == 0.00025
    assert summary["requests"] == 1
    assert summary["total_tokens"] == 150
    assert daily[0]["requests"] == 1
