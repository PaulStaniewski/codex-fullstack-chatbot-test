import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    AsyncOpenAI,
    OpenAIError,
)
from sqlalchemy.orm import Session

from app import models, progress as progress_service


logger = logging.getLogger(__name__)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
SAFE_STREAM_ERROR = "Error: Unable to generate response."
MESSAGE_TOO_LONG_ERROR = "Error: Message is too long. Please keep it under 2000 characters."
RATE_LIMIT_ERROR = "Error: Too many requests. Please wait a moment."
MAX_CHAT_MESSAGE_LENGTH = 2000
MAX_GENERATED_TITLE_LENGTH = 60
CHAT_STREAM_RATE_LIMIT = 10
CHAT_STREAM_RATE_WINDOW_SECONDS = 60

StreamTextCallable = Callable[[list[dict[str, str]]], AsyncIterator[str]]
DisconnectCallable = Callable[[], Awaitable[bool]]


def format_sse_data(value: str) -> str:
    lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "".join(f"data: {line}\n" for line in lines) + "\n"


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
    previous_messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.asc())
        .all()
    )
    openai_input = [{"role": "system", "content": build_system_prompt(mode)}]
    openai_input.extend([
        {"role": message.role, "content": message.content}
        for message in previous_messages
        if message.role in {"user", "assistant"} and message.content
    ])
    openai_input.append({"role": "user", "content": current_message})
    return openai_input


async def stream_openai_text(openai_input: list[dict[str, str]]):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = AsyncOpenAI()
    stream = await client.responses.create(
        model=os.getenv("OPENAI_MODEL", OPENAI_MODEL),
        input=openai_input,
        stream=True,
    )

    async for event in stream:
        if event.type == "response.output_text.delta":
            yield event.delta


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
):
    chunks: list[str] = []
    try:
        try:
            async for chunk in stream_text(openai_input):
                if await is_disconnected():
                    logger.info(
                        "Client disconnected from chat stream",
                        extra={"conversation_id": conversation_id, "user_id": user_id},
                    )
                    return
                if not chunk:
                    continue

                chunks.append(chunk)
                yield format_sse_data(chunk)
        except AuthenticationError:
            logger.exception("OpenAI authentication failed")
            yield format_sse_data(SAFE_STREAM_ERROR)
            return
        except APITimeoutError:
            logger.exception("OpenAI request timed out")
            yield format_sse_data(SAFE_STREAM_ERROR)
            return
        except APIConnectionError:
            logger.exception("OpenAI network connection failed")
            yield format_sse_data(SAFE_STREAM_ERROR)
            return
        except APIStatusError:
            logger.exception("OpenAI API returned an error status")
            yield format_sse_data(SAFE_STREAM_ERROR)
            return
        except APIError:
            logger.exception("OpenAI API error while streaming")
            yield format_sse_data(SAFE_STREAM_ERROR)
            return
        except OpenAIError:
            logger.exception("OpenAI error while streaming")
            yield format_sse_data(SAFE_STREAM_ERROR)
            return
        except Exception:
            logger.exception("Unexpected error while streaming chat response")
            yield format_sse_data(SAFE_STREAM_ERROR)
            return

        assistant_content = "".join(chunks).strip()
        if not assistant_content:
            return

        persist_assistant_message(
            db,
            conversation_id=conversation_id,
            user_id=user_id,
            content=assistant_content,
            should_generate_title=should_generate_title,
            title_source=clean_message,
        )
    finally:
        db.close()
