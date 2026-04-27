from app import models
from app.lessons import get_lesson
from app.progress import XP_PER_LESSON_COMPLETION
from app.routes.lesson_routes import build_lesson_tutor_prompt, build_practice_feedback_prompt


def _register_and_login(client, email="lesson@example.com"):
    client.post("/register", json={"email": email, "password": "password123"})
    response = client.post("/login", json={"email": email, "password": "password123"})
    return response.json()["access_token"]


async def _fake_feedback_stream(_openai_input):
    yield "Good start. "
    yield "Mention the route decorator too."


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


def test_lesson_tutor_stream_requires_auth(client):
    response = client.get(
        "/lessons/fastapi_intro/tutor-stream",
        params={"question": "Explain this"},
    )

    assert response.status_code == 401


def test_lesson_tutor_stream_unknown_lesson_returns_404(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/unknown/tutor-stream",
        params={"question": "Explain this", "token": token},
    )

    assert response.status_code == 404


def test_lesson_tutor_stream_invalid_step_index_returns_400(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/fastapi_intro/tutor-stream",
        params={"question": "Explain this", "step_index": 99, "token": token},
    )

    assert response.status_code == 400


def test_lesson_tutor_stream_empty_question_rejected(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/fastapi_intro/tutor-stream",
        params={"question": "   ", "token": token},
    )

    assert response.status_code == 400


def test_lesson_tutor_prompt_includes_lesson_step_and_question():
    lesson = get_lesson("fastapi_intro")
    step = lesson["steps"][0]

    prompt = build_lesson_tutor_prompt(lesson, step, "Why is this useful?")
    combined_content = "\n".join(item["content"] for item in prompt)

    assert lesson["title"] in combined_content
    assert step["title"] in combined_content
    assert step["content"] in combined_content
    assert "Why is this useful?" in combined_content


def test_practice_feedback_stream_requires_auth(client):
    response = client.get(
        "/lessons/fastapi_routing/practice-feedback-stream",
        params={"step_index": 2, "answer": "I would add app.get."},
    )

    assert response.status_code == 401


def test_practice_feedback_stream_unknown_lesson_returns_404(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/unknown/practice-feedback-stream",
        params={"step_index": 0, "answer": "My answer", "token": token},
    )

    assert response.status_code == 404


def test_practice_feedback_stream_invalid_step_index_returns_400(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/fastapi_routing/practice-feedback-stream",
        params={"step_index": 99, "answer": "My answer", "token": token},
    )

    assert response.status_code == 400


def test_practice_feedback_stream_non_practice_step_rejected(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/fastapi_routing/practice-feedback-stream",
        params={"step_index": 0, "answer": "My answer", "token": token},
    )

    assert response.status_code == 400


def test_practice_feedback_stream_empty_answer_rejected(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/fastapi_routing/practice-feedback-stream",
        params={"step_index": 2, "answer": "   ", "token": token},
    )

    assert response.status_code == 400


def test_practice_feedback_prompt_includes_instruction_and_user_answer():
    lesson = get_lesson("fastapi_routing")
    step = lesson["steps"][2]

    prompt = build_practice_feedback_prompt(lesson, step, "I would use @app.get('/health').")
    combined_content = "\n".join(item["content"] for item in prompt)

    assert lesson["title"] in combined_content
    assert step["title"] in combined_content
    assert step["content"] in combined_content
    assert "I would use @app.get('/health')." in combined_content


def test_practice_submission_saved_after_feedback(client, monkeypatch):
    monkeypatch.setattr("app.routes.lesson_routes._stream_openai_text", _fake_feedback_stream)
    token = _register_and_login(client)

    response = client.get(
        "/lessons/fastapi_routing/practice-feedback-stream",
        params={
            "step_index": 2,
            "answer": "I would create a health function.",
            "token": token,
        },
    )

    assert response.status_code == 200
    assert "Good start" in response.text

    history_response = client.get(
        "/lessons/fastapi_routing/practice-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    history = history_response.json()

    assert len(history) == 1
    assert history[0]["answer"] == "I would create a health function."
    assert history[0]["feedback"] == "Good start. Mention the route decorator too."


def test_practice_history_returns_user_only_submissions(client, monkeypatch):
    monkeypatch.setattr("app.routes.lesson_routes._stream_openai_text", _fake_feedback_stream)
    first_token = _register_and_login(client, "practice-one@example.com")
    second_token = _register_and_login(client, "practice-two@example.com")

    client.get(
        "/lessons/fastapi_routing/practice-feedback-stream",
        params={"step_index": 2, "answer": "First user answer", "token": first_token},
    )
    client.get(
        "/lessons/fastapi_routing/practice-feedback-stream",
        params={"step_index": 2, "answer": "Second user answer", "token": second_token},
    )

    response = client.get(
        "/lessons/fastapi_routing/practice-history",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    history = response.json()

    assert len(history) == 1
    assert history[0]["answer"] == "First user answer"


def test_practice_history_ordered_newest_first(client, monkeypatch):
    monkeypatch.setattr("app.routes.lesson_routes._stream_openai_text", _fake_feedback_stream)
    token = _register_and_login(client)

    client.get(
        "/lessons/fastapi_routing/practice-feedback-stream",
        params={"step_index": 2, "answer": "Older answer", "token": token},
    )
    client.get(
        "/lessons/fastapi_routing/practice-feedback-stream",
        params={"step_index": 2, "answer": "Newer answer", "token": token},
    )

    response = client.get(
        "/lessons/fastapi_routing/practice-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    history = response.json()

    assert [item["answer"] for item in history] == ["Newer answer", "Older answer"]


def test_practice_history_requires_auth(client):
    response = client.get("/lessons/fastapi_routing/practice-history")

    assert response.status_code == 401


def test_practice_history_unknown_lesson_returns_404(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/unknown/practice-history",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
