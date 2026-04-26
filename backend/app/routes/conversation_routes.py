from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db


router = APIRouter(prefix="/conversations", tags=["conversations"])
ALLOWED_CONVERSATION_MODES = {"chat", "learn"}


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


@router.post("", response_model=schemas.ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conversation_in: schemas.ConversationCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    conversation = models.Conversation(title=conversation_in.title, user_id=current_user.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("", response_model=list[schemas.ConversationRead])
def list_conversations(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == current_user.id)
        .order_by(models.Conversation.created_at.desc())
        .all()
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
