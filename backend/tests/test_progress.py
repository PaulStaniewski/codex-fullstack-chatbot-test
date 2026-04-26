from datetime import datetime, timezone

from app import models
from app.progress import (
    award_earned_achievements,
    get_progress_condition_value,
    update_learning_streak,
    update_time_spent,
)


def _register_and_login(client, email="progress@example.com"):
    client.post(
        "/register",
        json={"email": email, "password": "password123"},
    )
    login_response = client.post(
        "/login",
        json={"email": email, "password": "password123"},
    )
    return login_response.json()["access_token"]


async def _fake_openai_stream(_openai_input):
    yield "Assistant reply"


def test_progress_defaults(client):
    token = _register_and_login(client)

    response = client.get("/progress", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["sessions_count"] == 0
    assert data["messages_count"] == 0
    assert data["correct_answers"] == 0
    assert data["incorrect_answers"] == 0
    assert data["time_spent_seconds"] == 0
    assert data["current_streak_days"] == 0
    assert data["last_streak_date"] is None
    assert data["achievements"] == []


def test_progress_tracks_sessions_messages_and_achievements(client, monkeypatch):
    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", _fake_openai_stream)
    token = _register_and_login(client)

    conversation_response = client.post(
        "/conversations",
        json={"title": "Practice"},
        headers={"Authorization": f"Bearer {token}"},
    )
    conversation_id = conversation_response.json()["id"]
    client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "hello", "token": token},
    )

    response = client.get("/progress", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    achievement_names = {achievement["name"] for achievement in data["achievements"]}
    assert data["sessions_count"] == 1
    assert data["messages_count"] == 1
    assert data["current_streak_days"] == 1
    assert data["last_streak_date"] is not None
    assert data["last_activity_at"] is not None
    assert "First Session" in achievement_names
    assert "Conversation Starter" in achievement_names


def test_progress_requires_auth(client):
    response = client.get("/progress")

    assert response.status_code == 401


def test_update_time_spent_increments_under_threshold():
    progress = models.UserProgress(
        user_id=1,
        time_spent_seconds=30,
        last_activity_at=datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc),
    )

    update_time_spent(progress, datetime(2026, 4, 26, 12, 5, tzinfo=timezone.utc))

    assert progress.time_spent_seconds == 330
    assert progress.last_activity_at == datetime(2026, 4, 26, 12, 5, tzinfo=timezone.utc)


def test_update_time_spent_skips_after_inactivity():
    progress = models.UserProgress(
        user_id=1,
        time_spent_seconds=30,
        last_activity_at=datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc),
    )

    update_time_spent(progress, datetime(2026, 4, 26, 12, 11, tzinfo=timezone.utc))

    assert progress.time_spent_seconds == 30
    assert progress.last_activity_at == datetime(2026, 4, 26, 12, 11, tzinfo=timezone.utc)


def test_update_time_spent_skips_negative_elapsed_time():
    progress = models.UserProgress(
        user_id=1,
        time_spent_seconds=30,
        last_activity_at=datetime(2026, 4, 26, 12, 5, tzinfo=timezone.utc),
    )

    update_time_spent(progress, datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc))

    assert progress.time_spent_seconds == 30
    assert progress.last_activity_at == datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)


def test_update_learning_streak_first_activity_sets_one_day():
    progress = models.UserProgress(user_id=1)

    update_learning_streak(progress, datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc))

    assert progress.current_streak_days == 1
    assert progress.last_streak_date.isoformat() == "2026-04-26"


def test_update_learning_streak_consecutive_day_increments():
    progress = models.UserProgress(user_id=1, current_streak_days=2)
    progress.last_streak_date = datetime(2026, 4, 25, tzinfo=timezone.utc).date()

    update_learning_streak(progress, datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc))

    assert progress.current_streak_days == 3
    assert progress.last_streak_date.isoformat() == "2026-04-26"


def test_update_learning_streak_same_day_does_not_increment():
    progress = models.UserProgress(user_id=1, current_streak_days=2)
    progress.last_streak_date = datetime(2026, 4, 26, tzinfo=timezone.utc).date()

    update_learning_streak(progress, datetime(2026, 4, 26, 18, 0, tzinfo=timezone.utc))

    assert progress.current_streak_days == 2
    assert progress.last_streak_date.isoformat() == "2026-04-26"


def test_update_learning_streak_gap_resets():
    progress = models.UserProgress(user_id=1, current_streak_days=4)
    progress.last_streak_date = datetime(2026, 4, 20, tzinfo=timezone.utc).date()

    update_learning_streak(progress, datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc))

    assert progress.current_streak_days == 1
    assert progress.last_streak_date.isoformat() == "2026-04-26"


def test_achievement_granted_when_threshold_reached(client):
    token = _register_and_login(client)
    response = client.post(
        "/conversations",
        json={"title": "Practice"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    from app.database import get_db

    db = next(client.app.dependency_overrides[get_db]())
    try:
        progress = db.query(models.UserProgress).first()
        progress.current_streak_days = 3
        award_earned_achievements(db, progress)
        db.commit()

        earned_names = {
            item.achievement.name
            for item in db.query(models.UserAchievement)
            .filter(models.UserAchievement.user_id == progress.user_id)
            .all()
        }
    finally:
        db.close()

    assert "Consistent Learner" in earned_names


def test_achievement_not_granted_twice(client):
    token = _register_and_login(client)
    response = client.post(
        "/conversations",
        json={"title": "Practice"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    from app.database import get_db

    db = next(client.app.dependency_overrides[get_db]())
    try:
        progress = db.query(models.UserProgress).first()
        progress.current_streak_days = 3
        award_earned_achievements(db, progress)
        award_earned_achievements(db, progress)
        db.commit()

        achievements = (
            db.query(models.UserAchievement)
            .join(models.Achievement)
            .filter(
                models.UserAchievement.user_id == progress.user_id,
                models.Achievement.name == "Consistent Learner",
            )
            .all()
        )
    finally:
        db.close()

    assert len(achievements) == 1


def test_progress_condition_mapping():
    progress = models.UserProgress(
        user_id=1,
        current_streak_days=7,
        time_spent_seconds=3600,
        messages_count=50,
    )

    assert get_progress_condition_value(progress, "streak_days") == 7
    assert get_progress_condition_value(progress, "time_spent_seconds") == 3600
    assert get_progress_condition_value(progress, "messages_count") == 50
