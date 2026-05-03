import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import auth, models
from app.database import get_db
from app.observability import get_request_id
from app.services import chat_service


router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

SAFE_STREAM_ERROR = chat_service.SAFE_STREAM_ERROR
MESSAGE_TOO_LONG_ERROR = chat_service.MESSAGE_TOO_LONG_ERROR
RATE_LIMIT_ERROR = chat_service.RATE_LIMIT_ERROR
MAX_CHAT_MESSAGE_LENGTH = chat_service.MAX_CHAT_MESSAGE_LENGTH
CHAT_STREAM_RATE_LIMIT = chat_service.CHAT_STREAM_RATE_LIMIT
CHAT_STREAM_RATE_WINDOW_SECONDS = chat_service.CHAT_STREAM_RATE_WINDOW_SECONDS
_rate_limit_buckets: dict[int, list[float]] = {}

_format_sse_data = chat_service.format_sse_data
_format_sse_event = chat_service.format_sse_event
build_system_prompt = chat_service.build_system_prompt
generate_conversation_title = chat_service.generate_conversation_title
_build_openai_input = chat_service.build_openai_input
_stream_openai_text = chat_service.stream_openai_text


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

    current_user = auth.get_user_from_sse_token(db, token)
    user_id = current_user.id
    conversation = _get_owned_conversation(db, conversation_id, user_id)
    should_generate_title = not conversation.title.strip()

    if len(clean_message) > MAX_CHAT_MESSAGE_LENGTH:
        logger.info(
            "chat_stream.error",
            extra={
                "request_id": get_request_id(),
                "conversation_id": conversation_id,
                "user_id": user_id,
                "stream_outcome": "rejected",
                "reason": "message_too_long",
            },
        )
        return StreamingResponse(
            iter([_format_sse_event("error", MESSAGE_TOO_LONG_ERROR)]),
            media_type="text/event-stream",
        )

    if _is_rate_limited(user_id):
        logger.info(
            "chat_stream.error",
            extra={
                "request_id": get_request_id(),
                "conversation_id": conversation_id,
                "user_id": user_id,
                "stream_outcome": "rejected",
                "reason": "rate_limited",
            },
        )
        return StreamingResponse(
            iter([_format_sse_event("error", RATE_LIMIT_ERROR)]),
            media_type="text/event-stream",
        )

    openai_input = chat_service.prepare_chat_stream(
        db,
        conversation=conversation,
        user_id=user_id,
        clean_message=clean_message,
    )

    return StreamingResponse(
        chat_service.stream_chat_response(
            db,
            openai_input=openai_input,
            conversation_id=conversation_id,
            user_id=user_id,
            clean_message=clean_message,
            should_generate_title=should_generate_title,
            is_disconnected=request.is_disconnected,
            stream_text=_stream_openai_text,
            request_id=get_request_id(),
        ),
        media_type="text/event-stream",
    )
