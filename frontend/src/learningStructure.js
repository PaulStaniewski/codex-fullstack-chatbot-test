export const learningStructure = [
  {
    id: "backend",
    title: "Backend Engineering",
    modules: [
      {
        id: "fastapi-basics",
        title: "FastAPI Basics",
        lessons: [
          { id: "fastapi_intro", title: "FastAPI Introduction" },
          { id: "fastapi_routing", title: "FastAPI Routing" },
          { id: "fastapi_dependency", title: "Dependency Injection" },
        ],
      },
      {
        id: "database-migrations",
        title: "Database & Migrations",
        lessons: [
          { id: "alembic_missing_column", title: "Debugging Alembic Missing Column Errors" },
        ],
      },
      {
        id: "user-isolation",
        title: "User Isolation",
        lessons: [
          { id: "sqlAlchemy_user_scoped_queries", title: "User-Scoped Database Queries" },
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
        lessons: [{ id: "docker_basics", title: "Docker Basics" }],
      },
      {
        id: "startup-reliability",
        title: "Startup Reliability",
        lessons: [
          {
            id: "docker_startup_race_condition",
            title: "Docker Compose Startup Race Condition",
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
        lessons: [{ id: "sse_eventsource_auth", title: "SSE Authentication with EventSource" }],
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
        lessons: [{ id: "openai_streaming_errors", title: "Handling OpenAI Streaming Errors" }],
      },
    ],
  },
];
