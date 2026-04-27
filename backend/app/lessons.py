LESSONS = {
    "fastapi_intro": {
        "lesson_id": "fastapi_intro",
        "course_id": "fastapi",
        "title": "FastAPI Introduction",
        "difficulty": "easy",
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
        "difficulty": "easy",
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
                "difficulty": "easy",
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
        "difficulty": "easy",
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
                "difficulty": "easy",
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
        "difficulty": "easy",
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
        "difficulty": "medium",
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
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A FastAPI container starts before PostgreSQL is ready and crashes with a connection refused error. Explain why depends_on did not prevent this failure.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Propose a Docker Compose and backend startup strategy that waits safely for PostgreSQL before running Alembic migrations and starting Uvicorn.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Describe how you would make the startup flow resilient in production, including retry limits, logging, healthchecks, and what should happen if the database never becomes ready.",
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
        "difficulty": "medium",
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
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A user sees: column user_progress.current_streak_days does not exist. Explain the most likely mismatch between SQLAlchemy models and the actual database schema.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Write the sequence of Alembic checks and commands you would run to confirm the current revision, compare it with heads, and apply the missing migration safely.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Explain how you would prevent missing-column errors during deploys, including migration ordering, release checks, rollback thinking, and avoiding manual database edits.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned to compare model expectations with database migration state before changing application logic.",
            },
        ],
    },
    "alembic_revision_too_long": {
        "lesson_id": "alembic_revision_too_long",
        "course_id": "backend",
        "title": "Alembic Revision ID Too Long",
        "difficulty": "hard",
        "steps": [
            {
                "type": "intro",
                "title": "Revision IDs have practical limits",
                "content": "Alembic revision identifiers are stored in the database and referenced by migration files, so overly long IDs can break tooling or exceed column limits.",
            },
            {
                "type": "explanation",
                "title": "Why generated names can fail",
                "content": "Custom migration templates or manual revision IDs can accidentally create identifiers longer than the alembic_version table expects.",
            },
            {
                "type": "example",
                "title": "Typical symptom",
                "content": "sqlalchemy.exc.DataError: value too long for type character varying(32)\n\nCheck the revision id in the migration file and the version_num column length.",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A deploy fails while inserting a migration revision into alembic_version because the value is too long. Explain what you would inspect first and why.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Describe a safe fix for an overly long Alembic revision ID before it has been deployed to shared environments.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Design a migration review rule that prevents invalid revision IDs from reaching CI or production.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how revision ID length can break migrations and how to catch invalid migration metadata early.",
            },
        ],
    },
    "duplicate_migration_head": {
        "lesson_id": "duplicate_migration_head",
        "course_id": "backend",
        "title": "Duplicate Alembic Migration Head",
        "difficulty": "hard",
        "steps": [
            {
                "type": "intro",
                "title": "Multiple heads mean branches diverged",
                "content": "Alembic can report multiple heads when two migration files were created from the same previous revision.",
            },
            {
                "type": "explanation",
                "title": "Why teams hit this",
                "content": "Parallel feature branches often add migrations independently. When merged together, the migration graph has more than one latest revision.",
            },
            {
                "type": "example",
                "title": "Useful commands",
                "content": "alembic heads\nalembic history --verbose\nalembic merge -m \"merge heads\" <head_a> <head_b>",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "CI fails with 'Multiple head revisions are present'. Explain what this says about the migration graph and how you would identify the divergent heads.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Describe how to create and review an Alembic merge migration without losing either branch's schema changes.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Propose a CI check and team workflow that prevents duplicate migration heads from surprising production deploys.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how duplicate heads happen and how merge migrations restore a single migration path.",
            },
        ],
    },
    "missing_foreign_key_constraint": {
        "lesson_id": "missing_foreign_key_constraint",
        "course_id": "backend",
        "title": "Missing Foreign Key Constraint",
        "difficulty": "hard",
        "steps": [
            {
                "type": "intro",
                "title": "Relationships need database enforcement",
                "content": "A SQLAlchemy relationship in code does not guarantee the database enforces referential integrity unless the schema includes a foreign key constraint.",
            },
            {
                "type": "explanation",
                "title": "What goes wrong",
                "content": "Without a real foreign key, orphan rows can survive deletes, joins can behave unexpectedly, and data cleanup becomes harder.",
            },
            {
                "type": "example",
                "title": "Constraint shape",
                "content": "user_id = Column(Integer, ForeignKey('users.id'), nullable=False)\n\nCheck the generated Alembic migration includes op.create_foreign_key or a ForeignKey column.",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "Practice submissions have a user_id column but deleting a user leaves orphan submissions. Explain what schema issue you suspect and how you would confirm it.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Describe how to add the missing foreign key safely, including how you would handle existing orphan rows before applying the constraint.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Create a checklist for reviewing migrations that add user-owned tables so missing constraints and cascade behavior are caught early.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned why relationships should be backed by database constraints and how to repair missing foreign keys safely.",
            },
        ],
    },
    "sse_eventsource_auth": {
        "lesson_id": "sse_eventsource_auth",
        "course_id": "frontend",
        "title": "SSE Authentication with EventSource",
        "difficulty": "medium",
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
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A team uses /chat-stream?token=<jwt> for EventSource. Identify one concrete place that token might leak and why EventSource pushed the team toward this design.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Propose a safer SSE authentication approach or mitigation plan for query-token streams while keeping browser EventSource compatibility.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Design a production policy for SSE tokens that considers short lifetimes, logging redaction, HTTPS, refresh behavior, and what the client should do on auth failure.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned why SSE authentication often needs careful tradeoffs when using browser EventSource.",
            },
        ],
    },
    "eventsource_token_expired": {
        "lesson_id": "eventsource_token_expired",
        "course_id": "frontend",
        "title": "EventSource Token Expired",
        "difficulty": "hard",
        "steps": [
            {
                "type": "intro",
                "title": "Long streams can outlive tokens",
                "content": "SSE connections may stay open long enough for a JWT or short-lived stream token to expire while the user is still interacting.",
            },
            {
                "type": "explanation",
                "title": "How expiration appears",
                "content": "The server may reject a new stream with 401, close an active stream, or send a safe auth error depending on where validation happens.",
            },
            {
                "type": "example",
                "title": "Client recovery path",
                "content": "eventSource.onerror = () => {\n  showFriendlyError('Your session expired. Please sign in again.');\n  eventSource.close();\n}",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A user can load conversations but every new EventSource stream immediately fails after their token expires. Explain how you would distinguish auth expiration from a network failure.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Design a frontend and backend response flow for expired SSE tokens that avoids duplicate messages and gives the user a clear next action.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Propose a secure token lifetime and refresh strategy for SSE that balances usability, logging risk, and forced logout behavior.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how token expiration affects EventSource streams and how clients should recover safely.",
            },
        ],
    },
    "duplicate_stream_messages": {
        "lesson_id": "duplicate_stream_messages",
        "course_id": "frontend",
        "title": "Duplicate Stream Messages",
        "difficulty": "hard",
        "steps": [
            {
                "type": "intro",
                "title": "Streaming UI can duplicate state",
                "content": "A live assistant bubble can appear twice if the UI both appends streamed content and reloads persisted messages without reconciliation.",
            },
            {
                "type": "explanation",
                "title": "Where duplication comes from",
                "content": "Duplicate messages often happen when optimistic UI state, final persisted state, and retry logic all write separate assistant entries.",
            },
            {
                "type": "example",
                "title": "Stable live message pattern",
                "content": "Use one temporary assistant message during streaming, update its content as chunks arrive, then finalize that same message instead of appending another one.",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A chat UI shows two identical assistant answers after streaming completes. Explain which state transitions you would inspect first.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Describe a simple message-state approach that keeps one live assistant bubble during streaming and prevents duplicate final messages.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Design a retry and reconnect strategy that prevents duplicate user or assistant messages when a stream fails midway.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how stable message identity keeps streamed chat responses from duplicating or flickering.",
            },
        ],
    },
    "openai_streaming_errors": {
        "lesson_id": "openai_streaming_errors",
        "course_id": "ai",
        "title": "Handling OpenAI Streaming Errors",
        "difficulty": "medium",
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
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A streamed AI response stops halfway through. Explain which parts of the system could have failed and why the backend should avoid saving a partial assistant message.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Describe the backend and frontend behavior you would implement to send a safe SSE error and show a retry option without duplicating messages.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Explain how you would monitor and harden AI streaming failures in production, including timeout handling, provider errors, client disconnects, and user-facing recovery.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how safe SSE errors protect the user experience and keep persistence logic clean.",
            },
        ],
    },
    "openai_rate_limit_handling": {
        "lesson_id": "openai_rate_limit_handling",
        "course_id": "ai",
        "title": "OpenAI Rate Limit Handling",
        "difficulty": "production",
        "steps": [
            {
                "type": "intro",
                "title": "Provider limits are normal",
                "content": "AI applications must expect rate limits from upstream providers and respond without crashing or overwhelming the provider.",
            },
            {
                "type": "explanation",
                "title": "User-safe backpressure",
                "content": "Good rate-limit handling combines clear user messaging, retry-after behavior, local throttling, and logs that help operators tune usage.",
            },
            {
                "type": "example",
                "title": "Safe response",
                "content": "If the provider returns a rate limit error, stream or return a friendly message such as: 'The AI service is busy. Please try again shortly.'",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "Users report intermittent AI failures during busy periods. Explain how you would determine whether provider rate limits are the root cause.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Design a minimal backend strategy for catching OpenAI rate limit errors and returning a safe SSE error without saving a failed assistant response.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Propose a production plan for per-user limits, retry timing, monitoring, and communicating provider saturation to users.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how to handle AI provider rate limits with graceful user experience and operational backpressure.",
            },
        ],
    },
    "partial_stream_failure": {
        "lesson_id": "partial_stream_failure",
        "course_id": "ai",
        "title": "Partial Stream Failure",
        "difficulty": "production",
        "steps": [
            {
                "type": "intro",
                "title": "Partial output is risky",
                "content": "A stream can fail after sending useful-looking text, but the response may be incomplete, misleading, or unsafe to persist as final.",
            },
            {
                "type": "explanation",
                "title": "Finalization matters",
                "content": "Applications should distinguish between streamed draft content and successfully completed assistant messages.",
            },
            {
                "type": "example",
                "title": "State transition",
                "content": "streaming -> completed: save assistant message\nstreaming -> failed: show retry and avoid persisting incomplete assistant output",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A user sees half an answer and then an error. Explain why persisting that partial text as a normal assistant message could cause product and data problems.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Describe backend and frontend changes that separate live streamed text from final persisted assistant content.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Design observability and recovery behavior for partial stream failures, including logs, metrics, retry UI, and client disconnect handling.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned why partial streams need explicit failure handling before content is treated as final.",
            },
        ],
    },
    "sqlAlchemy_user_scoped_queries": {
        "lesson_id": "sqlAlchemy_user_scoped_queries",
        "course_id": "backend",
        "title": "User-Scoped Database Queries",
        "difficulty": "hard",
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
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A practice history query filters only by lesson_id. Explain how this can leak another user's submissions in a multi-user application.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Rewrite the query conceptually so practice history is scoped to both lesson_id and the authenticated current_user.id.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Describe a review checklist or test strategy that would catch missing user_id filters across conversations, lesson progress, and practice submissions.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned why user-scoped filters are a core backend safety habit for multi-user apps.",
            },
        ],
    },
    "postgres_container_not_ready": {
        "lesson_id": "postgres_container_not_ready",
        "course_id": "docker",
        "title": "Postgres Container Not Ready",
        "difficulty": "hard",
        "steps": [
            {
                "type": "intro",
                "title": "Running is not ready",
                "content": "A PostgreSQL container can be running while the database is still initializing and not yet accepting application connections.",
            },
            {
                "type": "explanation",
                "title": "Initialization takes time",
                "content": "Startup scripts, volume initialization, WAL recovery, and container networking can all delay database readiness after the process starts.",
            },
            {
                "type": "example",
                "title": "Readiness check",
                "content": "pg_isready -U postgres -d app_db\n\nUse readiness checks with retries instead of assuming the port is ready immediately.",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A backend fails on the first deploy attempt but works after docker compose restart. Explain why this points to a database readiness race.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Describe a startup sequence that waits for PostgreSQL readiness before running migrations or accepting traffic.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Explain how to handle repeated readiness failures with retry limits, clear logs, container health, and alerting.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned why PostgreSQL readiness needs explicit checks in containerized applications.",
            },
        ],
    },
    "docker_healthcheck_missing": {
        "lesson_id": "docker_healthcheck_missing",
        "course_id": "docker",
        "title": "Docker Healthcheck Missing",
        "difficulty": "hard",
        "steps": [
            {
                "type": "intro",
                "title": "Containers need health signals",
                "content": "Without healthchecks, orchestration tools may treat a process as healthy even when the application cannot serve real requests.",
            },
            {
                "type": "explanation",
                "title": "Healthchecks describe behavior",
                "content": "A good healthcheck verifies the service is actually ready, such as an API returning /health or a database accepting connections.",
            },
            {
                "type": "example",
                "title": "Compose healthcheck",
                "content": "healthcheck:\n  test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8000/health\"]\n  interval: 10s\n  timeout: 3s\n  retries: 5",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A container is marked running but the reverse proxy sends users to a failing backend. Explain why a missing healthcheck makes this harder to detect.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Design a healthcheck for a FastAPI backend and a PostgreSQL service, including what each should verify.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Explain how you would tune healthcheck interval, timeout, retries, and startup grace periods to avoid noisy restarts.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how healthchecks turn process status into useful readiness signals.",
            },
        ],
    },
    "env_variable_not_loaded": {
        "lesson_id": "env_variable_not_loaded",
        "course_id": "docker",
        "title": "Environment Variable Not Loaded",
        "difficulty": "hard",
        "steps": [
            {
                "type": "intro",
                "title": "Config can disappear at runtime",
                "content": "Environment variables may exist locally but be missing inside a container if Compose, env_file, or deployment configuration is incorrect.",
            },
            {
                "type": "explanation",
                "title": "Local shell is not the container",
                "content": "The variables available to your terminal are not automatically available inside Docker containers unless explicitly passed.",
            },
            {
                "type": "example",
                "title": "Compose env wiring",
                "content": "services:\n  backend:\n    env_file:\n      - .env\n    environment:\n      DATABASE_URL: ${DATABASE_URL}",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A backend container logs 'OPENAI_API_KEY is missing' even though .env exists on the host. Explain the likely configuration gap.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Describe how to pass required environment variables to a Docker Compose service without committing secrets.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Design a startup validation approach for required config that fails fast, logs safely, and avoids exposing secret values.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": "You learned how container environment configuration differs from local shell configuration and how to validate it safely.",
            },
        ],
    },
}


def get_lesson(lesson_id: str) -> dict | None:
    return LESSONS.get(lesson_id)
