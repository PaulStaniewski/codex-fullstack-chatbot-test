export const learningStructure = [
  {
    id: "backend",
    title: "Backend Engineering",
    modules: [
      {
        id: "fastapi-basics",
        title: "FastAPI Basics",
        lessons: [
          { id: "fastapi_intro", title: "FastAPI Introduction", difficulty: "easy" },
          { id: "fastapi_routing", title: "FastAPI Routing", difficulty: "easy" },
          { id: "fastapi_dependency", title: "Dependency Injection", difficulty: "easy" },
        ],
      },
      {
        id: "database-migrations",
        title: "Database & Migrations",
        lessons: [
          {
            id: "alembic_missing_column",
            title: "Debugging Alembic Missing Column Errors",
            difficulty: "medium",
          },
          {
            id: "alembic_revision_too_long",
            title: "Alembic Revision ID Too Long",
            difficulty: "hard",
          },
          {
            id: "duplicate_migration_head",
            title: "Duplicate Alembic Migration Head",
            difficulty: "hard",
          },
          {
            id: "missing_foreign_key_constraint",
            title: "Missing Foreign Key Constraint",
            difficulty: "hard",
          },
        ],
      },
      {
        id: "user-isolation",
        title: "User Isolation",
        lessons: [
          {
            id: "sqlAlchemy_user_scoped_queries",
            title: "User-Scoped Database Queries",
            difficulty: "hard",
          },
        ],
      },
    ],
  },
  {
    id: "docker",
    title: "Docker Foundations",
    modules: [
      {
        id: "containers-compose",
        title: "Containers & Compose",
        lessons: [{ id: "docker_basics", title: "Docker Basics", difficulty: "easy" }],
      },
      {
        id: "startup-reliability",
        title: "Startup Reliability",
        lessons: [
          {
            id: "docker_startup_race_condition",
            title: "Docker Compose Startup Race Condition",
            difficulty: "medium",
          },
          {
            id: "postgres_container_not_ready",
            title: "Postgres Container Not Ready",
            difficulty: "hard",
          },
          {
            id: "docker_healthcheck_missing",
            title: "Docker Healthcheck Missing",
            difficulty: "hard",
          },
          {
            id: "env_variable_not_loaded",
            title: "Environment Variable Not Loaded",
            difficulty: "hard",
          },
        ],
      },
    ],
  },
  {
    id: "frontend",
    title: "Frontend Architecture",
    modules: [
      {
        id: "eventsource-auth",
        title: "EventSource Auth",
        lessons: [
          {
            id: "sse_eventsource_auth",
            title: "SSE Authentication with EventSource",
            difficulty: "medium",
          },
          {
            id: "eventsource_token_expired",
            title: "EventSource Token Expired",
            difficulty: "hard",
          },
          {
            id: "duplicate_stream_messages",
            title: "Duplicate Stream Messages",
            difficulty: "hard",
          },
        ],
      },
    ],
  },
  {
    id: "ai",
    title: "AI Engineering",
    modules: [
      {
        id: "streaming-ai",
        title: "Streaming AI",
        lessons: [
          {
            id: "openai_streaming_errors",
            title: "Handling OpenAI Streaming Errors",
            difficulty: "medium",
          },
          {
            id: "openai_rate_limit_handling",
            title: "OpenAI Rate Limit Handling",
            difficulty: "production",
          },
          {
            id: "partial_stream_failure",
            title: "Partial Stream Failure",
            difficulty: "production",
          },
        ],
      },
    ],
  },
];
