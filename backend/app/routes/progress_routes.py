from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import re

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


def make_badge_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def serialize_badge(
    achievement: models.Achievement,
    earned_by_achievement_id: dict[int, models.UserAchievement],
) -> schemas.BadgeRead:
    earned_item = earned_by_achievement_id.get(achievement.id)
    return schemas.BadgeRead(
        id=achievement.id,
        key=make_badge_key(achievement.name),
        title=achievement.name,
        description=achievement.description,
        icon=achievement.icon,
        condition_type=achievement.condition_type,
        condition_value=achievement.condition_value,
        earned=earned_item is not None,
        earned_at=earned_item.earned_at if earned_item else None,
    )


def serialize_progress(progress: models.UserProgress) -> schemas.UserProgressStats:
    xp_progress = progress_service.build_xp_progress(progress.xp_points)
    return schemas.UserProgressStats(
        sessions_count=progress.sessions_count,
        messages_count=progress.messages_count,
        lessons_completed=progress.lessons_completed,
        correct_answers=progress.correct_answers,
        incorrect_answers=progress.incorrect_answers,
        time_spent_seconds=progress.time_spent_seconds,
        xp_points=progress.xp_points,
        level=progress.level,
        total_xp=xp_progress["total_xp"],
        xp_into_level=xp_progress["xp_into_level"],
        xp_required_for_next_level=xp_progress["xp_required_for_next_level"],
        progress_percent=xp_progress["progress_percent"],
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
    earned_by_achievement_id = {item.achievement_id: item for item in earned}
    all_achievements = db.query(models.Achievement).order_by(models.Achievement.id).all()
    new_items = [item for item in earned if not item.notified]
    achievements = [serialize_achievement(item) for item in earned]
    badges = [
        serialize_badge(achievement, earned_by_achievement_id)
        for achievement in all_achievements
    ]
    new_achievements = [serialize_achievement(item) for item in new_items]

    for item in new_items:
        item.notified = True

    db.commit()

    return schemas.ProgressResponse(
        progress=serialize_progress(progress),
        achievements=achievements,
        badges=badges,
        new_achievements=new_achievements,
    )


@router.post("/activity", response_model=schemas.UserProgressStats)
def record_activity(
    activity: schemas.ProgressActivityRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    progress = progress_service.record_active_time(
        db,
        current_user.id,
        activity.active_seconds,
    )
    db.commit()
    db.refresh(progress)
    return serialize_progress(progress)
