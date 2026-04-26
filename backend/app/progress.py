from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import models


DEFAULT_ACHIEVEMENTS = [
    {
        "id": 1,
        "name": "First Session",
        "description": "Start your first learning conversation.",
        "icon": "book",
        "condition_type": "sessions_count",
        "condition_value": 1,
    },
    {
        "id": 2,
        "name": "Conversation Starter",
        "description": "Send your first message.",
        "icon": "message",
        "condition_type": "messages_count",
        "condition_value": 1,
    },
    {
        "id": 3,
        "name": "Practice Streak",
        "description": "Send 10 messages across your practice sessions.",
        "icon": "spark",
        "condition_type": "messages_count",
        "condition_value": 10,
    },
]


def ensure_default_achievements(db: Session) -> None:
    for achievement_data in DEFAULT_ACHIEVEMENTS:
        achievement = db.get(models.Achievement, achievement_data["id"])
        if not achievement:
            db.add(models.Achievement(**achievement_data))


def get_or_create_progress(db: Session, user_id: int) -> models.UserProgress:
    progress = db.get(models.UserProgress, user_id)
    if progress:
        return progress

    progress = models.UserProgress(user_id=user_id)
    db.add(progress)
    db.flush()
    return progress


def update_progress_activity(
    db: Session,
    user_id: int,
    *,
    sessions_delta: int = 0,
    messages_delta: int = 0,
) -> models.UserProgress:
    progress = get_or_create_progress(db, user_id)
    progress.sessions_count += sessions_delta
    progress.messages_count += messages_delta
    progress.last_activity_at = datetime.now(timezone.utc)
    award_earned_achievements(db, progress)
    return progress


def award_earned_achievements(db: Session, progress: models.UserProgress) -> None:
    ensure_default_achievements(db)
    achievements = db.query(models.Achievement).all()
    earned_ids = {
        item.achievement_id
        for item in db.query(models.UserAchievement)
        .filter(models.UserAchievement.user_id == progress.user_id)
        .all()
    }

    for achievement in achievements:
        if achievement.id in earned_ids:
            continue
        current_value = getattr(progress, achievement.condition_type, 0)
        if current_value >= achievement.condition_value:
            db.add(
                models.UserAchievement(
                    user_id=progress.user_id,
                    achievement_id=achievement.id,
                )
            )
