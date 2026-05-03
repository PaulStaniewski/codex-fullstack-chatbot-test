from app import models
from app.lessons import get_lesson
from app.progress import XP_PER_LESSON_COMPLETION
from app.routes.lesson_routes import (
    build_lesson_study_prompt,
    build_lesson_tutor_prompt,
    build_practice_feedback_prompt,
    format_practice_feedback_for_user,
    get_reading_steps_for_study,
    parse_practice_feedback_metadata,
)


def _register_and_login(client, email="lesson@example.com"):
    client.post("/register", json={"email": email, "password": "password123"})
    response = client.post("/login", json={"email": email, "password": "password123"})
    return response.json()["access_token"]


async def _fake_feedback_stream(_openai_input):
    yield "Good start. "
    yield "Mention the route decorator too."


async def _fake_scored_feedback_stream(_openai_input):
    yield '{"summary_feedback":"Good answer. Add the exact route path.",'
    yield '"score":82,'
    yield '"strengths":["Mentions a health endpoint","Understands GET usage"],'
    yield '"improvements":["Include the /health path","Mention the decorator"],'
    yield '"suggested_answer":"I would add a GET /health endpoint that returns a simple status."}'


async def _fake_malformed_feedback_stream(_openai_input):
    yield "{not valid json"


def test_get_lesson_creates_progress(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/docker_basics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["lesson_id"] == "docker_basics"
    assert data["course_id"] == "docker"
    assert data["current_step_index"] == 0
    assert data["completed"] is False
    assert len(data["steps"]) > 0


def test_next_lesson_step_increments(client):
    token = _register_and_login(client)
    client.get("/lessons/docker_basics", headers={"Authorization": f"Bearer {token}"})

    response = client.post(
        "/lessons/docker_basics/next",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["current_step_index"] == 1
    assert data["completed"] is False


def test_completing_lesson_marks_completed(client):
    token = _register_and_login(client)
    lesson = client.get(
        "/lessons/docker_basics",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    response = None
    for _ in lesson["steps"]:
        response = client.post(
            "/lessons/docker_basics/next",
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
        "/lessons/docker_basics",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    for _ in lesson["steps"]:
        client.post(
            "/lessons/docker_basics/next",
            headers={"Authorization": f"Bearer {token}"},
        )

    first_progress = client.get("/progress", headers={"Authorization": f"Bearer {token}"}).json()[
        "progress"
    ]
    client.post(
        "/lessons/docker_basics/next",
        headers={"Authorization": f"Bearer {token}"},
    )
    second_progress = client.get("/progress", headers={"Authorization": f"Bearer {token}"}).json()[
        "progress"
    ]

    assert first_progress["xp_points"] == XP_PER_LESSON_COMPLETION + 50
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

    client.get("/lessons/docker_basics", headers={"Authorization": f"Bearer {first_token}"})
    client.get("/lessons/docker_basics", headers={"Authorization": f"Bearer {second_token}"})

    response = client.get(
        "/lessons/progress",
        headers={"Authorization": f"Bearer {first_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["lesson_id"] == "docker_basics"


def test_lesson_progress_endpoint_excludes_other_user_completed_rows(client):
    first_token = _register_and_login(client, "complete-one@example.com")
    second_token = _register_and_login(client, "complete-two@example.com")

    lesson = client.get(
        "/lessons/docker_basics",
        headers={"Authorization": f"Bearer {first_token}"},
    ).json()
    client.get("/lessons/docker_basics", headers={"Authorization": f"Bearer {second_token}"})

    for _ in lesson["steps"]:
        client.post(
            "/lessons/docker_basics/next",
            headers={"Authorization": f"Bearer {first_token}"},
        )

    response = client.get(
        "/lessons/progress",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["lesson_id"] == "docker_basics"
    assert data[0]["completed"] is False


def test_lesson_progress_unique_per_user_and_lesson(client):
    token = _register_and_login(client)
    client.get("/lessons/docker_basics", headers={"Authorization": f"Bearer {token}"})
    client.get("/lessons/docker_basics", headers={"Authorization": f"Bearer {token}"})

    from app.database import get_db

    db = next(client.app.dependency_overrides[get_db]())
    try:
        rows = db.query(models.LessonProgress).all()
    finally:
        db.close()

    assert len(rows) == 1


def test_lesson_completion_is_scoped_to_current_user(client):
    first_token = _register_and_login(client, "scoped-complete-one@example.com")
    second_token = _register_and_login(client, "scoped-complete-two@example.com")

    lesson = client.get(
        "/lessons/docker_basics",
        headers={"Authorization": f"Bearer {first_token}"},
    ).json()

    for _ in lesson["steps"]:
        client.post(
            "/lessons/docker_basics/next",
            headers={"Authorization": f"Bearer {first_token}"},
        )

    second_user_lesson = client.get(
        "/lessons/docker_basics",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    data = second_user_lesson.json()

    assert second_user_lesson.status_code == 200
    assert data["current_step_index"] == 0
    assert data["completed"] is False
    assert data["completed_at"] is None


def test_get_lesson_does_not_expose_other_user_progress(client):
    first_token = _register_and_login(client, "lesson-read-one@example.com")
    second_token = _register_and_login(client, "lesson-read-two@example.com")

    client.get("/lessons/docker_compose_basics", headers={"Authorization": f"Bearer {first_token}"})
    client.post(
        "/lessons/docker_compose_basics/next",
        headers={"Authorization": f"Bearer {first_token}"},
    )

    response = client.get(
        "/lessons/docker_compose_basics",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["current_step_index"] == 0
    assert data["completed"] is False


def test_completing_theory_step_awards_xp_once(client):
    token = _register_and_login(client, "theory-xp@example.com")

    first_response = client.post(
        "/lessons/docker_basics/steps/0/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    first_progress = client.get("/progress", headers={"Authorization": f"Bearer {token}"}).json()[
        "progress"
    ]

    second_response = client.post(
        "/lessons/docker_basics/steps/0/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    second_progress = client.get("/progress", headers={"Authorization": f"Bearer {token}"}).json()[
        "progress"
    ]

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["steps"][0]["completed"] is True
    assert first_response.json()["steps"][0]["xp_awarded"] == 5
    assert first_progress["xp_points"] == 5
    assert second_progress["xp_points"] == first_progress["xp_points"]


def test_completing_same_step_twice_does_not_create_duplicate_row(client):
    token = _register_and_login(client, "theory-duplicate@example.com")

    first_response = client.post(
        "/lessons/docker_basics/steps/0/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    second_response = client.post(
        "/lessons/docker_basics/steps/0/complete",
        headers={"Authorization": f"Bearer {token}"},
    )

    from app.database import get_db

    db = next(client.app.dependency_overrides[get_db]())
    try:
        rows = (
            db.query(models.LessonStepProgress)
            .filter(
                models.LessonStepProgress.lesson_id == "docker_basics",
                models.LessonStepProgress.step_index == 0,
            )
            .all()
        )
    finally:
        db.close()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(rows) == 1


def test_completed_step_returns_existing_state(client):
    token = _register_and_login(client, "theory-existing@example.com")

    first_response = client.post(
        "/lessons/docker_basics/steps/1/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    second_response = client.post(
        "/lessons/docker_basics/steps/1/complete",
        headers={"Authorization": f"Bearer {token}"},
    )

    first_step = first_response.json()["steps"][1]
    second_step = second_response.json()["steps"][1]
    progress = client.get("/progress", headers={"Authorization": f"Bearer {token}"}).json()[
        "progress"
    ]

    assert first_step["completed"] is True
    assert second_step["completed"] is True
    assert second_step["completed_at"] == first_step["completed_at"]
    assert second_step["xp_awarded"] == first_step["xp_awarded"]
    assert progress["xp_points"] == 10


def test_another_user_can_complete_same_step_independently(client):
    first_token = _register_and_login(client, "theory-user-one@example.com")
    second_token = _register_and_login(client, "theory-user-two@example.com")

    first_response = client.post(
        "/lessons/docker_basics/steps/0/complete",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    second_response = client.post(
        "/lessons/docker_basics/steps/0/complete",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    first_progress = client.get(
        "/progress",
        headers={"Authorization": f"Bearer {first_token}"},
    ).json()["progress"]
    second_progress = client.get(
        "/progress",
        headers={"Authorization": f"Bearer {second_token}"},
    ).json()["progress"]

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_progress["xp_points"] == 5
    assert second_progress["xp_points"] == 5


def test_completing_practice_step_does_not_award_reading_xp(client):
    token = _register_and_login(client, "practice-no-xp@example.com")

    response = client.post(
        "/lessons/docker_compose_basics/steps/5/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    progress = client.get("/progress", headers={"Authorization": f"Bearer {token}"}).json()[
        "progress"
    ]

    assert response.status_code == 200
    assert response.json()["steps"][5]["completed"] is True
    assert response.json()["steps"][5]["xp_awarded"] == 0
    assert progress["xp_points"] == 0


def test_complete_step_unknown_lesson_returns_404(client):
    token = _register_and_login(client, "unknown-step@example.com")

    response = client.post(
        "/lessons/unknown/steps/0/complete",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_complete_step_invalid_index_returns_400(client):
    token = _register_and_login(client, "invalid-step@example.com")

    response = client.post(
        "/lessons/docker_basics/steps/99/complete",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


def test_step_completion_is_scoped_to_current_user(client):
    first_token = _register_and_login(client, "step-scope-one@example.com")
    second_token = _register_and_login(client, "step-scope-two@example.com")

    client.post(
        "/lessons/docker_basics/steps/0/complete",
        headers={"Authorization": f"Bearer {first_token}"},
    )

    response = client.get(
        "/lessons/docker_basics",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 200
    assert response.json()["steps"][0]["completed"] is False
    assert response.json()["steps"][0]["xp_awarded"] == 0


def test_get_lesson_returns_step_completed_state(client):
    token = _register_and_login(client, "step-state@example.com")

    client.post(
        "/lessons/docker_basics/steps/1/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    response = client.get(
        "/lessons/docker_basics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["steps"][1]["completed"] is True
    assert response.json()["steps"][1]["completed_at"] is not None
    assert response.json()["steps"][1]["xp_awarded"] == 10


def test_lesson_study_stream_requires_auth(client):
    response = client.get(
        "/lessons/docker_basics/study-stream",
        params={"action": "summarize"},
    )

    assert response.status_code == 401


def test_lesson_study_stream_unknown_lesson_returns_404(client):
    token = _register_and_login(client, "study-unknown@example.com")

    response = client.get(
        "/lessons/unknown/study-stream",
        params={"action": "summarize", "token": token},
    )

    assert response.status_code == 404


def test_lesson_study_stream_invalid_action_returns_400(client):
    token = _register_and_login(client, "study-action@example.com")

    response = client.get(
        "/lessons/docker_basics/study-stream",
        params={"action": "invalid", "token": token},
    )

    assert response.status_code == 400


def test_lesson_study_prompt_includes_material_action_and_question():
    lesson = get_lesson("docker_basics")
    reading_steps = get_reading_steps_for_study(lesson)

    prompt = build_lesson_study_prompt(
        lesson,
        reading_steps,
        "custom_question",
        "Why does this endpoint matter?",
    )
    combined_content = "\n".join(message["content"] for message in prompt)

    assert lesson["title"] in combined_content
    assert reading_steps[0]["title"] in combined_content
    assert reading_steps[0]["content"] in combined_content
    assert "custom_question" in combined_content
    assert "Why does this endpoint matter?" in combined_content


def test_lesson_tutor_stream_requires_auth(client):
    response = client.get(
        "/lessons/docker_basics/tutor-stream",
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
        "/lessons/docker_basics/tutor-stream",
        params={"question": "Explain this", "step_index": 99, "token": token},
    )

    assert response.status_code == 400


def test_lesson_tutor_stream_empty_question_rejected(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/docker_basics/tutor-stream",
        params={"question": "   ", "token": token},
    )

    assert response.status_code == 400


def test_lesson_tutor_prompt_includes_lesson_step_and_question():
    lesson = get_lesson("docker_basics")
    step = lesson["steps"][0]

    prompt = build_lesson_tutor_prompt(lesson, step, "Why is this useful?")
    combined_content = "\n".join(item["content"] for item in prompt)

    assert lesson["title"] in combined_content
    assert step["title"] in combined_content
    assert step["content"] in combined_content
    assert "Why is this useful?" in combined_content


def test_practice_feedback_stream_requires_auth(client):
    response = client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "I would add app.get."},
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
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 99, "answer": "My answer", "token": token},
    )

    assert response.status_code == 400


def test_practice_feedback_stream_non_practice_step_rejected(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 0, "answer": "My answer", "token": token},
    )

    assert response.status_code == 400


def test_practice_feedback_stream_empty_answer_rejected(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "   ", "token": token},
    )

    assert response.status_code == 400


def test_practice_feedback_prompt_includes_instruction_and_user_answer():
    lesson = get_lesson("docker_compose_basics")
    step = lesson["steps"][5]

    prompt = build_practice_feedback_prompt(lesson, step, "I would use @app.get('/health').")
    combined_content = "\n".join(item["content"] for item in prompt)

    assert lesson["title"] in combined_content
    assert step["title"] in combined_content
    assert step["content"] in combined_content
    assert "I would use @app.get('/health')." in combined_content
    assert '"score": 0' in combined_content
    assert '"strengths": ["..."]' in combined_content
    assert '"improvements": ["..."]' in combined_content
    assert '"suggested_answer": "..."' in combined_content
    assert '"summary_feedback": "..."' in combined_content


def test_practice_submission_saved_after_feedback(client, monkeypatch):
    monkeypatch.setattr("app.routes.lesson_routes._stream_openai_text", _fake_feedback_stream)
    token = _register_and_login(client)

    response = client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={
            "step_index": 5,
            "answer": "I would create a health function.",
            "token": token,
        },
    )

    assert response.status_code == 200
    assert "Good start" in response.text

    history_response = client.get(
        "/lessons/docker_compose_basics/practice-history",
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
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "First user answer", "token": first_token},
    )
    client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "Second user answer", "token": second_token},
    )

    response = client.get(
        "/lessons/docker_compose_basics/practice-history",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    history = response.json()

    assert len(history) == 1
    assert history[0]["answer"] == "First user answer"


def test_practice_history_ordered_newest_first(client, monkeypatch):
    monkeypatch.setattr("app.routes.lesson_routes._stream_openai_text", _fake_feedback_stream)
    token = _register_and_login(client)

    client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "Older answer", "token": token},
    )
    client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "Newer answer", "token": token},
    )

    response = client.get(
        "/lessons/docker_compose_basics/practice-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    history = response.json()

    assert [item["answer"] for item in history] == ["Newer answer", "Older answer"]


def test_practice_history_requires_auth(client):
    response = client.get("/lessons/docker_compose_basics/practice-history")

    assert response.status_code == 401


def test_practice_history_unknown_lesson_returns_404(client):
    token = _register_and_login(client)

    response = client.get(
        "/lessons/unknown/practice-history",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_practice_feedback_metadata_parser_extracts_structured_feedback():
    feedback = (
        '{"score":91,'
        '"strengths":["Clear route choice","Good HTTP method"],'
        '"improvements":["Include response shape"],'
        '"suggested_answer":"Use a GET /health route.",'
        '"summary_feedback":"Nice work."}'
    )

    metadata = parse_practice_feedback_metadata(feedback)

    assert metadata["score"] == 91
    assert metadata["strengths"] == ["Clear route choice", "Good HTTP method"]
    assert metadata["improvements"] == ["Include response shape"]
    assert metadata["suggested_answer"] == "Use a GET /health route."
    assert metadata["summary_feedback"] == "Nice work."


def test_practice_feedback_metadata_parser_tolerates_malformed_json():
    metadata = parse_practice_feedback_metadata("{not valid json")

    assert metadata["score"] is None
    assert metadata["strengths"] is None
    assert metadata["improvements"] is None
    assert metadata["suggested_answer"] is None
    assert metadata["summary_feedback"] is None


def test_practice_feedback_metadata_parser_rejects_invalid_score():
    metadata = parse_practice_feedback_metadata(
        '{"score":101,"strengths":["Good"],"improvements":["Add detail"],'
        '"suggested_answer":"Better answer","summary_feedback":"Summary"}'
    )

    assert metadata["score"] is None
    assert metadata["strengths"] == ["Good"]
    assert metadata["improvements"] == ["Add detail"]


def test_practice_feedback_formatter_uses_valid_structured_output():
    metadata = parse_practice_feedback_metadata(
        '{"score":74,"strengths":["Good endpoint choice"],'
        '"improvements":["Mention the response"],'
        '"suggested_answer":"Return a simple status object.",'
        '"summary_feedback":"Solid start."}'
    )

    feedback = format_practice_feedback_for_user(metadata, "raw json")

    assert "Solid start." in feedback
    assert "Suggested answer:" in feedback
    assert "Return a simple status object." in feedback
    assert "Good endpoint choice" in feedback
    assert "Mention the response" in feedback
    assert "Score: 74/100" in feedback


def test_practice_submission_saves_score_metadata(client, monkeypatch):
    monkeypatch.setattr("app.routes.lesson_routes._stream_openai_text", _fake_scored_feedback_stream)
    token = _register_and_login(client)

    client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={
            "step_index": 5,
            "answer": "I would use a GET endpoint.",
            "token": token,
        },
    )
    history_response = client.get(
        "/lessons/docker_compose_basics/practice-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    submission = history_response.json()[0]

    assert submission["score"] == 82
    assert submission["strengths"] == [
        "Mentions a health endpoint",
        "Understands GET usage",
    ]
    assert submission["improvements"] == [
        "Include the /health path",
        "Mention the decorator",
    ]
    assert "Good answer. Add the exact route path." in submission["feedback"]
    assert "Suggested answer:" in submission["feedback"]


def test_practice_submission_malformed_json_still_saves_fallback_feedback(client, monkeypatch):
    monkeypatch.setattr("app.routes.lesson_routes._stream_openai_text", _fake_malformed_feedback_stream)
    token = _register_and_login(client)

    client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={
            "step_index": 5,
            "answer": "I would create a health route.",
            "token": token,
        },
    )
    history_response = client.get(
        "/lessons/docker_compose_basics/practice-history",
        headers={"Authorization": f"Bearer {token}"},
    )
    submission = history_response.json()[0]

    assert submission["feedback"] == "{not valid json"
    assert submission["score"] is None
    assert submission["strengths"] is None
    assert submission["improvements"] is None


def test_practice_submission_first_attempt_number_is_one(client, monkeypatch):
    monkeypatch.setattr("app.routes.lesson_routes._stream_openai_text", _fake_feedback_stream)
    token = _register_and_login(client)

    client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "First answer", "token": token},
    )
    history_response = client.get(
        "/lessons/docker_compose_basics/practice-history",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert history_response.json()[0]["attempt_number"] == 1


def test_practice_submission_second_attempt_increments(client, monkeypatch):
    monkeypatch.setattr("app.routes.lesson_routes._stream_openai_text", _fake_feedback_stream)
    token = _register_and_login(client)

    client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "First answer", "token": token},
    )
    client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "Second answer", "token": token},
    )
    history_response = client.get(
        "/lessons/docker_compose_basics/practice-history",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert [item["attempt_number"] for item in history_response.json()] == [2, 1]


def test_practice_submission_numbering_scoped_to_step(client, monkeypatch):
    monkeypatch.setattr("app.routes.lesson_routes._stream_openai_text", _fake_feedback_stream)
    token = _register_and_login(client)

    client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "Routing practice", "token": token},
    )
    client.get(
        "/lessons/postgres_container_not_ready/practice-feedback-stream",
        params={"step_index": 5, "answer": "Dependency practice", "token": token},
    )

    routing_history = client.get(
        "/lessons/docker_compose_basics/practice-history",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    dependency_history = client.get(
        "/lessons/postgres_container_not_ready/practice-history",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    assert routing_history[0]["attempt_number"] == 1
    assert dependency_history[0]["attempt_number"] == 1


def test_practice_submission_numbering_scoped_to_user(client, monkeypatch):
    monkeypatch.setattr("app.routes.lesson_routes._stream_openai_text", _fake_feedback_stream)
    first_token = _register_and_login(client, "attempt-one@example.com")
    second_token = _register_and_login(client, "attempt-two@example.com")

    client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "First user answer", "token": first_token},
    )
    client.get(
        "/lessons/docker_compose_basics/practice-feedback-stream",
        params={"step_index": 5, "answer": "Second user answer", "token": second_token},
    )

    first_history = client.get(
        "/lessons/docker_compose_basics/practice-history",
        headers={"Authorization": f"Bearer {first_token}"},
    ).json()
    second_history = client.get(
        "/lessons/docker_compose_basics/practice-history",
        headers={"Authorization": f"Bearer {second_token}"},
    ).json()

    assert first_history[0]["attempt_number"] == 1
    assert second_history[0]["attempt_number"] == 1
