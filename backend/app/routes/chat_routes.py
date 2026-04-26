import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
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

from app import auth, models
from app.database import get_db


router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
SAFE_STREAM_ERROR = "Error: Unable to generate response."
MESSAGE_TOO_LONG_ERROR = "Error: Message is too long. Please keep it under 2000 characters."
RATE_LIMIT_ERROR = "Error: Too many requests. Please wait a moment."
MAX_CHAT_MESSAGE_LENGTH = 2000
CHAT_STREAM_RATE_LIMIT = 10
CHAT_STREAM_RATE_WINDOW_SECONDS = 60
_rate_limit_buckets: dict[int, list[float]] = {}


def _get_owned_conversation(db: Session, conversation_id: int, user_id: int) -> models.Conversation:
    conversation = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == user_id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


def _format_sse_data(value: str) -> str:
    lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "".join(f"data: {line}\n" for line in lines) + "\n"


def _build_openai_input(
    db: Session, conversation_id: int, current_message: str
) -> list[dict[str, str]]:
    previous_messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.asc())
        .all()
    )
    openai_input = [
        {"role": message.role, "content": message.content}
        for message in previous_messages
        if message.role in {"user", "assistant"} and message.content
    ]
    openai_input.append({"role": "user", "content": current_message})
    return openai_input


def _is_rate_limited(user_id: int) -> bool:
    now = time.monotonic()
    window_start = now - CHAT_STREAM_RATE_WINDOW_SECONDS
    timestamps = [
        timestamp
        for timestamp in _rate_limit_buckets.get(user_id, [])
        if timestamp > window_start
    ]

    if len(timestamps) >= CHAT_STREAM_RATE_LIMIT:
        _rate_limit_buckets[user_id] = timestamps
        return True

    timestamps.append(now)
    _rate_limit_buckets[user_id] = timestamps
    return False


async def _stream_openai_text(openai_input: list[dict[str, str]]):
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


@router.get("/chat-stream")
async def chat_stream(
    request: Request,
    conversation_id: int,
    message: str,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    clean_message = message.strip()
    if not clean_message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")

    current_user = auth.get_user_from_token(db, token)
    user_id = current_user.id
    _get_owned_conversation(db, conversation_id, user_id)

    if len(clean_message) > MAX_CHAT_MESSAGE_LENGTH:
        logger.info(
            "Rejected chat stream message over length limit",
            extra={"conversation_id": conversation_id, "user_id": user_id},
        )
        return StreamingResponse(
            iter([_format_sse_data(MESSAGE_TOO_LONG_ERROR)]),
            media_type="text/event-stream",
        )

    if _is_rate_limited(user_id):
        logger.info(
            "Rejected chat stream request due to rate limit",
            extra={"conversation_id": conversation_id, "user_id": user_id},
        )
        return StreamingResponse(
            iter([_format_sse_data(RATE_LIMIT_ERROR)]),
            media_type="text/event-stream",
        )

    openai_input = _build_openai_input(db, conversation_id, clean_message)

    user_message = models.Message(
        conversation_id=conversation_id,
        user_id=user_id,
        role="user",
        content=clean_message,
    )
    db.add(user_message)
    db.commit()

    async def event_generator():
        chunks: list[str] = []
        try:
            try:
                async for chunk in _stream_openai_text(openai_input):
                    if await request.is_disconnected():
                        logger.info(
                            "Client disconnected from chat stream",
                            extra={"conversation_id": conversation_id, "user_id": user_id},
                        )
                        return
                    if not chunk:
                        continue

                    chunks.append(chunk)
                    yield _format_sse_data(chunk)
            except AuthenticationError:
                logger.exception("OpenAI authentication failed")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except APITimeoutError:
                logger.exception("OpenAI request timed out")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except APIConnectionError:
                logger.exception("OpenAI network connection failed")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except APIStatusError:
                logger.exception("OpenAI API returned an error status")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except APIError:
                logger.exception("OpenAI API error while streaming")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except OpenAIError:
                logger.exception("OpenAI error while streaming")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return
            except Exception:
                logger.exception("Unexpected error while streaming chat response")
                yield _format_sse_data(SAFE_STREAM_ERROR)
                return

            assistant_content = "".join(chunks).strip()
            if not assistant_content:
                return

            assistant_message = models.Message(
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=assistant_content,
            )
            db.add(assistant_message)
            db.commit()
        finally:
            db.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
