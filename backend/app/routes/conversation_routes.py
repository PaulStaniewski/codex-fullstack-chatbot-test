import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import auth, models, progress as progress_service, schemas
from app.database import get_db


router = APIRouter(prefix="/conversations", tags=["conversations"])
ALLOWED_CONVERSATION_MODES = {"chat", "learn", "interview"}
EXPORT_FORMATS = {"txt", "md", "json"}
DEFAULT_CONVERSATIONS_LIMIT = 50
MAX_CONVERSATIONS_LIMIT = 100


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


def _build_export_content(
    conversation: models.Conversation,
    messages: list[models.Message],
    export_format: str,
) -> tuple[str, str]:
    if export_format == "json":
        content = json.dumps(
            {
                "conversation": {
                    "id": conversation.id,
                    "title": conversation.title,
                    "mode": conversation.mode,
                    "created_at": conversation.created_at.isoformat(),
                },
                "messages": [
                    {
                        "id": message.id,
                        "role": message.role,
                        "content": message.content,
                        "created_at": message.created_at.isoformat(),
                    }
                    for message in messages
                ],
            },
            indent=2,
        )
        return content, "application/json"

    if export_format == "md":
        lines = [f"# {conversation.title}", ""]
        for message in messages:
            role = "User" if message.role == "user" else "Assistant"
            lines.extend(
                [
                    f"## {role}",
                    f"_ {message.created_at.isoformat()} _",
                    "",
                    message.content,
                    "",
                ]
            )
        return "\n".join(lines), "text/markdown; charset=utf-8"

    lines = [conversation.title, ""]
    for message in messages:
        role = "User" if message.role == "user" else "Assistant"
        lines.extend(
            [
                f"{role} ({message.created_at.isoformat()}):",
                message.content,
                "",
            ]
        )
    return "\n".join(lines), "text/plain; charset=utf-8"


@router.post("", response_model=schemas.ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conversation_in: schemas.ConversationCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    conversation = models.Conversation(title=conversation_in.title, user_id=current_user.id)
    db.add(conversation)
    progress_service.update_progress_activity(db, current_user.id, sessions_delta=1)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("", response_model=list[schemas.ConversationRead])
def list_conversations(
    limit: int = Query(default=DEFAULT_CONVERSATIONS_LIMIT, ge=1, le=MAX_CONVERSATIONS_LIMIT),
    offset: int = Query(default=0, ge=0),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == current_user.id)
        .order_by(
            models.Conversation.is_pinned.desc(),
            models.Conversation.created_at.desc(),
            models.Conversation.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{conversation_id}/export")
def export_conversation(
    conversation_id: int,
    format: str = Query(default="txt"),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if format not in EXPORT_FORMATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid export format")

    conversation = _get_owned_conversation(db, conversation_id, current_user.id)
    messages = (
        db.query(models.Message)
        .filter(
            models.Message.conversation_id == conversation.id,
            models.Message.user_id == current_user.id,
        )
        .order_by(models.Message.created_at.asc())
        .all()
    )
    content, media_type = _build_export_content(conversation, messages, format)
    filename = f"conversation-{conversation.id}.{format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{conversation_id}", response_model=schemas.ConversationRead)
def update_conversation(
    conversation_id: int,
    conversation_in: schemas.ConversationUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(db, conversation_id, current_user.id)
    conversation.title = conversation_in.title
    db.commit()
    db.refresh(conversation)
    return conversation


@router.patch("/{conversation_id}/mode", response_model=schemas.ConversationRead)
def update_conversation_mode(
    conversation_id: int,
    mode_in: schemas.ConversationModeUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if mode_in.mode not in ALLOWED_CONVERSATION_MODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation mode")

    conversation = _get_owned_conversation(db, conversation_id, current_user.id)
    conversation.mode = mode_in.mode
    db.commit()
    db.refresh(conversation)
    return conversation


@router.patch("/{conversation_id}/pin", response_model=schemas.ConversationRead)
def toggle_conversation_pin(
    conversation_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(db, conversation_id, current_user.id)
    conversation.is_pinned = not conversation.is_pinned
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned_conversation(db, conversation_id, current_user.id)
    db.delete(conversation)
    db.commit()
    return {"success": True}
