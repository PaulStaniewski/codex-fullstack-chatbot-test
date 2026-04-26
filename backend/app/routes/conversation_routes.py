from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db


router = APIRouter(prefix="/conversations", tags=["conversations"])


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
