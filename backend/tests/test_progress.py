from datetime import datetime, timezone

from app import models
from app.progress import (
    XP_PER_ACHIEVEMENT,
    XP_PER_MESSAGE,
    XP_PER_SESSION,
    calculate_level,
    evaluate_achievements,
    get_progress_condition_value,
    update_progress_activity,
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
    assert data["progress"]["sessions_count"] == 0
    assert data["progress"]["messages_count"] == 0
    assert data["progress"]["correct_answers"] == 0
    assert data["progress"]["incorrect_answers"] == 0
    assert data["progress"]["time_spent_seconds"] == 0
    assert data["progress"]["xp_points"] == 0
    assert data["progress"]["level"] == 1
    assert data["progress"]["current_streak_days"] == 0
    assert data["progress"]["last_streak_date"] is None
    assert data["achievements"] == []
    assert data["new_achievements"] == []


def test_progress_tracks_sessions_messages_and_achievements(client, monkeypatch):
    monkeypatch.setattr("app.routes.chat_routes._stream_openai_text", _fake_openai_stream)
    token = _register_and_login(client)

    conversation_response = client.post(
        "/conversations",
        json={"title": "Practice"},
        headers={"Authorization": f"Bearer {token}"},
    )
    conversation_id = conversation_response.json()["id"]
    stream_response = client.get(
        "/chat-stream",
        params={"conversation_id": conversation_id, "message": "hello", "token": token},
    )
    assert stream_response.status_code == 200
    assert "Assistant reply" in stream_response.text

    response = client.get("/progress", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    achievement_names = {achievement["name"] for achievement in data["achievements"]}
    new_achievement_names = {achievement["name"] for achievement in data["new_achievements"]}
    assert data["progress"]["sessions_count"] == 1
    assert data["progress"]["messages_count"] == 1
    assert data["progress"]["xp_points"] == (
        XP_PER_SESSION + XP_PER_MESSAGE + (2 * XP_PER_ACHIEVEMENT)
    )
    assert data["progress"]["level"] == 2
    assert data["progress"]["current_streak_days"] == 1
    assert data["progress"]["last_streak_date"] is not None
    assert data["progress"]["last_activity_at"] is not None
    assert "First Session" in achievement_names
    assert "Conversation Starter" in achievement_names
    assert "First Session" in new_achievement_names
    assert "Conversation Starter" in new_achievement_names

    second_response = client.get("/progress", headers={"Authorization": f"Bearer {token}"})
    assert second_response.status_code == 200
    assert second_response.json()["new_achievements"] == []


def test_progress_requires_auth(client):
    response = client.get("/progress")

    assert response.status_code == 401


def test_xp_increases_on_session_activity(client):
    token = _register_and_login(client)

    response = client.post(
        "/conversations",
        json={"title": "Practice"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    progress_response = client.get("/progress", headers={"Authorization": f"Bearer {token}"})
    progress = progress_response.json()["progress"]

    assert progress["sessions_count"] == 1
    assert progress["xp_points"] == XP_PER_SESSION + XP_PER_ACHIEVEMENT
    assert progress["level"] == 1


def test_xp_increases_on_message_activity(client):
    _register_and_login(client)

    from app.database import get_db

    db = next(client.app.dependency_overrides[get_db]())
    try:
        user = db.query(models.User).first()
        progress = update_progress_activity(db, user.id, messages_delta=1)
        db.commit()
        db.refresh(progress)
    finally:
        db.close()

    assert progress.messages_count == 1
    assert progress.xp_points == XP_PER_MESSAGE + XP_PER_ACHIEVEMENT


def test_level_increases_after_xp_threshold(client):
    token = _register_and_login(client)

    from app.database import get_db

    db = next(client.app.dependency_overrides[get_db]())
    try:
        user = db.query(models.User).first()
        progress = update_progress_activity(db, user.id, messages_delta=1)
        progress.xp_points = 90
        db.flush()

        update_progress_activity(db, user.id, messages_delta=1)
        db.commit()
        db.refresh(progress)
    finally:
        db.close()

    assert progress.xp_points >= 100
    assert progress.level == 2


def test_xp_accumulation_awards_achievement_bonus_once(client):
    token = _register_and_login(client)

    response = client.post(
        "/conversations",
        json={"title": "Practice"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    first_progress = client.get("/progress", headers={"Authorization": f"Bearer {token}"}).json()[
        "progress"
    ]
    second_progress = client.get("/progress", headers={"Authorization": f"Bearer {token}"}).json()[
        "progress"
    ]

    assert first_progress["xp_points"] == XP_PER_SESSION + XP_PER_ACHIEVEMENT
    assert second_progress["xp_points"] == first_progress["xp_points"]


def test_level_calculation_correct():
    assert calculate_level(0) == 1
    assert calculate_level(99) == 1
    assert calculate_level(100) == 2
    assert calculate_level(250) == 3
    assert calculate_level(-10) == 1


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
        evaluate_achievements(progress, db)
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


def test_achievement_not_granted_before_threshold(client):
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
        progress.messages_count = 49
        progress.current_streak_days = 2
        evaluate_achievements(progress, db)
        db.commit()

        earned_names = {
            item.achievement.name
            for item in db.query(models.UserAchievement)
            .filter(models.UserAchievement.user_id == progress.user_id)
            .all()
        }
    finally:
        db.close()

    assert "Communicator" not in earned_names
    assert "Consistent Learner" not in earned_names


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
        evaluate_achievements(progress, db)
        evaluate_achievements(progress, db)
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


def test_multiple_achievements_triggered_in_one_update(client):
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
        progress.sessions_count = 5
        progress.messages_count = 50
        progress.current_streak_days = 7
        progress.time_spent_seconds = 3600
        evaluate_achievements(progress, db)
        db.commit()

        earned_names = {
            item.achievement.name
            for item in db.query(models.UserAchievement)
            .filter(models.UserAchievement.user_id == progress.user_id)
            .all()
        }
    finally:
        db.close()

    assert "Explorer" in earned_names
    assert "Communicator" in earned_names
    assert "Consistent Learner" in earned_names
    assert "Dedicated" in earned_names
    assert "Marathon" in earned_names


def test_progress_condition_mapping():
    progress = models.UserProgress(
        user_id=1,
        current_streak_days=7,
        time_spent_seconds=3600,
        messages_count=50,
        sessions_count=5,
    )

    assert get_progress_condition_value(progress, "streak_days") == 7
    assert get_progress_condition_value(progress, "time_spent_seconds") == 3600
    assert get_progress_condition_value(progress, "messages_count") == 50
    assert get_progress_condition_value(progress, "sessions_count") == 5
