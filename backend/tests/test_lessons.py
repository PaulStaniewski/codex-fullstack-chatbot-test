from app import models
from app.progress import XP_PER_LESSON_COMPLETION


def _register_and_login(client, email="lesson@example.com"):
    client.post("/register", json={"email": email, "password": "password123"})
    response = client.post("/login", json={"email": email, "password": "password123"})
    return response.json()["access_token"]


def test_get_lesson_creates_progress(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/fastapi_intro",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["lesson_id"] == "fastapi_intro"
    assert data["course_id"] == "fastapi"
    assert data["current_step_index"] == 0
    assert data["completed"] is False
    assert len(data["steps"]) > 0


def test_next_lesson_step_increments(client):
    token = _register_and_login(client)
    client.get("/lessons/fastapi_intro", headers={"Authorization": f"Bearer {token}"})

    response = client.post(
        "/lessons/fastapi_intro/next",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["current_step_index"] == 1
    assert data["completed"] is False


def test_completing_lesson_marks_completed(client):
    token = _register_and_login(client)
    lesson = client.get(
        "/lessons/fastapi_intro",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    response = None
    for _ in lesson["steps"]:
        response = client.post(
            "/lessons/fastapi_intro/next",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["completed"] is True
    assert data["completed_at"] is not None
    assert data["current_step_index"] == len(data["steps"]) - 1


def test_completing_lesson_awards_xp_once(client):
    token = _register_and_login(client)
    lesson = client.get(
        "/lessons/fastapi_intro",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    for _ in lesson["steps"]:
        client.post(
            "/lessons/fastapi_intro/next",
            headers={"Authorization": f"Bearer {token}"},
        )

    first_progress = client.get("/progress", headers={"Authorization": f"Bearer {token}"}).json()[
        "progress"
    ]
    client.post(
        "/lessons/fastapi_intro/next",
        headers={"Authorization": f"Bearer {token}"},
    )
    second_progress = client.get("/progress", headers={"Authorization": f"Bearer {token}"}).json()[
        "progress"
    ]

    assert first_progress["xp_points"] == XP_PER_LESSON_COMPLETION
    assert second_progress["xp_points"] == first_progress["xp_points"]


def test_unknown_lesson_returns_404(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/unknown",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_lesson_progress_endpoint_returns_user_only_progress(client):
    first_token = _register_and_login(client, "lesson-one@example.com")
    second_token = _register_and_login(client, "lesson-two@example.com")

    client.get("/lessons/fastapi_intro", headers={"Authorization": f"Bearer {first_token}"})
    client.get("/lessons/docker_basics", headers={"Authorization": f"Bearer {second_token}"})

    response = client.get(
        "/lessons/progress",
        headers={"Authorization": f"Bearer {first_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["lesson_id"] == "fastapi_intro"


def test_lesson_progress_unique_per_user_and_lesson(client):
    token = _register_and_login(client)
    client.get("/lessons/fastapi_intro", headers={"Authorization": f"Bearer {token}"})
    client.get("/lessons/fastapi_intro", headers={"Authorization": f"Bearer {token}"})

    from app.database import get_db

    db = next(client.app.dependency_overrides[get_db]())
    try:
        rows = db.query(models.LessonProgress).all()
    finally:
        db.close()

    assert len(rows) == 1
