export const learningStructure = [
  {
    id: "fastapi",
    title: "FastAPI Fundamentals",
    lessons: [
      { id: "fastapi_intro", title: "FastAPI Introduction" },
      { id: "fastapi_routing", title: "FastAPI Routing" },
      { id: "fastapi_dependency", title: "Dependency Injection" },
    ],
  },
  {
    id: "docker",
    title: "Docker Foundations",
    lessons: [
      { id: "docker_basics", title: "Docker Basics" },
      {
        id: "docker_startup_race_condition",
        title: "Docker Compose Startup Race Condition",
      },
    ],
  },
  {
    id: "backend",
    title: "Backend Engineering",
    lessons: [
      { id: "alembic_missing_column", title: "Debugging Alembic Missing Column Errors" },
      { id: "sqlAlchemy_user_scoped_queries", title: "User-Scoped Database Queries" },
    ],
  },
  {
    id: "frontend",
    title: "Frontend Architecture",
    lessons: [
      { id: "sse_eventsource_auth", title: "SSE Authentication with EventSource" },
    ],
  },
  {
    id: "ai",
    title: "AI Engineering",
    lessons: [
      { id: "openai_streaming_errors", title: "Handling OpenAI Streaming Errors" },
    ],
  },
];
