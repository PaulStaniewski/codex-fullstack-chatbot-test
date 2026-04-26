from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db


router = APIRouter(prefix="/messages", tags=["messages"])


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


@router.post("", response_model=schemas.MessageRead, status_code=status.HTTP_201_CREATED)
def create_message(
    message_in: schemas.MessageCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_conversation(db, message_in.conversation_id, current_user.id)

    message = models.Message(
        conversation_id=message_in.conversation_id,
        user_id=current_user.id,
        role=message_in.role,
        content=message_in.content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("", response_model=list[schemas.MessageRead])
def list_messages(
    conversation_id: int | None = Query(default=None),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Message).filter(models.Message.user_id == current_user.id)
    if conversation_id is not None:
        _get_owned_conversation(db, conversation_id, current_user.id)
        query = query.filter(models.Message.conversation_id == conversation_id)
    return query.order_by(models.Message.created_at.asc()).all()
