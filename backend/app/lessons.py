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
}


def get_lesson(lesson_id: str) -> dict | None:
    return LESSONS.get(lesson_id)
