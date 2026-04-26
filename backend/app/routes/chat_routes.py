import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import auth, models
from app.database import get_db


router = APIRouter(tags=["chat"])

FAKE_ASSISTANT_RESPONSE = "This is a streamed assistant response."


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
            for chunk in FAKE_ASSISTANT_RESPONSE.split():
                if await request.is_disconnected():
                    return
                chunks.append(chunk)
                yield f"data: {chunk}\n\n"
                await asyncio.sleep(0.05)

            assistant_message = models.Message(
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=" ".join(chunks),
            )
            db.add(assistant_message)
            db.commit()
        finally:
            db.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
