from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import auth, models, progress as progress_service, schemas
from app.database import get_db


router = APIRouter(prefix="/progress", tags=["progress"])


def serialize_achievement(item: models.UserAchievement) -> schemas.AchievementRead:
    return schemas.AchievementRead(
        id=item.achievement.id,
        name=item.achievement.name,
        description=item.achievement.description,
        icon=item.achievement.icon,
        condition_type=item.achievement.condition_type,
        condition_value=item.achievement.condition_value,
        earned_at=item.earned_at,
    )


def serialize_progress(progress: models.UserProgress) -> schemas.UserProgressStats:
    return schemas.UserProgressStats(
        sessions_count=progress.sessions_count,
        messages_count=progress.messages_count,
        correct_answers=progress.correct_answers,
        incorrect_answers=progress.incorrect_answers,
        time_spent_seconds=progress.time_spent_seconds,
        current_streak_days=progress.current_streak_days,
        last_streak_date=progress.last_streak_date,
        last_activity_at=progress.last_activity_at,
    )


@router.get("", response_model=schemas.ProgressResponse)
def get_progress(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    progress = progress_service.get_or_create_progress(db, current_user.id)
    progress_service.evaluate_achievements(progress, db)
    db.flush()
    db.refresh(progress)

    earned = (
        db.query(models.UserAchievement)
        .filter(models.UserAchievement.user_id == current_user.id)
        .all()
    )
    new_items = [item for item in earned if not item.notified]
    achievements = [serialize_achievement(item) for item in earned]
    new_achievements = [serialize_achievement(item) for item in new_items]

    for item in new_items:
        item.notified = True

    db.commit()

    return schemas.ProgressResponse(
        progress=serialize_progress(progress),
        achievements=achievements,
        new_achievements=new_achievements,
    )
