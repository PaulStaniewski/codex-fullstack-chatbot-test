from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models


ACTIVE_TIME_THRESHOLD_SECONDS = 10 * 60

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
    {
        "id": 4,
        "name": "Consistent Learner",
        "description": "Practice for 3 days in a row.",
        "icon": "streak",
        "condition_type": "streak_days",
        "condition_value": 3,
    },
    {
        "id": 5,
        "name": "Dedicated",
        "description": "Practice for 7 days in a row.",
        "icon": "flame",
        "condition_type": "streak_days",
        "condition_value": 7,
    },
    {
        "id": 6,
        "name": "Machine",
        "description": "Practice for 30 days in a row.",
        "icon": "gear",
        "condition_type": "streak_days",
        "condition_value": 30,
    },
    {
        "id": 7,
        "name": "Marathon",
        "description": "Spend 1 hour actively learning.",
        "icon": "timer",
        "condition_type": "time_spent_seconds",
        "condition_value": 3600,
    },
    {
        "id": 8,
        "name": "Communicator",
        "description": "Send 50 messages.",
        "icon": "chat",
        "condition_type": "messages_count",
        "condition_value": 50,
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
    now: datetime | None = None,
) -> models.UserProgress:
    progress = get_or_create_progress(db, user_id)
    current_time = now or datetime.now(timezone.utc)
    if messages_delta:
        update_time_spent(progress, current_time)
    else:
        progress.last_activity_at = current_time
    update_learning_streak(progress, current_time)
    progress.sessions_count += sessions_delta
    progress.messages_count += messages_delta
    award_earned_achievements(db, progress)
    return progress


def update_time_spent(progress: models.UserProgress, now: datetime | None = None) -> None:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    last_activity_at = progress.last_activity_at
    if last_activity_at and last_activity_at.tzinfo is None:
        last_activity_at = last_activity_at.replace(tzinfo=timezone.utc)

    if last_activity_at:
        elapsed_seconds = int((current_time - last_activity_at).total_seconds())
        if 0 <= elapsed_seconds < ACTIVE_TIME_THRESHOLD_SECONDS:
            progress.time_spent_seconds += elapsed_seconds

    progress.last_activity_at = current_time


def update_learning_streak(progress: models.UserProgress, now: datetime | None = None) -> None:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    today = current_time.astimezone(timezone.utc).date()
    last_streak_date = progress.last_streak_date

    if last_streak_date == today:
        return

    if last_streak_date == today - timedelta(days=1):
        progress.current_streak_days += 1
    else:
        progress.current_streak_days = 1

    progress.last_streak_date = today


def get_progress_condition_value(progress: models.UserProgress, condition_type: str) -> int:
    if condition_type == "streak_days":
        return progress.current_streak_days
    return getattr(progress, condition_type, 0)


def award_earned_achievements(db: Session, progress: models.UserProgress) -> None:
    ensure_default_achievements(db)
    achievements = db.query(models.Achievement).all()
    earned_ids = {
        item.achievement_id
        for item in db.query(models.UserAchievement)
        .filter(models.UserAchievement.user_id == progress.user_id)
        .all()
    }
    earned_ids.update(
        item.achievement_id
        for item in db.new
        if isinstance(item, models.UserAchievement) and item.user_id == progress.user_id
    )

    for achievement in achievements:
        if achievement.id in earned_ids:
            continue
        current_value = get_progress_condition_value(progress, achievement.condition_type)
        if current_value >= achievement.condition_value:
            db.add(
                models.UserAchievement(
                    user_id=progress.user_id,
                    achievement_id=achievement.id,
                )
            )
            earned_ids.add(achievement.id)
