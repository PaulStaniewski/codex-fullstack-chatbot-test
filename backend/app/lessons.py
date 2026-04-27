LESSONS = {
    "fastapi_intro": {
        "lesson_id": "fastapi_intro",
        "course_id": "fastapi",
        "title": "FastAPI Introduction",
        "steps": [
            {
                "type": "intro",
                "title": "What is FastAPI?",
                "content": "FastAPI is a modern Python web framework for building APIs.",
            },
            {
                "type": "explanation",
                "title": "Why developers use it",
                "content": "It combines type hints, automatic validation, and generated OpenAPI docs.",
            },
            {
                "type": "example",
                "title": "Minimal endpoint",
                "content": "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned what FastAPI is and why it is useful for API development.",
            },
        ],
    },
    "fastapi_routing": {
        "lesson_id": "fastapi_routing",
        "course_id": "fastapi",
        "title": "FastAPI Routing",
        "steps": [
            {
                "type": "intro",
                "title": "Routes map requests",
                "content": "A route connects an HTTP method and path to a Python function.",
            },
            {
                "type": "explanation",
                "title": "Path operations",
                "content": "Decorators like @app.get('/items') and @app.post('/items') define path operations.",
            },
            {
                "type": "practice",
                "title": "Practice",
                "content": "Describe how you would create a GET /health endpoint.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how FastAPI routes organize API behavior by method and path.",
            },
        ],
    },
    "fastapi_dependency": {
        "lesson_id": "fastapi_dependency",
        "course_id": "fastapi",
        "title": "Dependency Injection",
        "steps": [
            {
                "type": "intro",
                "title": "Reusable request logic",
                "content": "Dependencies let you share authentication, database sessions, and validation logic.",
            },
            {
                "type": "example",
                "title": "Depends",
                "content": "from fastapi import Depends\n\ndef get_current_user():\n    return {'email': 'user@example.com'}\n\n@app.get('/me')\ndef me(user = Depends(get_current_user)):\n    return user",
            },
            {
                "type": "practice",
                "title": "Practice",
                "content": "Name one piece of request logic that would make sense as a dependency.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how dependencies keep endpoint code focused and reusable.",
            },
        ],
    },
    "docker_basics": {
        "lesson_id": "docker_basics",
        "course_id": "docker",
        "title": "Docker Basics",
        "steps": [
            {
                "type": "intro",
                "title": "Containers package apps",
                "content": "Docker packages an application with the runtime and dependencies it needs.",
            },
            {
                "type": "explanation",
                "title": "Images and containers",
                "content": "An image is a template. A container is a running instance of that image.",
            },
            {
                "type": "example",
                "title": "Common command",
                "content": "docker compose up --build",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how Docker helps run applications consistently across environments.",
            },
        ],
    },
    "docker_startup_race_condition": {
        "lesson_id": "docker_startup_race_condition",
        "course_id": "docker",
        "title": "Docker Compose Startup Race Condition",
        "steps": [
            {
                "type": "intro",
                "title": "Startup order is not readiness",
                "content": "Docker Compose depends_on can start services in order, but it does not guarantee that PostgreSQL is ready to accept connections.",
            },
            {
                "type": "explanation",
                "title": "Healthchecks and retries",
                "content": "Healthchecks describe service readiness, while application-level retry handles real connection timing and transient startup failures.",
            },
            {
                "type": "example",
                "title": "Retry migrations before serving",
                "content": "until alembic upgrade head; do\n  echo 'Database not ready, retrying...'\n  sleep 2\ndone\nuvicorn app.main:app --host 0.0.0.0 --port 8000",
            },
            {
                "type": "practice",
                "title": "Practice",
                "content": "Explain how you would make a FastAPI backend wait safely for PostgreSQL in Docker Compose without assuming depends_on is enough.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned why startup order can race database readiness and how healthchecks plus retries make container startup safer.",
            },
        ],
    },
    "alembic_missing_column": {
        "lesson_id": "alembic_missing_column",
        "course_id": "backend",
        "title": "Debugging Alembic Missing Column Errors",
        "steps": [
            {
                "type": "intro",
                "title": "What the error usually means",
                "content": "A 'column does not exist' error often means your SQLAlchemy model expects a column that the actual database schema does not have yet.",
            },
            {
                "type": "explanation",
                "title": "Model state vs migration state",
                "content": "Changing a model class does not change the database by itself. Alembic migrations are the bridge between code state and database state.",
            },
            {
                "type": "example",
                "title": "Useful Alembic checks",
                "content": "alembic current\nalembic heads\nalembic upgrade head",
            },
            {
                "type": "practice",
                "title": "Practice",
                "content": "A user sees: column user_progress.current_streak_days does not exist. Explain how you would diagnose the migration state and fix it safely.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned to compare model expectations with database migration state before changing application logic.",
            },
        ],
    },
    "sse_eventsource_auth": {
        "lesson_id": "sse_eventsource_auth",
        "course_id": "frontend",
        "title": "SSE Authentication with EventSource",
        "steps": [
            {
                "type": "intro",
                "title": "EventSource has header limits",
                "content": "The browser EventSource API does not let you attach custom Authorization headers like fetch does.",
            },
            {
                "type": "explanation",
                "title": "Token query param tradeoffs",
                "content": "Passing a token in the query string can make SSE work, but URLs may appear in logs, browser history, or monitoring tools.",
            },
            {
                "type": "example",
                "title": "Authenticated stream URL",
                "content": "/chat-stream?message=Explain%20SSE&token=<jwt>",
            },
            {
                "type": "practice",
                "title": "Practice",
                "content": "Explain one security risk of query-token SSE and one mitigation you would use in a production app.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned why SSE authentication often needs careful tradeoffs when using browser EventSource.",
            },
        ],
    },
    "openai_streaming_errors": {
        "lesson_id": "openai_streaming_errors",
        "course_id": "ai",
        "title": "Handling OpenAI Streaming Errors",
        "steps": [
            {
                "type": "intro",
                "title": "Streams can fail mid-response",
                "content": "AI streaming depends on network, provider, and client connections, so failures can happen after a response has already started.",
            },
            {
                "type": "explanation",
                "title": "Graceful SSE error events",
                "content": "A safe streamed error lets the client show a friendly message without crashing the server or saving incomplete assistant output.",
            },
            {
                "type": "example",
                "title": "Safe fallback message",
                "content": "SAFE_STREAM_ERROR = 'Error: Unable to generate response.'\nyield format_sse_data(SAFE_STREAM_ERROR)",
            },
            {
                "type": "practice",
                "title": "Practice",
                "content": "Describe how the UI should behave when AI streaming fails after the user has already sent a message.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how safe SSE errors protect the user experience and keep persistence logic clean.",
            },
        ],
    },
    "sqlAlchemy_user_scoped_queries": {
        "lesson_id": "sqlAlchemy_user_scoped_queries",
        "course_id": "backend",
        "title": "User-Scoped Database Queries",
        "steps": [
            {
                "type": "intro",
                "title": "Every owned query needs user scope",
                "content": "When data belongs to a user, queries should filter by both the resource identifier and current user_id.",
            },
            {
                "type": "explanation",
                "title": "Preventing cross-user leaks",
                "content": "Filtering only by a public or guessable identifier can expose another user's conversations, lessons, or submissions.",
            },
            {
                "type": "example",
                "title": "Scoped query pattern",
                "content": "db.query(PracticeSubmission).filter(\n    PracticeSubmission.user_id == current_user.id,\n    PracticeSubmission.lesson_id == lesson_id,\n)",
            },
            {
                "type": "practice",
                "title": "Practice",
                "content": "Explain why WHERE lesson_id = ... is not enough when fetching practice history for a logged-in user.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned why user-scoped filters are a core backend safety habit for multi-user apps.",
            },
        ],
    },
}


def get_lesson(lesson_id: str) -> dict | None:
    return LESSONS.get(lesson_id)
