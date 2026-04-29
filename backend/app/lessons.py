LESSONS = {
    "docker_basics": {
        "lesson_id": "docker_basics",
        "course_id": "docker",
        "title": "Docker Basics",
        "difficulty": "easy",
        "steps": [
            {
                "type": "intro",
                "title": "Why containers matter",
                "content": """Docker solves a very ordinary engineering problem: software often works on one machine and fails on another because the runtime, operating system packages, environment variables, ports, and startup commands are different. A container gives the application a repeatable execution environment. Instead of telling every developer to install the right Python version, Node version, PostgreSQL client, system libraries, and shell tools manually, the project describes the environment in a Dockerfile and runs it as a container. This matters for fullstack teams because frontend, backend, database, and worker processes all need predictable setup. Docker does not remove the need to understand your app, but it makes the runtime easier to share, rebuild, inspect, and automate in development, CI, demos, and production-like training environments.""",
            },
            {
                "type": "concept",
                "title": "Images, containers, and reproducibility",
                "content": """The core Docker concept is the difference between an image and a container. An image is a versioned template built from instructions: copy these files, install these packages, expose this port, and run this command. A container is a running instance of that image. This distinction solves a practical reproducibility problem. The team can rebuild the image when dependencies change, then run containers from that image in the same way on different machines. Docker also separates build-time concerns from run-time concerns. Installing dependencies belongs in the image build. Secrets, database URLs, and feature flags usually belong in environment variables at runtime. Use this model when you want a service to have a predictable filesystem and command, while still allowing configuration to change between local development, CI, and deployment.""",
            },
            {
                "type": "deep_dive",
                "title": "What Docker actually isolates",
                "content": """A container is not a tiny virtual machine. It is a process running on the host kernel with isolation around its filesystem, process tree, networking, and environment. That is why containers start quickly and why they still depend on the host operating system capabilities. Docker builds images in layers. Each instruction in a Dockerfile can create a cached layer, which makes rebuilds faster when earlier layers do not change. This also creates edge cases: copying package files before the full source tree can improve cache behavior, while copying everything too early can force dependency reinstallations on every code change. Another common mistake is assuming files written inside a container are permanent. Container filesystems are disposable unless data is stored in a mounted volume. Good Docker usage means understanding what is baked into the image, what is supplied at runtime, what persists, and what disappears when the container is recreated.""",
            },
            {
                "type": "example",
                "title": "A small backend Dockerfile",
                "content": """A simple Python backend image might start like this:\n\nFROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nCMD [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\n\nFROM chooses the base runtime. WORKDIR creates a predictable application directory. COPY requirements.txt before copying the full source lets Docker reuse the dependency layer when only app code changes. RUN installs dependencies into the image. The second COPY adds the application code. CMD describes the default command when the container starts. The expected behavior is that the same image can start the API without relying on a developer's local Python environment. In a real project, you would also consider non-root users, healthchecks, build context size, and environment-specific configuration.""",
            },
            {
                "type": "checklist",
                "title": "Docker basics checklist",
                "content": """- Confirm the Dockerfile starts from an appropriate base image for the language and runtime.\n- Keep dependency installation separate from application source copies so rebuilds stay fast.\n- Make the container command explicit and easy to inspect from logs or compose configuration.\n- Store runtime configuration in environment variables rather than hardcoding local paths or secrets.\n- Use volumes only for data that should survive container recreation.\n- Check which ports are exposed by the app and which ports are published to the host.\n- Rebuild the image when dependencies or Dockerfile instructions change, not just when code changes.""",
            },
            {
                "type": "practice",
                "title": "Practice - Explain the runtime boundary",
                "difficulty": "easy",
                "content": "A teammate says Docker is unnecessary because the app already works on their laptop. Explain what problems Docker still solves for a fullstack team and what Docker does not automatically solve.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": """- Docker images are reusable templates; containers are running instances of those templates.\n- Containers isolate the app process and filesystem, but they are not full virtual machines.\n- Runtime configuration should stay outside the image when it changes by environment.\n- Container data is disposable unless it is stored in a volume or external service.\n- Good Dockerfiles improve reproducibility, build speed, and team onboarding.\n- Production Docker work still requires security, observability, and careful configuration.""",
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
                "content": """A fullstack application rarely consists of one process. A realistic development setup may include a React frontend, a FastAPI backend, PostgreSQL, a migration command, and sometimes a cache or background worker. Starting each service manually creates hidden setup knowledge: which terminal starts which command, which ports must be open, which environment variables are required, and which service must exist before another one can work. Docker Compose turns that operational knowledge into a versioned file. This is valuable because setup becomes repeatable instead of tribal. A new developer can run one command and see the same service layout as everyone else. Compose is not only a local convenience; it is a way to learn service boundaries, networking, persistence, and startup behavior in a controlled environment.""",
            },
            {
                "type": "concept",
                "title": "A service graph in configuration",
                "content": """Docker Compose describes a group of services and the relationships between them. A service is a role in the system, such as backend, frontend, or db. Each service can define an image, build context, command, environment variables, ports, volumes, and healthchecks. Compose also creates a project network where services can reach each other by service name. This solves the problem of coordinating multiple processes consistently. Instead of documenting separate commands in a README and hoping every person runs them correctly, the compose file becomes executable documentation. Use Compose for local development, integration tests, demos, and benchmark projects where repeatability matters. It is especially useful for teaching because it makes dependencies visible: the backend depends on the database, the frontend depends on the API, and persistent state depends on volumes.""",
            },
            {
                "type": "deep_dive",
                "title": "How Compose wiring behaves",
                "content": """When docker compose up runs, Compose reads the YAML file, creates a default network, creates named volumes if needed, builds missing images, and starts containers for each service. Services on the same network can communicate using service names as DNS hostnames. That means a backend container should connect to PostgreSQL with host db, not localhost. Inside the backend container, localhost means the backend container itself. Compose also manages host port publishing separately from internal service communication. A port mapping like 8000:8000 lets your browser reach the backend from the host, but other containers usually use the service name and container port. Edge cases include stale named volumes, old images that were not rebuilt, environment variables interpolated on the host instead of passed into containers, and depends_on being mistaken for a readiness guarantee. Compose gives structure, but the application still needs explicit readiness and error handling.""",
            },
            {
                "type": "example",
                "title": "Compose file for a small API stack",
                "content": """A minimal API stack can be described like this:\n\nservices:\n  backend:\n    build: ./backend\n    ports:\n      - \"8000:8000\"\n    environment:\n      DATABASE_URL: postgresql://postgres:postgres@db:5432/app\n    depends_on:\n      - db\n  db:\n    image: postgres:16\n    environment:\n      POSTGRES_DB: app\n      POSTGRES_USER: postgres\n      POSTGRES_PASSWORD: postgres\n    volumes:\n      - postgres_data:/var/lib/postgresql/data\n\nvolumes:\n  postgres_data:\n\nThe backend builds from local source and publishes port 8000 to the host. DATABASE_URL points to db because db is the service name. The db service initializes PostgreSQL and stores data in a named volume. The expected behavior is that containers share a network and the database keeps data after restarts. This is still not production complete: readiness checks, secrets management, and safer startup commands are still needed.""",
            },
            {
                "type": "checklist",
                "title": "Compose review checklist",
                "content": """- Name services by their role so connection strings are readable and stable.\n- Use service names for container-to-container hostnames instead of localhost.\n- Publish only ports that humans or external tools need from the host machine.\n- Store database files in named volumes when data should survive container recreation.\n- Keep required environment variables explicit and avoid committing real secrets.\n- Rebuild images after dependency or Dockerfile changes, not only after source code changes.\n- Add healthchecks or retry behavior for services that depend on databases, queues, or external APIs.""",
            },
            {
                "type": "practice",
                "title": "Practice - Design a local stack",
                "difficulty": "easy",
                "content": "Sketch a Compose setup for a React, FastAPI, and PostgreSQL application. Explain which services need ports, which services need volumes, and how the backend should connect to the database.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": """- Compose describes a multi-service development environment in one file.\n- Services communicate by service name on the Compose network.\n- Host port mappings are separate from internal container networking.\n- Named volumes preserve state across container recreation.\n- depends_on helps with order but does not prove readiness.\n- A good compose file is both runnable infrastructure and useful documentation.""",
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
                "title": "The container is running, but Postgres is not ready",
                "content": """A PostgreSQL container can be running before the database is actually ready for application work. This creates one of the most common Docker Compose failures: the backend starts, immediately tries to connect, and crashes with connection refused, timeout, or authentication errors. A restart often appears to fix it because PostgreSQL finished initializing while the developer was reading the logs. That makes the problem feel random, but it is a startup sequencing issue. This matters in local development, CI, and deployment pipelines because unreliable startup reduces trust in the environment. A dependable Docker setup does not assume that a running container means a usable database. It verifies readiness with checks that match the real application connection and uses bounded retries around startup work such as migrations.""",
            },
            {
                "type": "concept",
                "title": "Readiness means useful work can happen",
                "content": """Database readiness means the database can perform the operation the application needs now. For a FastAPI backend, that usually means resolving the database hostname, opening a TCP connection, authenticating as the configured user, selecting the configured database, and running a simple query or migration. This concept solves the gap between process status and service capability. Docker can tell you that a container process exists, but only PostgreSQL can prove that it is accepting the same kind of connection the backend will use. Use readiness checks before running migrations, before marking an API healthy, and before allowing dependent services to handle traffic. Strong readiness checks use the real host, user, and database rather than only checking whether port 5432 is open.""",
            },
            {
                "type": "deep_dive",
                "title": "Postgres startup phases and hidden state",
                "content": """The official PostgreSQL image performs several phases during startup. On a fresh volume it creates the database cluster, applies environment-based initialization, may run scripts from docker-entrypoint-initdb.d, and then starts the server. On an existing volume it skips some initialization but may still replay logs, recover from an unclean shutdown, or wait on disk operations. During parts of this lifecycle, the container is alive but PostgreSQL is not ready for the backend's connection. Edge cases include wrong database names, credentials that changed after a volume was created, slow CI disks, old local volumes preserving unexpected state, and Compose networks that were recreated while containers were still restarting. A common mistake is adding a fixed sleep. Sleeps hide the race when the machine is fast and fail again when the environment is slower. A better design uses pg_isready plus application-level retry with clear logs and a deadline.""",
            },
            {
                "type": "example",
                "title": "Database-aware readiness check",
                "content": """A useful readiness check targets the same service identity the app uses:\n\npg_isready -h db -U postgres -d app\n\nThe -h db option uses the Compose service name. The -U postgres option checks the configured user. The -d app option checks the intended database. In Compose, this can become a healthcheck, while the backend still retries its startup operation:\n\nuntil alembic upgrade head; do\n  echo \"Database not ready for migrations, retrying...\"\n  sleep 2\ndone\nuvicorn app.main:app --host 0.0.0.0 --port 8000\n\nThe expected behavior is not infinite waiting. Normal initialization should delay startup briefly. Bad credentials, missing databases, or broken migrations should eventually fail with logs that explain which operation could not complete.""",
            },
            {
                "type": "checklist",
                "title": "Postgres readiness checklist",
                "content": """- Read the exact error: connection refused, timeout, authentication failed, and unknown database point to different causes.\n- Run readiness checks from inside the Compose network so hostname and routing match the backend.\n- Confirm DATABASE_URL uses the database service name, not localhost.\n- Check that POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD match the backend connection string.\n- Inspect Postgres logs for initialization, recovery, permissions, or script failures.\n- Treat persistent volumes as possible hidden state when environment variables changed.\n- Wrap migrations or startup queries in bounded retry logic with clear failure messages.""",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A backend fails on first compose up with connection refused, then works after docker compose restart. Diagnose why this points to readiness rather than a missing dependency.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Design a startup script that waits for PostgreSQL by retrying the real migration command with a maximum wait time and useful logs.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Explain how you would adapt this local readiness pattern for production, including health endpoints, migration ownership, alerts, and what should happen if the database never becomes ready.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": """- A running database container is not the same as a ready database service.\n- Readiness checks should use the same host, user, and database as the application.\n- Fixed sleeps are fragile because startup time changes across machines and environments.\n- Application-level retry should be bounded and should log the failing operation.\n- Persistent volumes can preserve old state and make configuration changes confusing.\n- Reliable startup combines database-aware checks, migration retry, and clear failure behavior.""",
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
                "title": "Why healthchecks change debugging",
                "content": """Without healthchecks, Docker can usually tell you whether a container process is running, but it cannot tell whether the service inside that container is actually usable. A backend process might be alive while its database connection is broken. PostgreSQL might be running while it is still initializing. A frontend server might listen on a port while serving stale configuration. Healthchecks give containers a small self-test that reports whether the service is healthy from the perspective that matters to dependents. This matters because logs alone are reactive: you notice failure after another service crashes or a user reports a problem. Healthchecks make service state visible earlier, improve Compose orchestration, and provide a shared diagnostic vocabulary when a multi-container app starts behaving strangely.""",
            },
            {
                "type": "concept",
                "title": "A healthcheck is an executable contract",
                "content": """A healthcheck is a command that Docker runs inside a container on a schedule. The command exits with success when the service is healthy and failure when it is not. This solves the problem of guessing whether a dependency is usable. For PostgreSQL, the check might run pg_isready. For a FastAPI backend, it might call a /health endpoint that verifies the app has started and can reach required dependencies. Healthchecks are used by Compose, operators, and humans to understand service state. They should be cheap, deterministic, and specific enough to catch meaningful failure. A weak healthcheck that only checks whether a process exists can create false confidence. A strong healthcheck tells you whether the service can do the basic work other services depend on.""",
            },
            {
                "type": "deep_dive",
                "title": "Designing useful health signals",
                "content": """A healthcheck runs repeatedly, so it must balance accuracy with cost. If it checks too little, it misses real failures. If it checks too much, it can overload dependencies or fail during harmless transient states. Docker healthchecks have interval, timeout, retries, and start_period options. start_period is important for services like databases that need time to initialize before failures should count. Edge cases include commands missing from minimal images, shell syntax that works locally but not inside the container, credentials not available to the healthcheck process, and checks that depend on external internet access. Healthchecks also do not replace application retry. A service can become unhealthy after startup, and dependent apps still need runtime error handling. The goal is layered reliability: healthchecks expose state, startup scripts wait intelligently, and application code handles failures that occur after the system is already running.""",
            },
            {
                "type": "example",
                "title": "Compose healthcheck examples",
                "content": """A database healthcheck can look like this:\n\nservices:\n  db:\n    image: postgres:16\n    healthcheck:\n      test: [\"CMD-SHELL\", \"pg_isready -U postgres -d app\"]\n      interval: 5s\n      timeout: 3s\n      retries: 10\n      start_period: 10s\n\nA backend healthcheck can call an internal endpoint:\n\n  backend:\n    build: ./backend\n    healthcheck:\n      test: [\"CMD\", \"python\", \"-c\", \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\"]\n      interval: 10s\n      timeout: 3s\n      retries: 5\n\nThe expected behavior is that Docker reports health based on real service checks. If the command fails repeatedly after the start period, the container is marked unhealthy, which gives developers a direct signal instead of forcing them to infer readiness from logs.""",
            },
            {
                "type": "checklist",
                "title": "Healthcheck checklist",
                "content": """- Choose a check that proves the service can perform useful work, not only that a process exists.\n- Keep the command available inside the image; minimal images may not include curl, wget, or shell tools.\n- Set start_period long enough for normal initialization so slow startup is not reported as failure.\n- Keep checks cheap and local when possible to avoid creating load or depending on the public internet.\n- Log enough information in the app so failed healthchecks can be diagnosed quickly.\n- Pair healthchecks with application retry because dependencies can fail after startup.\n- Test healthcheck behavior by intentionally breaking credentials, ports, or readiness assumptions.""",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "medium",
                "content": "A backend starts before the database is usable, and docker ps only shows both containers as running. Explain what diagnostic signal is missing.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Write a Compose healthcheck strategy for PostgreSQL and the backend. Explain what each check proves and what it does not prove.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Describe how healthchecks should interact with deployment readiness, runtime monitoring, restart policies, and alerting in a production environment.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": """- Healthchecks turn hidden service readiness into an observable signal.\n- A useful check proves basic service capability, not just process existence.\n- start_period, interval, timeout, and retries control how noisy or patient the check is.\n- Healthchecks do not replace application-level retry or runtime error handling.\n- Minimal images may not contain the tools your healthcheck command assumes.\n- Production systems use healthchecks as one layer in readiness, monitoring, and recovery.""",
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
                "title": "Timing bugs in multi-container apps",
                "content": """A startup race condition happens when one container begins work before another container is ready to support it. In a fullstack Docker setup, the backend might start and run Alembic migrations before PostgreSQL accepts connections. The failure often disappears after a restart, which makes it tempting to blame Docker itself. The real issue is usually that the system depended on timing instead of an explicit readiness contract. This matters because timing bugs create flaky development, flaky CI, and risky deployments. They also train teams to use fixed sleeps, which work only until the environment gets slower. A reliable container system describes service order, checks readiness, retries expected transient failures, and exits clearly when a dependency never becomes usable.""",
            },
            {
                "type": "concept",
                "title": "Startup order is not readiness",
                "content": """The central concept is that container startup order is not the same as application readiness. Compose can start the database container before the backend container, but it cannot automatically know when PostgreSQL is ready for migrations. depends_on describes a structural relationship, not a complete operational guarantee. This distinction solves a common misconception. Orchestration can help arrange containers, but the application must still handle the real dependency operation it needs: connect to the database, authenticate, acquire locks, run migrations, and start serving only when required setup is complete. This pattern applies beyond PostgreSQL. Caches, queues, object storage emulators, model servers, and internal APIs can all have process startup that happens before usable readiness. Correct systems use layered checks rather than relying on luck.""",
            },
            {
                "type": "deep_dive",
                "title": "Layered startup reliability",
                "content": """A mature startup flow usually has several layers. Compose can express dependency order and optional health conditions. The dependency can expose a healthcheck that proves basic readiness. The dependent service can retry the exact operation it needs, such as alembic upgrade head, because that operation proves more than an open port. The backend can expose its own health endpoint only after startup initialization succeeds. Finally, logs and monitoring should show whether startup is slow, repeatedly failing, or blocked by configuration. Edge cases include migrations that are not safe to run from multiple replicas, healthchecks that pass before a required extension or database exists, old volumes with incompatible schema, and retry loops that hide permanent failures. The goal is not to wait forever. The goal is to tolerate normal transient startup delay while failing loudly and safely when the dependency is genuinely broken.""",
            },
            {
                "type": "example",
                "title": "Bounded retry before serving",
                "content": """A simple startup command can retry migrations before starting the web server:\n\n#!/bin/sh\nset -e\n\nattempt=1\nmax_attempts=30\n\nuntil alembic upgrade head; do\n  if [ \"$attempt\" -ge \"$max_attempts\" ]; then\n    echo \"Database never became ready for migrations\"\n    exit 1\n  fi\n  echo \"Migration attempt $attempt failed; retrying in 2 seconds\"\n  attempt=$((attempt + 1))\n  sleep 2\ndone\n\nexec uvicorn app.main:app --host 0.0.0.0 --port 8000\n\nThe script retries the real startup operation, not just a generic ping. set -e stops on unexpected failures outside the retry loop. exec lets Uvicorn receive container signals properly. The expected behavior is patient startup during normal database initialization and clear failure when the database or migration chain is actually broken.""",
            },
            {
                "type": "checklist",
                "title": "Race-condition checklist",
                "content": """- Identify which operation fails first: DNS resolution, TCP connection, authentication, migration, or application import.\n- Remove fixed sleeps and replace them with checks or retries tied to real dependency behavior.\n- Add a maximum retry budget so broken configuration does not loop forever.\n- Make logs include attempt count, target service, and failing operation.\n- Ensure only one process owns schema migrations in multi-replica deployments.\n- Expose backend readiness only after required startup work is complete.\n- Test slow database startup intentionally instead of waiting for the race to appear randomly.""",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "hard",
                "content": "A FastAPI container crashes on alembic upgrade head during docker compose up, but succeeds when restarted. Explain why this is a startup race and identify which logs you would inspect first.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "hard",
                "content": "Design a bounded retry startup flow for a backend that must run migrations before serving traffic. Include how it should log and how it should fail.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Explain how the design changes when the backend runs multiple replicas and migrations should not be executed concurrently by every container.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": """- Startup order does not guarantee that a dependency is ready for useful work.\n- depends_on can express structure, but readiness needs healthchecks and application retry.\n- Retrying the real startup operation often proves more than checking an open port.\n- Retry loops must have limits and clear logs so permanent failures are visible.\n- Migration ownership becomes important when multiple backend replicas exist.\n- Reliable startup is layered across Compose, scripts, app readiness, and monitoring.""",
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
                "title": "From runnable to dependable",
                "content": """A container that runs locally is not automatically ready for production. Production hardening is the work of making the image, configuration, runtime behavior, and operational signals safe enough for real users. Local Docker setups often optimize for convenience: broad environment access, root users, bind mounts, verbose logs, and quick rebuilds. Production needs different priorities: smaller images, limited privileges, explicit configuration, predictable shutdown, health and readiness signals, secret handling, resource awareness, and vulnerability management. This matters because containers can make deployment feel simple while hiding serious operational risk. A hardened Docker service should be reproducible, observable, least-privileged, and recoverable. The goal is not perfection; it is reducing avoidable failure modes before users and operators pay for them.""",
            },
            {
                "type": "concept",
                "title": "Hardening reduces blast radius",
                "content": """The core concept of production hardening is blast-radius reduction. If something fails or is compromised, the container should expose as little as possible and recover as predictably as possible. This includes running as a non-root user, avoiding unnecessary packages, keeping secrets out of images, pinning important dependency versions, exposing only required ports, and ensuring shutdown signals are handled cleanly. Hardening is used when moving from a benchmark or demo to an environment where uptime, data protection, and incident response matter. It solves practical problems: a leaked image should not contain credentials, a compromised process should not have root privileges by default, and a restart should not corrupt state. Good hardening also improves debugging because the system's assumptions are explicit.""",
            },
            {
                "type": "deep_dive",
                "title": "Operational details that matter",
                "content": """Production Docker reliability is shaped by many small decisions. Image size affects deploy speed and vulnerability surface. Running as root increases risk if the app or dependency is exploited. A process that does not receive SIGTERM correctly may be killed before finishing in-flight work. Logs written only to files inside the container may disappear during recreation; logs should usually go to stdout or stderr for the platform to collect. Healthchecks and readiness endpoints need to reflect real service state without overloading dependencies. Secrets should come from the runtime platform, not the Dockerfile. Resource limits should be understood because memory pressure can kill containers abruptly. Edge cases include multi-stage builds that accidentally copy build tools into runtime images, cached layers that keep vulnerable dependencies, and environment variables that differ silently between staging and production. Hardening is a review habit, not a one-time checklist.""",
            },
            {
                "type": "example",
                "title": "A more production-minded Dockerfile",
                "content": """A backend image can be improved like this:\n\nFROM python:3.12-slim AS runtime\nENV PYTHONDONTWRITEBYTECODE=1 \\\n    PYTHONUNBUFFERED=1\nWORKDIR /app\nRUN adduser --disabled-password --gecos \"\" appuser\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nUSER appuser\nCMD [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\n\nThe slim base reduces unnecessary packages. PYTHONUNBUFFERED helps logs appear promptly. The non-root user reduces privilege if the process is compromised. Dependencies are installed before source copy to preserve build caching. The command keeps the process in the foreground so the container runtime can manage it. This example is not complete security, but it demonstrates the direction: fewer privileges, clearer runtime behavior, and image contents that match production needs.""",
            },
            {
                "type": "checklist",
                "title": "Production hardening checklist",
                "content": """- Run the application as a non-root user unless there is a documented reason not to.\n- Keep secrets out of Dockerfiles, images, build logs, and committed compose files.\n- Use small runtime images and remove build-only tools from production images.\n- Send logs to stdout or stderr so the platform can collect and retain them.\n- Add health and readiness checks that represent real service capability.\n- Confirm the process handles shutdown signals and does not lose important in-flight work.\n- Scan images and rebuild regularly when base images or dependencies receive security fixes.\n- Set resource expectations and observe memory, CPU, restart count, and startup duration.""",
            },
            {
                "type": "practice",
                "title": "Practice 1 - Diagnose",
                "difficulty": "production",
                "content": "Review a Dockerfile that runs as root, copies .env into the image, and writes logs to /tmp/app.log. Identify the production risks and rank the most urgent fixes.",
            },
            {
                "type": "practice",
                "title": "Practice 2 - Fix",
                "difficulty": "production",
                "content": "Propose a hardened Dockerfile and runtime configuration for a FastAPI backend. Include user permissions, logging, secrets, and startup command choices.",
            },
            {
                "type": "practice",
                "title": "Practice 3 - Production hardening",
                "difficulty": "production",
                "content": "Design an operational review checklist for Docker images before release, including vulnerability scanning, healthchecks, rollback readiness, and secret handling.",
            },
            {
                "type": "summary",
                "title": "Summary",
                "content": """- A locally runnable container still needs production hardening before serving users.\n- Hardening reduces blast radius through least privilege, smaller images, and explicit runtime behavior.\n- Secrets should be injected at runtime, not baked into images or source control.\n- Logs, healthchecks, and shutdown behavior are part of production reliability.\n- Image scanning and rebuild discipline matter because base images and dependencies age.\n- Production Docker quality comes from repeated operational review, not one magic setting.""",
            },
        ],
    },
}


DOCKER_DEPTH_SUPPLEMENTS = {
    "docker_basics": {
        1: " In practice, this lets teams separate three questions that are often confused: what software is installed, what command starts the service, and what configuration changes between environments. Once those questions are separate, Docker becomes easier to reason about during onboarding, debugging, and deployment reviews.",
        2: " Docker also gives each container its own network view. A service can listen on port 8000 inside the container while the host maps that port differently, or not at all. That distinction prevents accidental assumptions about what is reachable from the browser, from another container, or from the host operating system. Understanding those boundaries is essential when a backend cannot reach a database, a frontend cannot reach an API, or a port appears to be in use.",
    },
    "docker_compose_basics": {
        1: " A well-written Compose file also gives reviewers a map of the system. They can see which service owns the database, which service exposes HTTP traffic, which values are configurable, and which parts of the stack are stateful. That makes Compose useful beyond startup because it documents architecture in a form the machine can execute.",
        2: " Compose also scopes resources by project. Networks, containers, and volumes may be named with a project prefix, which is why two checkouts of the same repository can sometimes create separate stacks. That isolation is helpful, but it means debugging should always confirm which project, volume, and container are actually running. Otherwise a developer may inspect logs from an old container or wonder why a schema change did not appear after rebuilding an image.",
    },
    "postgres_container_not_ready": {
        1: " This is especially important before schema migrations. A migration is not just a connection test; it proves the application can reach the database, authenticate, inspect version state, and apply changes. When readiness is defined around the real operation, failures become easier to classify and logs become more useful.",
        2: " Readiness can also regress after startup. A database may pass an initial check and later restart because of memory pressure, disk problems, or an operator action. That is why readiness checks should be paired with normal runtime error handling and observability. Startup retry gets the service online safely; runtime handling keeps it honest after the first successful connection.",
    },
    "docker_healthcheck_missing": {
        1: " The best healthchecks are written from the perspective of the service contract. If other services need PostgreSQL to accept SQL connections, check that. If users need the backend to answer HTTP requests after startup, check that. A healthcheck should therefore be small, repeatable evidence that the service can satisfy its most basic promise.",
        2: " Healthchecks also affect human debugging behavior. When a container is marked unhealthy, developers know to inspect that service first instead of chasing failures in every dependent container. In CI, health status can explain why an integration test started too early. In production, health status can drive load balancers, restart policies, or alerts, depending on the platform. The signal is only useful if it represents the real service condition rather than an overly shallow command.",
    },
    "docker_startup_race_condition": {
        0: " These issues are worth studying because they are easy to create accidentally and hard to trust once they appear. A race condition damages confidence in the whole environment: developers stop believing fresh setup works, CI reruns become normal, and deployment failures are dismissed as timing noise instead of fixed directly.",
        1: " A useful mental model is to ask what fact has actually been proven. Starting a container proves that Docker launched a process. Opening a port proves that something is listening. Running a migration proves much more: name resolution, network path, credentials, database selection, migration locks, and schema history are all usable enough for the app to proceed.",
        2: " There is also a coordination issue when teams grow. One developer may add depends_on, another may add a healthcheck, and another may add a startup script. If those pieces are not designed together, the system can still fail in confusing ways. The cleanest approach defines which layer provides which guarantee and documents that boundary near the Compose file or startup script.",
    },
    "docker_production_hardening": {
        0: " The same image that feels convenient in development can become a liability when it contains unnecessary tools, runs with broad privileges, or depends on configuration that only exists on one laptop. Hardening turns local success into an operational contract that can be reviewed, repeated, and monitored.",
        1: " This concept is used during release preparation, security review, incident response, and platform migration. It helps teams ask concrete questions: what can this process access, what happens when it is restarted, how are secrets supplied, how do we know it is healthy, and how quickly can we rebuild it after a dependency vulnerability?",
        2: " Multi-stage builds are another important production tool. They let the build stage contain compilers or package managers while the runtime stage contains only what the service needs to run. This reduces image size and removes tools attackers do not need to find. Production hardening also means checking the surrounding runtime: filesystem permissions, network exposure, environment injection, restart policy, and whether the platform can stop the service gracefully during deploys.",
    },
}

for lesson_id, step_updates in DOCKER_DEPTH_SUPPLEMENTS.items():
    for step_index, extra_content in step_updates.items():
        LESSONS[lesson_id]["steps"][step_index]["content"] += extra_content

DOCKER_CONTENT_POLISH = {
    "docker_basics": {
        3: """\n\nA useful way to read this Dockerfile is to separate build preparation from runtime behavior. The requirements file is copied before the application source so dependency installation can be cached independently from normal code edits. The final CMD is not executed during image build; it becomes the default command when the container starts. If the app fails at runtime, inspect whether the image built successfully, whether dependencies were installed in the image, whether the working directory contains the expected files, and whether the command binds to 0.0.0.0 so traffic from outside the container can reach the server.""",
        4: """\n- Inspect the final image with docker image history when builds are unexpectedly slow or large.\n- Run docker logs on a failed container before rebuilding, because startup errors often explain the real issue.\n- Confirm the app listens on an interface reachable from outside the container, usually 0.0.0.0 for web services.""",
        6: """\n- When debugging, ask whether the problem belongs to image build, container runtime, networking, or persistent data.\n- In production, avoid treating a working local container as proof that security, observability, and lifecycle behavior are ready.""",
    },
    "docker_compose_basics": {
        3: """\n\nRead this configuration as a small service contract. The backend service owns application startup, while the db service owns persistent database state. The DATABASE_URL deliberately uses db as the hostname because Compose provides DNS for service names on the project network. The volume declaration is separate from the service definition because named volumes are managed resources in the Compose project. If the backend cannot connect, the first checks should be the service name, the database credentials, the active Compose project, and whether an old volume was initialized with different values.""",
        4: """\n- Use docker compose ps to see container state, published ports, and health information in one place.\n- Use docker compose logs <service> to inspect one service without losing the context of the full stack.\n- Keep compose service names stable because connection strings and documentation often depend on them.""",
        6: """\n- A Compose file should make the system understandable before anyone runs it.\n- If a service depends on another service, document both the network path and the readiness expectation.\n- Review Compose changes like application code because they affect developer setup, tests, and release behavior.""",
    },
    "postgres_container_not_ready": {
        3: """\n\nThe migration retry loop is intentionally tied to the real operation the backend needs. A generic wait-for-port script can say that something is listening, but it cannot prove the configured database exists or that Alembic can record schema state. The loop should be paired with a maximum attempt count because infinite startup hides broken credentials and blocks deployment feedback. In a team setting, the log message should name the failing dependency and operation so developers can distinguish normal initialization delay from a migration conflict or configuration mistake.""",
        4: """\n- Compare the DATABASE_URL used by the app with the values printed in container environment inspection.\n- Remove or recreate only the intended local volume when testing first-start behavior; do not casually destroy shared data.\n- Verify whether failures happen before migrations start, during migration locking, or after the backend begins serving.""",
        8: """\n- The most reliable check is close to the real workload, not merely close to the container process.\n- Production systems should expose readiness separately from liveness so traffic is not routed too early.\n- A startup fix is incomplete unless permanent misconfiguration still fails loudly.""",
    },
    "docker_healthcheck_missing": {
        3: """\n\nThe database healthcheck uses CMD-SHELL because pg_isready is executed as a shell command with arguments. The interval controls how often Docker runs it, timeout controls how long one check may take, retries controls how many failures are tolerated, and start_period gives the service time to initialize before failures count. The backend example uses Python instead of curl so it works even in images that do not install curl. The expected behavior is that health status becomes a visible signal for humans and tooling, but the application still handles real runtime failures after startup.""",
        4: """\n- Confirm the healthcheck command exists inside the container image, not only on the host machine.\n- Test both success and failure paths by temporarily breaking credentials or stopping a dependency.\n- Keep healthcheck output clear enough that logs explain what the check attempted.\n- Avoid checks that depend on unrelated public services unless the app truly cannot operate without them.""",
        8: """\n- A healthcheck is useful only if it reflects the service promise other components rely on.\n- Health status should guide debugging, not replace logs, metrics, or application error handling.\n- In production, tune healthcheck timing so normal startup is tolerated but real failure is detected quickly.""",
    },
    "docker_startup_race_condition": {
        3: """\n\nThis script also demonstrates a clean handoff between setup and serving. Migration retry happens before Uvicorn starts, so the backend does not accept requests while schema state is unknown. The final exec is important because it replaces the shell with the Uvicorn process, allowing container stop signals to reach the server directly. In production, this exact pattern may move into an entrypoint script, init job, or release task, but the principle is the same: startup dependencies should be verified before the service advertises readiness.""",
        4: """\n- Check whether multiple backend replicas could run the same startup migration at the same time.\n- Separate transient dependency errors from deterministic migration errors in logs and alerting.\n- Test the failure path by using bad credentials and confirming the container exits instead of looping forever.""",
        8: """\n- Race conditions often look random because timing changes between machines and restarts.\n- Make readiness explicit in configuration, startup scripts, and application health endpoints.\n- Production hardening includes deciding who owns migrations when services scale horizontally.""",
    },
    "docker_production_hardening": {
        3: """\n\nThis Dockerfile still needs project-specific review, but it shows several production habits. The runtime image is intentionally slim, Python writes logs without buffering, and the process does not run as root. Dependency installation happens before source copy for cache efficiency. A real release pipeline would also pin dependency versions, scan the final image, avoid copying test fixtures or local secrets, and verify that the service can shut down gracefully. Expected behavior is not just that the API starts, but that it starts with fewer unnecessary privileges and fewer hidden assumptions.""",
        4: """\n- Verify the build context does not include .env files, local databases, node_modules, virtual environments, or generated secrets.\n- Check that the container can be stopped gracefully within the platform's termination window.\n- Confirm runtime configuration comes from the deployment environment and is visible enough to debug without exposing secrets.\n- Review whether the image can be rebuilt quickly when a base-image vulnerability is announced.""",
        8: """\n- Production readiness includes the image, the runtime platform, release process, and operational signals.\n- Least privilege, secret hygiene, health signals, and graceful shutdown reduce avoidable incident risk.\n- The safest Docker systems are reviewed continuously as dependencies, infrastructure, and threat models change.""",
    },
}

for lesson_id, step_updates in DOCKER_CONTENT_POLISH.items():
    for step_index, extra_content in step_updates.items():
        LESSONS[lesson_id]["steps"][step_index]["content"] += extra_content

DOCKER_ARTICLE_REWRITE = {
    "docker_basics": {
        0: """Docker is often introduced as a packaging tool, but the bigger idea is repeatable runtime behavior. A backend that works on one laptop can fail on another because the Python version, operating system packages, environment variables, ports, or startup command are different.

Containers give a team a shared boundary around the application process. Instead of relying on every developer to manually recreate the same environment, the project describes that environment in a Dockerfile and runs it as a container.

This matters most when an application grows beyond a single script. A fullstack project may include a backend API, frontend build tooling, a database client, migration commands, and system libraries. Docker makes those assumptions visible.

In real projects, Docker also helps with onboarding. A new contributor should not need a long checklist of local installations before they can run the app. The container becomes a documented, executable setup path.

Docker does not remove the need to understand deployment, security, networking, or persistence. It gives you a controlled environment where those concerns can be discussed more clearly.

The practical goal is not just to make the app start. The goal is to know what is inside the runtime, what is configured from outside, what data survives restarts, and how to debug the service when something fails.""",
        1: """The central Docker concept is the difference between an image and a container. An image is a template built from instructions. A container is a running process created from that template.

This separation solves an important engineering problem. The team can review and rebuild the image when dependencies change, then run containers from that image in a consistent way across machines.

A Dockerfile describes build-time decisions. It chooses a base image, copies files, installs dependencies, sets a working directory, and defines a default command. Those decisions become part of the image.

Runtime configuration is different. Database URLs, feature flags, API keys, and environment-specific values are usually passed when the container starts. This keeps one image usable in more than one environment.

Docker is used when the application needs a predictable filesystem, dependency set, and startup command. It is especially useful when different services in the same project require different runtimes.

The model also helps debugging. If a dependency is missing, ask whether the image was built correctly. If a secret is wrong, ask whether runtime configuration was supplied correctly.

Good Docker practice means keeping the image reproducible while keeping environment-specific configuration outside the image. That boundary is the foundation for the rest of the course.""",
        2: """A container is not a small virtual machine. It is a process running on the host kernel with isolation around filesystem, networking, process visibility, and environment.

When Docker builds an image, it creates layers. Each Dockerfile instruction can create a layer that may be cached during future builds. This is why instruction order affects build speed.

For example, copying requirements.txt before copying the whole application lets Docker reuse the dependency-install layer when only source code changes. Copying all source first often invalidates the cache too early.

At runtime, the container has its own filesystem view. Files written inside the container disappear when the container is removed unless they are stored in a volume or an external service.

Networking has similar boundaries. An app can listen on port 8000 inside the container, but the host cannot reach that port unless it is published. Other containers may reach it differently through a Docker network.

A common mistake is using localhost from inside a container when the developer means another service. Inside the backend container, localhost means the backend container itself, not the host machine and not the database container.

Another mistake is rebuilding an image when the real problem is runtime configuration. If the Dockerfile did not change but DATABASE_URL did, the fix is usually configuration, not a new image layer.

The internal behavior matters because Docker bugs are often boundary bugs. You debug them by asking which boundary is involved: build cache, container filesystem, host networking, service networking, environment variables, or persistent storage.""",
        3: """A small backend Dockerfile might look like this:

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM selects the base runtime. In this case, the image starts from a slim Python 3.12 environment rather than depending on Python installed on the host machine.

WORKDIR creates a predictable directory for the application. Every following command runs from /app unless another working directory is set.

COPY requirements.txt and RUN pip install create a dependency layer. This is intentionally placed before copying the full source tree so normal code edits do not reinstall dependencies every time.

COPY . . adds the application source. CMD defines what runs when the container starts. Binding Uvicorn to 0.0.0.0 is important because the server must listen beyond the container's loopback interface.

The expected behavior is that anyone with Docker can build the image and run the backend without installing Python packages directly on their machine. Production versions would also review user permissions, image size, secret handling, and healthchecks.""",
        4: """- Check whether a failure happens during image build or container startup; those are different phases with different fixes.
- Inspect the Dockerfile instruction order when builds are unexpectedly slow or dependencies reinstall too often.
- Confirm the application listens on an interface reachable from outside the container, usually 0.0.0.0 for HTTP services.
- Verify which configuration comes from runtime environment variables instead of hardcoded files.
- Check whether important data is written to a disposable container filesystem or to a volume.
- Use docker logs before rebuilding; startup errors often explain the real cause.
- Ask whether networking should use a host port, a container port, or a service name on a Docker network.""",
        6: """- Docker images are reusable runtime templates; containers are running instances of those templates.
- Build-time dependencies belong in the image, while environment-specific configuration usually belongs at runtime.
- Containers isolate the process and filesystem, but they are not full virtual machines.
- Files inside a container are disposable unless stored in a volume or external service.
- Most Docker debugging starts by identifying the boundary involved: build, runtime config, network, or persistence.
- A working local container is a starting point, not proof that production security and operations are ready.""",
    },
    "docker_compose_basics": {
        0: """Docker Compose exists because real applications are rarely one process. A useful development environment often needs a backend, frontend, database, migration command, and sometimes a cache or worker.

Without Compose, every developer has to remember several commands and run them in the right order. That knowledge usually lives in a README, terminal history, or one teammate's memory.

Compose turns that knowledge into configuration. The compose file describes which services exist, how they start, which ports they expose, which variables they need, and which volumes keep data.

This matters for onboarding and debugging. A new developer can run one command and see the same service graph as the rest of the team instead of assembling the stack by hand.

Compose also makes architecture visible. When you read the file, you can see the backend depends on the database, the frontend talks to the API, and the database stores state in a volume.

In production, teams may use other orchestrators, but the Compose mental model remains valuable. You learn to think in services, networks, configuration, startup behavior, and persistent state.""",
        1: """A Compose file describes a group of services. Each service represents one role in the application, such as backend, frontend, db, worker, or cache.

The service definition can choose an image, build from a Dockerfile, publish ports, pass environment variables, mount volumes, and define healthchecks. This creates an executable service graph.

Compose creates a default network for the project. Services on that network can reach each other by service name, which means the backend can connect to the database using db as the hostname.

This solves a common local-development problem. Instead of asking whether PostgreSQL is installed locally or which port it uses on the host, the backend connects to the Compose-managed database service.

Compose is used for development environments, demos, integration tests, and benchmark projects. It is best when the goal is repeatable multi-service setup rather than full production orchestration.

The file also documents state. A named volume shows that database data should survive container recreation, while a bind mount shows that host files are being shared into a container.

The important concept is that Compose coordinates services, but it does not automatically make those services correct. Readiness, credentials, migrations, and safe shutdown still need deliberate design.""",
        2: """When docker compose up runs, Compose reads the YAML file and creates project resources. Those resources usually include containers, a default network, and any named volumes declared by the project.

If a service has a build section, Compose can build an image from a Dockerfile. If a service uses image, Compose pulls or reuses that image. Then it starts containers for each service.

Networking is one of the most important behaviors. Inside the Compose network, service names become DNS names. A backend should usually connect to postgresql://...@db:5432/... rather than localhost.

Port publishing is separate. A mapping like 8000:8000 lets the host browser reach the backend, but other containers do not need the host mapping to communicate on the internal network.

Volumes are also managed separately from containers. Removing and recreating containers does not necessarily remove named volumes, which is why old database state can survive many rebuilds.

Environment variables have two phases that are easy to confuse. Compose may interpolate values from the host while reading the YAML, and it may also pass values into the container environment.

A common mistake is assuming depends_on means the dependency is ready. It mostly expresses startup order. A database can be started but still initializing, so readiness checks and retry logic remain necessary.

The internal behavior explains many local bugs. If the wrong database state appears, inspect volumes. If a hostname fails, inspect the service name and network. If a value is missing, inspect both host interpolation and container environment.""",
        3: """A small Compose file for an API and database can look like this:

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/app
    depends_on:
      - db
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:

The backend service builds from local source and publishes port 8000 so the host browser can reach it. DATABASE_URL uses db because db is the service name on the Compose network.

The db service uses the official PostgreSQL image and declares initial database settings. The named volume stores database files outside the disposable container lifecycle.

The expected behavior is that Compose creates one network, starts both containers, and lets the backend connect to PostgreSQL through the service name. A more reliable version would add healthchecks and bounded backend startup retry.""",
        4: """- Use service names for container-to-container hostnames instead of localhost.
- Publish only the ports humans or host tools need to access directly.
- Inspect named volumes when database state survives rebuilds or appears stale.
- Keep required environment variables explicit and avoid committing real secrets.
- Use docker compose ps to check service state, ports, and health information.
- Use docker compose logs <service> to debug one service while preserving stack context.
- Add healthchecks or retries for services that depend on databases, queues, or external APIs.""",
        6: """- Compose describes a multi-service application in one executable configuration file.
- Services communicate by name on the Compose network, while host port mappings serve host access.
- Named volumes preserve state after containers are recreated.
- depends_on can help with order, but it does not prove readiness.
- A good compose file documents architecture as well as startup commands.
- Debug Compose issues by checking service names, networks, volumes, environment variables, and logs.""",
    },
    "postgres_container_not_ready": {
        0: """A PostgreSQL container can be running while PostgreSQL itself is still not ready for the backend. This is one of the most common Docker Compose problems in fullstack projects.

The symptom is usually frustrating. The backend fails on the first startup with connection refused, timeout, or migration errors, then works after a restart.

That restart is the clue. If time fixes the issue without a code change, the system probably relied on timing rather than a clear readiness signal.

This matters in local development because unreliable startup makes the whole environment feel flaky. It matters even more in CI, where slower machines and parallel jobs make timing problems more visible.

It also matters in production-style deployments. A database can be alive as a process while it is recovering, applying initialization, or not yet accepting the exact connection the app needs.

The lesson is simple but important: container running state is not the same as service readiness. A reliable app verifies readiness with checks and retries that match the real database operation.""",
        1: """Database readiness means the database can do the useful work the application needs right now. For a backend, that is more than opening a TCP port.

A useful readiness check should prove that the backend can resolve the database hostname, open a connection, authenticate as the configured user, select the configured database, and run a basic operation.

This concept solves the gap between infrastructure state and application state. Docker can report that the postgres container is running, but PostgreSQL must prove it can serve the app.

Readiness is used before running migrations, before accepting HTTP traffic, and before marking a deployment as available. It is part of startup safety.

The exact check depends on the workload. A simple app may use pg_isready. A backend that must run migrations may retry the migration command because that is the operation that must succeed.

Readiness is not a permanent guarantee. A database can become unavailable later because of restart, disk pressure, memory pressure, network interruption, or operator action.

That is why startup readiness and runtime error handling work together. Startup checks get the app online safely; runtime handling keeps the app honest after the first successful connection.""",
        2: """The official PostgreSQL image performs several steps during startup. On a fresh volume, it creates the database cluster, applies environment-based initialization, and may run scripts from docker-entrypoint-initdb.d.

Only after that setup does the server become ready for normal client connections. During the earlier phases, the container process can exist even though the app cannot yet use the database.

On an existing volume, initialization may be skipped, but startup can still involve recovery, log replay, or permission checks. Existing state can make one machine behave differently from another.

Credentials are another common edge case. If a volume was initialized with old credentials, changing POSTGRES_PASSWORD in Compose does not rewrite the existing database state.

Networking adds another layer. The backend must use the Compose service name and correct port. Using localhost inside the backend container points to the backend container, not the database.

Fixed sleeps are a fragile workaround. A five-second sleep may pass on a fast laptop and fail in CI. A thirty-second sleep may hide real configuration mistakes and slow every startup.

Better systems use bounded retry around the real operation. If migrations must run before serving, retry migrations with clear logs and a maximum wait time.

The step-by-step debugging path is to inspect the error type, verify the connection string, check database logs, test readiness from inside the Docker network, and confirm whether persistent volume state is involved.""",
        3: """A database-aware readiness check can target the same identity the app uses:

pg_isready -h db -U postgres -d app

The -h db option uses the Compose service name. The -U postgres option checks the configured user. The -d app option checks the intended database.

For a backend that must run migrations, the startup command can retry the real migration:

until alembic upgrade head; do
  echo "Database not ready for migrations, retrying..."
  sleep 2
done
uvicorn app.main:app --host 0.0.0.0 --port 8000

The readiness check tells you whether PostgreSQL accepts connections. The migration retry tells you whether the application can perform the operation required before serving.

The expected behavior is patient startup during normal database initialization and clear failure when credentials, database names, or migrations are truly broken. In production, the loop should also have a maximum attempt count.""",
        4: """- Read the exact error message before changing configuration; connection refused, timeout, authentication failed, and unknown database mean different things.
- Run readiness checks from inside the Compose network so hostname and routing match the backend.
- Confirm DATABASE_URL uses the database service name, not localhost.
- Compare POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD with the backend connection string.
- Inspect PostgreSQL logs for initialization, recovery, permissions, or script failures.
- Treat persistent volumes as possible hidden state when credentials or database names changed.
- Wrap migrations or startup queries in bounded retry logic with clear failure messages.""",
        8: """- A running PostgreSQL container is not necessarily ready for application connections.
- Readiness should prove the operation the application actually needs.
- Fixed sleeps are unreliable because startup time changes between environments.
- Persistent volumes can preserve old credentials, databases, and schema state.
- Backend startup should retry expected transient failures but fail clearly after a deadline.
- Production readiness should be separate from liveness so traffic is not routed too early.""",
    },
    "docker_healthcheck_missing": {
        0: """Without healthchecks, Docker can tell you whether a container process is running, but not whether the service is useful. That distinction matters in multi-container systems.

A backend process might be alive while its database connection is broken. PostgreSQL might be running while it is still initializing. A frontend server might respond while serving the wrong configuration.

Healthchecks give the container a small self-test. The result becomes visible as healthy, unhealthy, or starting, which is much more informative than running alone.

This matters during development because it points debugging at the right service. If the database is unhealthy, the backend failure is probably a symptom rather than the first cause.

It matters in CI because tests often start as soon as containers exist. A health signal can prevent integration tests from racing the services they depend on.

It matters in production because platforms can use health and readiness signals to decide when to route traffic, restart services, or alert operators. The signal must be meaningful, not decorative.""",
        1: """A healthcheck is an executable contract. It is a command that runs inside the container and exits successfully when the service passes its basic self-test.

The contract should match what other services need. If the backend needs PostgreSQL to accept SQL connections, the database healthcheck should test PostgreSQL readiness, not just process existence.

For an API, a healthcheck may call an HTTP endpoint. That endpoint might simply confirm the process is alive, or it might also verify required dependencies depending on whether it is liveness or readiness.

This concept is used whenever service state should be observable. Developers use it during local debugging. CI uses it before tests. Production platforms use it for routing and recovery decisions.

The healthcheck command should be cheap enough to run repeatedly. A check that performs expensive work can create load or introduce its own failure mode.

It should also be specific enough to catch meaningful failures. A check that always returns success gives false confidence and can make incidents harder to understand.

The best healthchecks are boring, local, deterministic, and tied to a real service promise. They do not replace logs or metrics, but they make service state visible sooner.""",
        2: """Docker healthchecks run repeatedly according to timing settings. interval controls how often the check runs, timeout controls how long one check may take, retries controls how many failures are tolerated, and start_period gives startup time before failures count.

These settings matter because services have different startup profiles. PostgreSQL may need time to initialize a fresh volume, while a simple static server may be ready almost immediately.

The command runs inside the container. This creates a common edge case: curl may exist on the host but not inside a minimal runtime image. The healthcheck must use tools available in the image.

Another edge case is checking too much. If a healthcheck depends on an external public API, the container may become unhealthy because the internet is briefly unavailable, even though the local service is fine.

Checking too little is also risky. A command that only confirms a process exists may miss broken credentials, missing databases, or a backend that cannot finish startup.

Healthchecks are signals, not complete recovery systems. An unhealthy container still needs logs, metrics, and operator context to explain why it is unhealthy.

They also do not replace application retry. A dependency can pass a healthcheck and then fail later. Runtime code still needs timeouts and error handling.

A useful design layers these concerns: healthchecks expose state, startup scripts wait for required dependencies, application code handles runtime failures, and monitoring tracks patterns over time.""",
        3: """A PostgreSQL healthcheck can look like this:

services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d app"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s

The test command runs inside the database container. pg_isready checks whether PostgreSQL is accepting connections for the configured user and database.

The start_period gives PostgreSQL time to initialize before failures count. retries prevents one transient failure from immediately marking the service unhealthy.

A backend healthcheck might call a local endpoint:

test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

This uses Python instead of curl so it works in images that do not install curl. The expected behavior is that health status reflects real service capability, while logs explain the cause when the check fails.""",
        4: """- Confirm the healthcheck command exists inside the container image, not only on the host.
- Choose a check that proves useful service behavior rather than process existence alone.
- Tune start_period so normal initialization is not reported as failure.
- Keep healthchecks cheap and local unless the service truly depends on an external system.
- Test the failure path by temporarily breaking credentials, ports, or dependencies.
- Make application logs explain what failed when healthchecks report unhealthy status.
- Pair healthchecks with retry and runtime error handling because health can change after startup.""",
        8: """- Healthchecks turn hidden readiness assumptions into visible service state.
- A useful healthcheck is an executable version of the service's basic contract.
- Timing settings control whether checks are patient, noisy, strict, or too slow.
- Healthchecks should guide debugging but not replace logs, metrics, or error handling.
- Minimal images may not include the tools your healthcheck command assumes.
- Production systems use health signals as one layer in readiness, routing, restart, and alerting decisions.""",
    },
    "docker_startup_race_condition": {
        0: """A startup race condition happens when one service begins work before another service is ready. In Docker Compose, this often appears when a backend starts before PostgreSQL can accept connections.

The failure may look random. The first docker compose up fails, but a restart works. Nothing changed except time, which is the strongest clue that readiness was assumed instead of verified.

This topic matters because race conditions destroy trust in the development environment. Developers start rerunning commands instead of understanding failures.

It also matters in CI. Automated jobs are less forgiving than humans, and slower runners often expose startup assumptions that fast laptops hide.

In production-style systems, startup races can turn into deployment incidents. A service may announce readiness before migrations, dependencies, or caches are actually prepared.

The real lesson is that container orchestration cannot guess every application requirement. The app must define what must be true before it starts accepting work.""",
        1: """Startup order is not readiness. Compose can start one container before another, but it does not automatically know when the application inside a container is ready.

depends_on expresses a structural dependency. It can say the backend should start after the database container starts, but container start does not mean PostgreSQL can run migrations.

Readiness is application-specific. For one service, readiness might mean an HTTP port is open. For another, it might mean a database connection, a completed migration, or a warmed cache.

This concept is used whenever a service performs startup work before serving. Databases, queues, caches, object storage emulators, and internal APIs can all have delayed readiness.

The fix is not always one tool. Healthchecks, startup scripts, migration ownership, application retries, and readiness endpoints each solve part of the problem.

A helpful mental model is to ask what has actually been proven. Starting a container proves Docker launched a process. Running a migration proves much more about the database path.

Reliable startup design means choosing the proof that matches the risk. If schema state matters before requests are served, prove schema setup before the server announces readiness.""",
        2: """A mature startup sequence has layers. Compose defines services and relationships. Healthchecks expose basic service state. Startup scripts wait for required operations. The application exposes readiness only after initialization succeeds.

Consider database migrations. A backend may need to resolve the database hostname, authenticate, select the correct database, inspect the migration table, acquire locks, apply schema changes, and then start serving HTTP.

Checking only that port 5432 is open proves very little. It does not prove credentials, database name, migration history, or migration safety.

Retrying the real migration command proves much more, but it must be bounded. Infinite retry loops hide broken configuration and can make deployments appear stuck instead of failed.

Multiple replicas create another edge case. If every backend container runs migrations at startup, they may compete or corrupt assumptions. Production systems often move migrations to one release step or job.

Healthchecks can also be misleading. A database can pass pg_isready before a specific database extension or schema is available. A backend can pass liveness while still not ready for traffic.

Old volumes add another failure mode. The database may be ready but contain schema state from an earlier branch, causing migrations or application queries to fail.

Debugging proceeds step by step: identify the first failed operation, check whether startup order or readiness was assumed, inspect logs, reproduce slow startup, and add explicit proof where the system relied on timing.""",
        3: """A bounded startup script can retry migrations before serving:

#!/bin/sh
set -e

attempt=1
max_attempts=30

until alembic upgrade head; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Database never became ready for migrations"
    exit 1
  fi
  echo "Migration attempt $attempt failed; retrying in 2 seconds"
  attempt=$((attempt + 1))
  sleep 2
done

exec uvicorn app.main:app --host 0.0.0.0 --port 8000

set -e stops the script on unexpected failures outside the retry loop. The loop retries the real dependency operation with a maximum attempt count.

The final exec replaces the shell with Uvicorn so container stop signals reach the server process. The expected behavior is patient startup during normal database initialization and clear failure when the dependency never becomes usable.""",
        4: """- Identify the first operation that fails: DNS, TCP connection, authentication, migration lock, schema query, or app import.
- Replace fixed sleeps with readiness checks or retries tied to real dependency behavior.
- Add a maximum retry budget so broken configuration does not loop forever.
- Include attempt count, target service, and failing operation in startup logs.
- Decide whether migrations are safe to run from every container or need one owner.
- Expose backend readiness only after required startup work has completed.
- Test slow database startup intentionally so the race is reproduced under controlled conditions.""",
        8: """- Startup races often look random because timing changes between restarts and machines.
- Container startup order does not prove application readiness.
- Retrying the real startup operation is usually stronger than checking an open port.
- Retry loops must have deadlines and useful logs.
- Multi-replica deployments need a clear migration ownership strategy.
- Reliable startup is layered across Compose configuration, dependency health, startup scripts, app readiness, and monitoring.""",
    },
    "docker_production_hardening": {
        0: """A container that runs locally is not automatically ready for production. Local setups often optimize for speed and convenience, while production needs safety, observability, and predictable recovery.

Production hardening is the process of reducing avoidable risk in the image, runtime configuration, process behavior, and operational signals.

This matters because containers can make deployment feel deceptively simple. The same abstraction that hides local setup complexity can also hide root users, copied secrets, missing healthchecks, and poor shutdown behavior.

Real systems fail in ordinary ways. A dependency vulnerability appears. A container restarts during traffic. A secret is accidentally copied into an image. Logs disappear because they were written to an internal file.

Hardening does not mean making the container perfect. It means making the most common and expensive failure modes less likely, easier to detect, and easier to recover from.

The practical outcome is a service that can be rebuilt, deployed, stopped, observed, and reviewed with confidence. Production Docker is operational engineering, not just packaging.""",
        1: """The core concept is blast-radius reduction. If the service fails or is compromised, the container should expose as little as possible and recover as predictably as possible.

Running as a non-root user reduces the impact of application compromise. Keeping secrets out of images reduces the damage if an image is shared or leaked.

Small runtime images reduce unnecessary tools and packages. This can reduce vulnerability surface and make image scanning easier to understand.

Explicit configuration reduces surprises. The service should not depend on a developer's local files, hidden environment variables, or bind mounts that do not exist in deployment.

Hardening is used during release preparation, security review, platform migration, and incident response. It gives teams concrete questions to ask before the service reaches users.

The concept also improves debugging. When logs go to stdout, healthchecks are meaningful, and shutdown is graceful, operators can understand the service without entering the container.

Good hardening is continuous. Base images age, dependencies change, threat models evolve, and deployment platforms impose new constraints. The review has to repeat.""",
        2: """Production Docker behavior depends on many small technical choices. The base image determines available packages, default users, update cadence, and vulnerability surface.

The build process determines what enters the final image. If test files, local secrets, virtual environments, or build tools are copied accidentally, the runtime image carries unnecessary risk.

User permissions matter. A process running as root has more power inside the container than most web services need. A non-root user limits damage if the process is exploited.

Signal handling matters too. Containers are stopped with signals. If the app or shell wrapper does not pass SIGTERM correctly, the platform may kill the service before it finishes in-flight work.

Logging should usually go to stdout or stderr so the platform can collect it. Logs written only to files inside the container may disappear when the container is recreated.

Health and readiness signals need to represent real service state. A container that is alive but cannot reach required dependencies should not receive user traffic.

Secrets should be injected by the runtime environment, not baked into the Dockerfile or committed compose files. Baked secrets are hard to rotate and easy to leak.

Edge cases include cached vulnerable layers, multi-stage builds that still copy build artifacts into runtime images, and environment drift between staging and production. Hardening is the discipline of finding these issues before an incident.""",
        3: """A more production-minded Dockerfile might look like this:

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN adduser --disabled-password --gecos "" appuser
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

The slim base limits unnecessary packages. PYTHONUNBUFFERED makes logs appear promptly in container output. The non-root user reduces privilege.

Dependency installation happens before source copy to preserve build caching. USER appuser ensures the server runs without root privileges.

The expected behavior is not merely that the API starts. The expected behavior is that it starts with clearer runtime assumptions, fewer privileges, and logs that the platform can collect. A release pipeline should also scan the final image and verify secrets are not copied into it.""",
        4: """- Run the application as a non-root user unless there is a documented reason not to.
- Keep secrets out of Dockerfiles, image layers, build logs, and committed compose files.
- Use small runtime images and avoid copying build-only tools into production images.
- Send logs to stdout or stderr so the deployment platform can collect them.
- Add health and readiness checks that represent real service capability.
- Verify the process handles shutdown signals within the platform's termination window.
- Scan images and rebuild when base images or dependencies receive security fixes.
- Check that the build context excludes .env files, local databases, virtual environments, and generated secrets.""",
        8: """- Production readiness includes image contents, runtime configuration, process lifecycle, and operational signals.
- Least privilege reduces blast radius when something fails or is compromised.
- Secrets should be injected at runtime rather than baked into images.
- Logs, healthchecks, and graceful shutdown are reliability features, not decoration.
- Image scanning and rebuild discipline matter because dependencies age.
- Production Docker quality comes from repeated review as the app, platform, and threat model change.""",
    },
}

for lesson_id, step_updates in DOCKER_ARTICLE_REWRITE.items():
    for step_index, content in step_updates.items():
        LESSONS[lesson_id]["steps"][step_index]["content"] = content


def get_lesson(lesson_id: str) -> dict | None:
    return LESSONS.get(lesson_id)
