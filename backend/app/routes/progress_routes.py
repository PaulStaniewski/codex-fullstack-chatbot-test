from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import auth, models, progress as progress_service, schemas
from app.database import get_db


router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=schemas.UserProgressRead)
def get_progress(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    progress = progress_service.get_or_create_progress(db, current_user.id)
    progress_service.award_earned_achievements(db, progress)
    db.commit()
    db.refresh(progress)

    earned = (
        db.query(models.UserAchievement)
        .filter(models.UserAchievement.user_id == current_user.id)
        .all()
    )
    achievements = [
        schemas.AchievementRead(
            id=item.achievement.id,
            name=item.achievement.name,
            description=item.achievement.description,
            icon=item.achievement.icon,
            condition_type=item.achievement.condition_type,
            condition_value=item.achievement.condition_value,
            earned_at=item.earned_at,
        )
        for item in earned
    ]

    return schemas.UserProgressRead(
        sessions_count=progress.sessions_count,
        messages_count=progress.messages_count,
        correct_answers=progress.correct_answers,
        incorrect_answers=progress.incorrect_answers,
        time_spent_seconds=progress.time_spent_seconds,
        last_activity_at=progress.last_activity_at,
        achievements=achievements,
    )
