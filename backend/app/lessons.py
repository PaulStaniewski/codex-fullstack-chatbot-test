LESSONS = {
    "docker_basics": {
        "lesson_id": "docker_basics",
        "course_id": "docker",
        "title": "Docker Basics",
        "difficulty": "easy",
        "steps": [
            {
                "type": "intro",
                "title": "What Docker is",
                "content": (
                    "Docker packages an app with the runtime, files, dependencies, and startup command "
                    "it needs. It exists to reduce works on my machine bugs by running the app in a "
                    "repeatable container instead of relying on each developer's laptop setup."
                ),
            },
            {
                "type": "concept",
                "title": "Images and containers",
                "content": (
                    "An image is the built template for your app; a container is a running instance of "
                    "that image. Think of the image as a recipe and the container as the meal being "
                    "served. Build means creating the image: installing packages, copying files, and "
                    "saving a default command. Run means starting a container from that image with runtime "
                    "settings like ports and environment variables. A container is not a full virtual "
                    "machine; it is an isolated process with its own filesystem, process view, network "
                    "view, and environment. Common trap: localhost inside a container means that same "
                    "container, not your database or host machine."
                ),
            },
            {
                "type": "example",
                "title": "A small backend Dockerfile",
                "content": (
                    "A FastAPI Dockerfile can look like this:\n\n"
                    "FROM python:3.12-slim\n"
                    "WORKDIR /app\n"
                    "COPY requirements.txt .\n"
                    "RUN pip install --no-cache-dir -r requirements.txt\n"
                    "COPY . .\n"
                    "CMD [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\n\n"
                    "FROM chooses Python on a small Linux base. WORKDIR makes /app the working folder. "
                    "COPY requirements.txt adds only the dependency list first. RUN installs those "
                    "dependencies into the image. This order helps caching: code edits do not reinstall "
                    "packages unless requirements.txt changes. COPY . . adds the app source. CMD is the "
                    "default command used when a container starts, not during image build."
                ),
            },
            {
                "type": "checklist",
                "title": "Docker basics checklist",
                "content": (
                    "- Decide first: is this a build failure or a run failure?\n"
                    "- Missing package? Check requirements.txt and rebuild the image.\n"
                    "- Database URL failing? Do not use localhost when you mean another container.\n"
                    "- App unreachable? Check host port mapping and the app bind address.\n"
                    "- Data disappeared? Use a volume instead of container storage.\n"
                    "- Read container logs before rebuilding or changing code."
                ),
            },
            {
                "type": "practice",
                "title": "Practice - Explain build and run",
                "difficulty": "easy",
                "content": (
                    "A developer changes requirements.txt, rebuilds the Docker image, then starts a new "
                    "container with DATABASE_URL set at runtime. Explain what happened during build, what "
                    "happens during run, and why the image and container are different."
                ),
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": (
                    "- Docker makes app runtime setup repeatable.\n"
                    "- An image is the built template; a container is the running instance.\n"
                    "- Build creates the image; run starts the container.\n"
                    "- localhost inside a container means that container.\n"
                    "- Reproducible images reduce works on my machine bugs."
                ),
            },
        ],
    },
    "docker_compose_basics": {
        "lesson_id": "docker_compose_basics",
        "course_id": "docker",
        "title": "Docker Compose Basics",
        "difficulty": "easy",
        "steps": [
            {
                "type": "intro",
                "title": "Why Compose exists",
                "content": (
                    "Most fullstack apps need more than one process. You may have a React frontend, a "
                    "FastAPI backend, PostgreSQL, and migrations. Docker Compose lets you describe those "
                    "services in one file so a developer can start the stack consistently. It turns setup "
                    "instructions into runnable configuration."
                ),
            },
            {
                "type": "concept",
                "title": "Services, networks, and volumes",
                "content": (
                    "A Compose service is one role in the system, such as backend, frontend, or db. "
                    "Compose creates a network where services can reach each other by service name. That "
                    "means a backend container should connect to PostgreSQL with host db, not localhost. "
                    "Ports expose services to your host machine. Volumes store data outside the container "
                    "so it can survive recreation."
                ),
            },
            {
                "type": "example",
                "title": "A small API stack",
                "content": (
                    "A local stack might define backend and db services. The backend builds from "
                    "./backend, publishes 8000:8000, and gets DATABASE_URL set to "
                    "postgresql://postgres:postgres@db:5432/app. The db service uses the postgres image "
                    "and stores files in a named volume. The important detail is the hostname: db works "
                    "inside the Compose network because it is the service name."
                ),
            },
            {
                "type": "checklist",
                "title": "Compose checklist",
                "content": (
                    "- Name services by role.\n"
                    "- Use service names for container-to-container connections.\n"
                    "- Publish only ports needed from the host.\n"
                    "- Use named volumes for persistent database data.\n"
                    "- Keep required environment variables explicit.\n"
                    "- Add healthchecks or retry logic for dependencies."
                ),
            },
            {
                "type": "practice",
                "title": "Practice - Design a local stack",
                "difficulty": "easy",
                "content": (
                    "Sketch a Compose setup for React, FastAPI, and PostgreSQL. Name the services, ports, "
                    "volume, and backend database hostname."
                ),
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": (
                    "- Compose runs a multi-service app from one file.\n"
                    "- Services communicate by service name.\n"
                    "- Host ports are separate from internal networking.\n"
                    "- Volumes preserve state.\n"
                    "- Startup order is not the same as readiness."
                ),
            },
        ],
    },
    "postgres_container_not_ready": {
        "lesson_id": "postgres_container_not_ready",
        "course_id": "docker",
        "title": "Postgres Container Not Ready",
        "difficulty": "medium",
        "steps": [
            {
                "type": "intro",
                "title": "Running is not ready",
                "content": (
                    "A PostgreSQL container can be running before PostgreSQL is ready for your app. The "
                    "backend may fail on first startup, then work after a restart. That usually means the "
                    "app depended on timing instead of readiness. Reliable setups check whether the "
                    "database can accept the real connection the backend needs."
                ),
            },
            {
                "type": "concept",
                "title": "Readiness means useful work can happen",
                "content": (
                    "Database readiness means more than an open port. The backend must resolve the host, "
                    "connect, authenticate, select the right database, and often run migrations. A good "
                    "startup flow retries expected temporary failures but stops after a clear deadline. "
                    "This keeps slow startup from becoming random failure while still exposing bad "
                    "credentials or broken migrations."
                ),
            },
            {
                "type": "example",
                "title": "Check the same database the app uses",
                "content": (
                    "A useful check is pg_isready -h db -U postgres -d app. The host db is the Compose "
                    "service name. The user and database should match the backend connection string. If "
                    "the backend must run migrations before serving, retry alembic upgrade head with a "
                    "maximum attempt count, then start Uvicorn only after migrations succeed."
                ),
            },
            {
                "type": "checklist",
                "title": "Postgres readiness checklist",
                "content": (
                    "- Read the exact connection error.\n"
                    "- Use the Compose service name, not localhost.\n"
                    "- Match POSTGRES_DB, POSTGRES_USER, and DATABASE_URL.\n"
                    "- Check Postgres logs during first startup.\n"
                    "- Remember old volumes may keep old state.\n"
                    "- Use bounded retries, not fixed sleeps."
                ),
            },
            {
                "type": "practice",
                "title": "Practice - Diagnose first-start failure",
                "difficulty": "medium",
                "content": (
                    "A backend fails with connection refused on first compose up but works after restart. "
                    "Explain why this points to readiness and list the first three checks you would make."
                ),
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": (
                    "- A running container is not always a ready database.\n"
                    "- Readiness should test the real app connection.\n"
                    "- Fixed sleeps are fragile.\n"
                    "- Volumes can preserve old database state.\n"
                    "- Retry startup work with a clear deadline."
                ),
            },
        ],
    },
    "docker_healthcheck_missing": {
        "lesson_id": "docker_healthcheck_missing",
        "course_id": "docker",
        "title": "Docker Healthcheck Missing",
        "difficulty": "medium",
        "steps": [
            {
                "type": "intro",
                "title": "Why healthchecks help",
                "content": (
                    "Docker can show that a container process is running, but that does not prove the "
                    "service is usable. A backend might be alive while the database connection is broken. "
                    "A healthcheck adds a small repeated test so developers and tools can see whether the "
                    "service is healthy."
                ),
            },
            {
                "type": "concept",
                "title": "A healthcheck is a service promise",
                "content": (
                    "A healthcheck is a command that exits successfully when the service passes a basic "
                    "self-test. For Postgres, that may be pg_isready. For FastAPI, it may be a /health "
                    "endpoint. The check should be cheap, reliable, and close to what other services need. "
                    "It should not depend on unrelated external systems unless the app truly cannot work "
                    "without them."
                ),
            },
            {
                "type": "example",
                "title": "Backend and database checks",
                "content": (
                    "A Postgres healthcheck can run pg_isready -U postgres -d app. A backend healthcheck "
                    "can call http://localhost:8000/health from inside the container. The database check "
                    "proves Postgres accepts connections. The backend check proves the API process can "
                    "respond. These checks help debugging, but the app still needs runtime error handling."
                ),
            },
            {
                "type": "checklist",
                "title": "Healthcheck checklist",
                "content": (
                    "- Check useful service behavior, not only process existence.\n"
                    "- Use commands available inside the image.\n"
                    "- Set a start period for slow services.\n"
                    "- Keep checks cheap and local.\n"
                    "- Test failure paths intentionally.\n"
                    "- Pair healthchecks with app-level retries."
                ),
            },
            {
                "type": "practice",
                "title": "Practice - Pick health signals",
                "difficulty": "medium",
                "content": (
                    "Choose one healthcheck for PostgreSQL and one for a FastAPI backend. Explain what "
                    "each check proves and what it does not prove."
                ),
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": (
                    "- Running is not the same as healthy.\n"
                    "- Healthchecks make service state visible.\n"
                    "- Good checks are cheap and meaningful.\n"
                    "- Timing settings reduce noise during startup.\n"
                    "- Healthchecks do not replace error handling."
                ),
            },
        ],
    },
    "docker_startup_race_condition": {
        "lesson_id": "docker_startup_race_condition",
        "course_id": "docker",
        "title": "Docker Compose Startup Race Condition",
        "difficulty": "hard",
        "steps": [
            {
                "type": "intro",
                "title": "Timing bugs in local stacks",
                "content": (
                    "A startup race happens when one service starts work before another service is ready. "
                    "In Compose, the backend may run migrations before Postgres accepts connections. If a "
                    "restart fixes the issue, the system probably relied on timing instead of an explicit "
                    "readiness rule."
                ),
            },
            {
                "type": "concept",
                "title": "Startup order is not readiness",
                "content": (
                    "depends_on can express that the backend should start after the database container, "
                    "but it does not prove the database can run queries or migrations. Readiness is "
                    "application-specific. A safe backend startup should wait for the real operation it "
                    "needs, such as a migration, and fail clearly if that operation never succeeds."
                ),
            },
            {
                "type": "example",
                "title": "Bounded retry before serving",
                "content": (
                    "A startup script can retry alembic upgrade head before starting Uvicorn. It should "
                    "log each failed attempt, sleep briefly, and stop after a maximum number of attempts. "
                    "After migrations succeed, it can exec uvicorn so the server receives shutdown signals "
                    "properly. This makes normal slow startup safe without hiding permanent failures."
                ),
            },
            {
                "type": "checklist",
                "title": "Race-condition checklist",
                "content": (
                    "- Identify the first operation that fails.\n"
                    "- Replace fixed sleeps with readiness checks or retries.\n"
                    "- Retry the real startup operation when possible.\n"
                    "- Add a maximum retry budget.\n"
                    "- Log attempt count and failing operation.\n"
                    "- Decide who owns migrations in multi-replica deployments."
                ),
            },
            {
                "type": "practice",
                "title": "Practice - Design startup retry",
                "difficulty": "hard",
                "content": (
                    "Design a bounded retry flow for a backend that must run migrations before serving "
                    "traffic. Include what it logs and when it exits."
                ),
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": (
                    "- Startup order does not prove readiness.\n"
                    "- Race conditions often look random.\n"
                    "- Retry real dependency operations, not arbitrary sleeps.\n"
                    "- Retry loops need deadlines.\n"
                    "- Migrations need clear ownership when services scale."
                ),
            },
        ],
    },
    "docker_production_hardening": {
        "lesson_id": "docker_production_hardening",
        "course_id": "docker",
        "title": "Docker Production Hardening",
        "difficulty": "production",
        "steps": [
            {
                "type": "intro",
                "title": "From runnable to safer",
                "content": (
                    "A container that runs locally is not automatically production-ready. Production "
                    "hardening reduces avoidable risk in the image, runtime configuration, process "
                    "permissions, logging, health signals, and shutdown behavior. The goal is not "
                    "perfection. The goal is a service that is easier to operate and safer when something "
                    "goes wrong."
                ),
            },
            {
                "type": "concept",
                "title": "Reduce blast radius",
                "content": (
                    "Hardening means limiting what the container can access and making behavior explicit. "
                    "Run as a non-root user when possible. Keep secrets out of images and source control. "
                    "Use small runtime images. Send logs to stdout or stderr. Expose health and readiness "
                    "signals. These choices reduce damage if the app fails or is compromised and make "
                    "operations easier to debug."
                ),
            },
            {
                "type": "example",
                "title": "A more production-minded image",
                "content": (
                    "A production-minded Python image may use python:3.12-slim, set PYTHONUNBUFFERED=1, "
                    "install dependencies without cache, copy only needed files, create an app user, and "
                    "run Uvicorn as that user. The image should not copy .env files or local data. A "
                    "release process should scan the final image and rebuild when base images or "
                    "dependencies receive security fixes."
                ),
            },
            {
                "type": "checklist",
                "title": "Production hardening checklist",
                "content": (
                    "- Run the app as non-root when possible.\n"
                    "- Keep secrets out of images and build logs.\n"
                    "- Use small runtime images.\n"
                    "- Log to stdout or stderr.\n"
                    "- Add useful health and readiness checks.\n"
                    "- Verify graceful shutdown."
                ),
            },
            {
                "type": "practice",
                "title": "Practice - Review a Dockerfile",
                "difficulty": "production",
                "content": (
                    "Review a Dockerfile that runs as root, copies .env, and writes logs to a file inside "
                    "the container. List the risks and the first fixes you would make."
                ),
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": (
                    "- Local success is not production readiness.\n"
                    "- Least privilege reduces risk.\n"
                    "- Secrets belong in runtime configuration, not images.\n"
                    "- Logs and healthchecks support operations.\n"
                    "- Images need regular review and rebuilds."
                ),
            },
        ],
    },
}


def get_lesson(lesson_id: str) -> dict | None:
    return LESSONS.get(lesson_id)
