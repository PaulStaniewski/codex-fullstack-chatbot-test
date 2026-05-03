import logging
import os
import time
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import date

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    AsyncOpenAI,
    OpenAIError,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, progress as progress_service
from app.observability import get_request_id, reset_request_id, set_request_id


logger = logging.getLogger(__name__)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
SAFE_STREAM_ERROR = "Error: Unable to generate response."
MESSAGE_TOO_LONG_ERROR = "Error: Message is too long. Please keep it under 2000 characters."
RATE_LIMIT_ERROR = "Error: Too many requests. Please wait a moment."
MAX_CHAT_MESSAGE_LENGTH = 2000
MAX_GENERATED_TITLE_LENGTH = 60
CHAT_STREAM_RATE_LIMIT = 10
CHAT_STREAM_RATE_WINDOW_SECONDS = 60
DEFAULT_CHAT_HISTORY_MAX_MESSAGES = 20
DEFAULT_CHAT_HISTORY_MAX_CHARS = 12000
DEFAULT_OPENAI_INPUT_COST_PER_1M_TOKENS = 0.0
DEFAULT_OPENAI_OUTPUT_COST_PER_1M_TOKENS = 0.0


def _get_positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return max(0, value)


CHAT_HISTORY_MAX_MESSAGES = _get_positive_int_env(
    "CHAT_HISTORY_MAX_MESSAGES",
    DEFAULT_CHAT_HISTORY_MAX_MESSAGES,
)
CHAT_HISTORY_MAX_CHARS = _get_positive_int_env(
    "CHAT_HISTORY_MAX_CHARS",
    DEFAULT_CHAT_HISTORY_MAX_CHARS,
)

@dataclass
class AIUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str


class AIUsageTracker:
    def __init__(self) -> None:
        self.usage: AIUsage | None = None

    def capture(self, usage: AIUsage | None) -> None:
        if usage is not None:
            self.usage = usage


StreamTextCallable = Callable[..., AsyncIterator[str]]
DisconnectCallable = Callable[[], Awaitable[bool]]


def format_sse_data(value: str, event: str | None = None) -> str:
    lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    event_prefix = f"event: {event}\n" if event else ""
    return event_prefix + "".join(f"data: {line}\n" for line in lines) + "\n"


def format_sse_event(event: str, value: str = "") -> str:
    return format_sse_data(value, event=event)


def build_system_prompt(mode: str) -> str:
    if mode == "learn":
        return (
            "You are an AI tutor.\n"
            "Teach the user step by step.\n"
            "Ask one question at a time.\n"
            "Wait for the user's answer.\n"
            "Give feedback.\n"
            "Guide the user forward.\n"
            "Do not give full solutions immediately."
        )
    if mode == "interview":
        return (
            "You are a technical interviewer.\n"
            "Run a realistic interview simulation.\n"
            "Ask one question at a time.\n"
            "Wait for the candidate's answer before giving feedback.\n"
            "Evaluate answers clearly but constructively.\n"
            "Ask follow-up questions when useful.\n"
            "Do not reveal ideal answers before the candidate attempts to answer.\n"
            "Focus on practical engineering reasoning.\n"
            "If the user does not specify a topic, ask what role or topic they want to practice, "
            "such as Python, FastAPI, React, Docker, PostgreSQL, AI / RAG, system design, "
            "or backend engineering."
        )
    return "You are a helpful AI assistant."


def generate_conversation_title(text: str) -> str:
    title = " ".join(text.strip().split())
    title = title.rstrip(".,!?;:-")
    if len(title) > MAX_GENERATED_TITLE_LENGTH:
        title = title[:MAX_GENERATED_TITLE_LENGTH].rstrip()
        title = title.rstrip(".,!?;:-")
    if not title:
        return "New conversation"
    return title[0].upper() + title[1:]


def build_openai_input(
    db: Session, conversation_id: int, current_message: str, mode: str
) -> list[dict[str, str]]:
    recent_messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.desc(), models.Message.id.desc())
        .limit(CHAT_HISTORY_MAX_MESSAGES)
        .all()
    )
    previous_messages = list(reversed(recent_messages))

    history_messages: list[dict[str, str]] = []
    used_chars = 0
    for message in reversed(previous_messages):
        if message.role not in {"user", "assistant"} or not message.content:
            continue

        message_chars = len(message.content)
        if CHAT_HISTORY_MAX_CHARS and used_chars + message_chars > CHAT_HISTORY_MAX_CHARS:
            continue

        history_messages.append({"role": message.role, "content": message.content})
        used_chars += message_chars

    history_messages.reverse()

    openai_input = [{"role": "system", "content": build_system_prompt(mode)}]
    openai_input.extend(history_messages)
    openai_input.append({"role": "user", "content": current_message})
    return openai_input


def _get_field(value, *names):
    for name in names:
        if isinstance(value, dict) and name in value:
            return value[name]
        if hasattr(value, name):
            return getattr(value, name)
    return None


def _coerce_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def extract_usage_from_openai_event(event, fallback_model: str | None = None) -> AIUsage | None:
    response = _get_field(event, "response") or event
    usage = _get_field(response, "usage") or _get_field(event, "usage")
    if usage is None:
        return None

    prompt_tokens = _coerce_int(_get_field(usage, "input_tokens", "prompt_tokens"))
    completion_tokens = _coerce_int(_get_field(usage, "output_tokens", "completion_tokens"))
    total_tokens = _coerce_int(_get_field(usage, "total_tokens"))
    if not total_tokens:
        total_tokens = prompt_tokens + completion_tokens

    model = _get_field(response, "model") or _get_field(event, "model") or fallback_model
    if not model:
        return None

    return AIUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=str(model),
    )


def _get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def get_model_token_pricing(model: str) -> tuple[float, float]:
    raw_pricing = os.getenv("OPENAI_MODEL_PRICING_JSON")
    if raw_pricing:
        try:
            pricing_by_model = json.loads(raw_pricing)
            pricing = pricing_by_model.get(model) or pricing_by_model.get("default")
            if pricing:
                return (
                    float(pricing.get("input_cost_per_1m_tokens", pricing.get("input", 0.0))),
                    float(pricing.get("output_cost_per_1m_tokens", pricing.get("output", 0.0))),
                )
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("openai.pricing_config_invalid", extra={"request_id": get_request_id()})

    return (
        _get_float_env("OPENAI_INPUT_COST_PER_1M_TOKENS", DEFAULT_OPENAI_INPUT_COST_PER_1M_TOKENS),
        _get_float_env("OPENAI_OUTPUT_COST_PER_1M_TOKENS", DEFAULT_OPENAI_OUTPUT_COST_PER_1M_TOKENS),
    )


def estimate_usage_cost_usd(usage: AIUsage) -> float:
    input_cost_per_1m, output_cost_per_1m = get_model_token_pricing(usage.model)
    return round(
        (usage.prompt_tokens / 1_000_000 * input_cost_per_1m)
        + (usage.completion_tokens / 1_000_000 * output_cost_per_1m),
        8,
    )


async def stream_openai_text(
    openai_input: list[dict[str, str]],
    usage_callback: Callable[[AIUsage | None], None] | None = None,
):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")

    request_id = get_request_id()
    model = os.getenv("OPENAI_MODEL", OPENAI_MODEL)
    client = AsyncOpenAI()
    started_at = time.perf_counter()
    stream = await client.responses.create(
        model=model,
        input=openai_input,
        stream=True,
    )
    logger.info(
        "openai.call.ready",
        extra={
            "request_id": request_id,
            "model": model,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
        },
    )

    async for event in stream:
        if _get_field(event, "type") == "response.output_text.delta":
            yield _get_field(event, "delta") or ""
        usage = extract_usage_from_openai_event(event, fallback_model=model)
        if usage_callback and usage:
            usage_callback(usage)


async def iterate_stream_text(
    stream_text: StreamTextCallable,
    openai_input: list[dict[str, str]],
    usage_tracker: AIUsageTracker,
):
    try:
        stream = stream_text(openai_input, usage_callback=usage_tracker.capture)
    except TypeError:
        stream = stream_text(openai_input)

    async for chunk in stream:
        yield chunk


def record_ai_usage(
    db: Session,
    *,
    user_id: int,
    request_id: str | None,
    feature: str,
    usage: AIUsage | None,
    latency_ms: float,
) -> models.AIUsageRecord | None:
    if usage is None:
        return None

    estimated_cost_usd = estimate_usage_cost_usd(usage)
    record = models.AIUsageRecord(
        user_id=user_id,
        request_id=request_id,
        feature=feature,
        model=usage.model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        estimated_cost_usd=estimated_cost_usd,
        latency_ms=latency_ms,
    )
    db.add(record)
    db.commit()
    logger.info(
        "openai.usage",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "feature": feature,
            "model": usage.model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "latency_ms": round(latency_ms, 2),
        },
    )
    return record


def get_ai_usage_summary_for_user(db: Session, user_id: int) -> dict[str, float | int]:
    row = (
        db.query(
            func.coalesce(func.sum(models.AIUsageRecord.prompt_tokens), 0),
            func.coalesce(func.sum(models.AIUsageRecord.completion_tokens), 0),
            func.coalesce(func.sum(models.AIUsageRecord.total_tokens), 0),
            func.coalesce(func.sum(models.AIUsageRecord.estimated_cost_usd), 0.0),
            func.count(models.AIUsageRecord.id),
        )
        .filter(models.AIUsageRecord.user_id == user_id)
        .one()
    )
    return {
        "prompt_tokens": int(row[0] or 0),
        "completion_tokens": int(row[1] or 0),
        "total_tokens": int(row[2] or 0),
        "estimated_cost_usd": float(row[3] or 0.0),
        "requests": int(row[4] or 0),
    }


def get_daily_ai_usage_for_user(db: Session, user_id: int) -> list[dict[str, float | int | str]]:
    day = func.date(models.AIUsageRecord.created_at)
    rows = (
        db.query(
            day,
            func.coalesce(func.sum(models.AIUsageRecord.prompt_tokens), 0),
            func.coalesce(func.sum(models.AIUsageRecord.completion_tokens), 0),
            func.coalesce(func.sum(models.AIUsageRecord.total_tokens), 0),
            func.coalesce(func.sum(models.AIUsageRecord.estimated_cost_usd), 0.0),
            func.count(models.AIUsageRecord.id),
        )
        .filter(models.AIUsageRecord.user_id == user_id)
        .group_by(day)
        .order_by(day)
        .all()
    )
    return [
        {
            "date": row[0].isoformat() if isinstance(row[0], date) else str(row[0]),
            "prompt_tokens": int(row[1] or 0),
            "completion_tokens": int(row[2] or 0),
            "total_tokens": int(row[3] or 0),
            "estimated_cost_usd": float(row[4] or 0.0),
            "requests": int(row[5] or 0),
        }
        for row in rows
    ]


def persist_user_message(
    db: Session,
    *,
    conversation_id: int,
    user_id: int,
    content: str,
) -> None:
    db.add(
        models.Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=content,
        )
    )
    progress_service.update_progress_activity(db, user_id, messages_delta=1)
    db.commit()


def persist_assistant_message(
    db: Session,
    *,
    conversation_id: int,
    user_id: int,
    content: str,
    should_generate_title: bool,
    title_source: str,
) -> None:
    db.add(
        models.Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=content,
        )
    )
    if should_generate_title:
        (
            db.query(models.Conversation)
            .filter(
                models.Conversation.id == conversation_id,
                models.Conversation.user_id == user_id,
            )
            .update({"title": generate_conversation_title(title_source)})
        )
    db.commit()


def prepare_chat_stream(
    db: Session,
    *,
    conversation: models.Conversation,
    user_id: int,
    clean_message: str,
) -> list[dict[str, str]]:
    openai_input = build_openai_input(
        db,
        conversation.id,
        clean_message,
        conversation.mode,
    )
    persist_user_message(
        db,
        conversation_id=conversation.id,
        user_id=user_id,
        content=clean_message,
    )
    return openai_input


async def stream_chat_response(
    db: Session,
    *,
    openai_input: list[dict[str, str]],
    conversation_id: int,
    user_id: int,
    clean_message: str,
    should_generate_title: bool,
    is_disconnected: DisconnectCallable,
    stream_text: StreamTextCallable = stream_openai_text,
    request_id: str | None = None,
):
    chunks: list[str] = []
    started_at = time.perf_counter()
    model = os.getenv("OPENAI_MODEL", OPENAI_MODEL)
    outcome = "empty"
    usage_tracker = AIUsageTracker()
    request_id = request_id or get_request_id()
    request_id_token = set_request_id(request_id)
    logger.info(
        "chat_stream.start",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "model": model,
        },
    )
    try:
        try:
            async for chunk in iterate_stream_text(stream_text, openai_input, usage_tracker):
                if await is_disconnected():
                    outcome = "disconnected"
                    logger.info(
                        "chat_stream.disconnected",
                        extra={
                            "request_id": request_id,
                            "conversation_id": conversation_id,
                            "user_id": user_id,
                            "stream_outcome": outcome,
                        },
                    )
                    return
                if not chunk:
                    continue

                chunks.append(chunk)
                yield format_sse_data(chunk)
        except AuthenticationError:
            outcome = "error"
            logger.exception(
                "chat_stream.error",
                extra={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_outcome": outcome,
                    "reason": "openai_authentication_failed",
                },
            )
            yield format_sse_event("error", SAFE_STREAM_ERROR)
            return
        except APITimeoutError:
            outcome = "error"
            logger.exception(
                "chat_stream.error",
                extra={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_outcome": outcome,
                    "reason": "openai_timeout",
                },
            )
            yield format_sse_event("error", SAFE_STREAM_ERROR)
            return
        except APIConnectionError:
            outcome = "error"
            logger.exception(
                "chat_stream.error",
                extra={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_outcome": outcome,
                    "reason": "openai_connection_failed",
                },
            )
            yield format_sse_event("error", SAFE_STREAM_ERROR)
            return
        except APIStatusError:
            outcome = "error"
            logger.exception(
                "chat_stream.error",
                extra={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_outcome": outcome,
                    "reason": "openai_status_error",
                },
            )
            yield format_sse_event("error", SAFE_STREAM_ERROR)
            return
        except APIError:
            outcome = "error"
            logger.exception(
                "chat_stream.error",
                extra={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_outcome": outcome,
                    "reason": "openai_api_error",
                },
            )
            yield format_sse_event("error", SAFE_STREAM_ERROR)
            return
        except OpenAIError:
            outcome = "error"
            logger.exception(
                "chat_stream.error",
                extra={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_outcome": outcome,
                    "reason": "openai_error",
                },
            )
            yield format_sse_event("error", SAFE_STREAM_ERROR)
            return
        except Exception:
            outcome = "error"
            logger.exception(
                "chat_stream.error",
                extra={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "model": model,
                    "stream_outcome": outcome,
                    "reason": "unexpected_error",
                },
            )
            yield format_sse_event("error", SAFE_STREAM_ERROR)
            return

        assistant_content = "".join(chunks).strip()
        if assistant_content:
            outcome = "success"
            persist_assistant_message(
                db,
                conversation_id=conversation_id,
                user_id=user_id,
                content=assistant_content,
                should_generate_title=should_generate_title,
                title_source=clean_message,
            )
        record_ai_usage(
            db,
            user_id=user_id,
            request_id=request_id,
            feature="chat",
            usage=usage_tracker.usage,
            latency_ms=(time.perf_counter() - started_at) * 1000,
        )
        yield format_sse_event("done", "done")
    finally:
        logger.info(
            "chat_stream.end",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "model": model,
                "stream_outcome": outcome,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
        )
        reset_request_id(request_id_token)
        db.close()
