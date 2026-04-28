export const learningStructure = [
  {
    id: "fastapi",
    title: "FastAPI",
    modules: [
      {
        id: "fastapi-foundations",
        title: "Level 1 - Foundations",
        lessons: [
          { id: "fastapi_intro", title: "FastAPI Introduction", difficulty: "easy" },
          { id: "fastapi_routing", title: "FastAPI Routing", difficulty: "easy" },
        ],
      },
      {
        id: "fastapi-implementation",
        title: "Level 2 - Implementation",
        lessons: [
          {
            id: "fastapi_dependency_injection",
            title: "FastAPI Dependency Injection",
            difficulty: "medium",
          },
          {
            id: "fastapi_request_validation",
            title: "FastAPI Request Validation",
            difficulty: "medium",
          },
          {
            id: "fastapi_error_handling",
            title: "FastAPI Error Handling",
            difficulty: "medium",
          },
        ],
      },
      {
        id: "fastapi-debugging",
        title: "Level 3 - Debugging",
        lessons: [
          { id: "fastapi_auth_jwt_flow", title: "FastAPI JWT Auth Flow", difficulty: "hard" },
          {
            id: "fastapi_database_sessions",
            title: "FastAPI Database Sessions",
            difficulty: "hard",
          },
          {
            id: "fastapi_background_tasks",
            title: "FastAPI Background Tasks",
            difficulty: "hard",
          },
        ],
      },
      {
        id: "fastapi-production",
        title: "Level 4 - Production",
        lessons: [
          {
            id: "fastapi_startup_shutdown_lifespan",
            title: "FastAPI Startup, Shutdown, and Lifespan",
            difficulty: "production",
          },
          {
            id: "fastapi_rate_limits_and_security",
            title: "FastAPI Rate Limits and Security",
            difficulty: "production",
          },
        ],
      },
    ],
  },
  {
    id: "docker",
    title: "Docker",
    modules: [
      {
        id: "docker-foundations",
        title: "Level 1 - Foundations",
        lessons: [
          { id: "docker_basics", title: "Docker Basics", difficulty: "easy" },
          { id: "docker_compose_basics", title: "Docker Compose Basics", difficulty: "easy" },
        ],
      },
      {
        id: "docker-implementation",
        title: "Level 2 - Implementation",
        lessons: [
          {
            id: "docker_environment_variables",
            title: "Docker Environment Variables",
            difficulty: "medium",
          },
          { id: "docker_networking", title: "Docker Networking", difficulty: "medium" },
          { id: "docker_volumes", title: "Docker Volumes", difficulty: "medium" },
        ],
      },
      {
        id: "docker-debugging",
        title: "Level 3 - Debugging",
        lessons: [
          {
            id: "postgres_container_not_ready",
            title: "Postgres Container Not Ready",
            difficulty: "hard",
          },
          {
            id: "docker_startup_race_condition",
            title: "Docker Compose Startup Race Condition",
            difficulty: "hard",
          },
          {
            id: "env_variable_not_loaded",
            title: "Environment Variable Not Loaded",
            difficulty: "hard",
          },
        ],
      },
      {
        id: "docker-production",
        title: "Level 4 - Production",
        lessons: [
          {
            id: "docker_healthcheck_missing",
            title: "Docker Healthcheck Missing",
            difficulty: "production",
          },
          {
            id: "docker_production_hardening",
            title: "Docker Production Hardening",
            difficulty: "production",
          },
        ],
      },
    ],
  },
  {
    id: "backend",
    title: "Backend Engineering",
    modules: [
      {
        id: "backend-foundations",
        title: "Level 1 - Foundations",
        lessons: [
          {
            id: "backend_api_design_basics",
            title: "Backend API Design Basics",
            difficulty: "easy",
          },
          {
            id: "backend_user_owned_resources",
            title: "Backend User-Owned Resources",
            difficulty: "easy",
          },
        ],
      },
      {
        id: "backend-implementation",
        title: "Level 2 - Implementation",
        lessons: [
          {
            id: "sqlAlchemy_user_scoped_queries",
            title: "User-Scoped Database Queries",
            difficulty: "medium",
          },
          {
            id: "missing_foreign_key_constraint",
            title: "Missing Foreign Key Constraint",
            difficulty: "medium",
          },
          {
            id: "database_transaction_basics",
            title: "Database Transaction Basics",
            difficulty: "medium",
          },
        ],
      },
      {
        id: "backend-debugging",
        title: "Level 3 - Debugging",
        lessons: [
          {
            id: "alembic_missing_column",
            title: "Debugging Alembic Missing Column Errors",
            difficulty: "hard",
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
        ],
      },
      {
        id: "backend-production",
        title: "Level 4 - Production",
        lessons: [
          {
            id: "backend_data_isolation_audit",
            title: "Backend Data Isolation Audit",
            difficulty: "production",
          },
          {
            id: "backend_migration_release_strategy",
            title: "Backend Migration Release Strategy",
            difficulty: "production",
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
        id: "frontend-foundations",
        title: "Level 1 - Foundations",
        lessons: [
          {
            id: "frontend_component_state_basics",
            title: "Frontend Component State Basics",
            difficulty: "easy",
          },
          {
            id: "frontend_api_client_basics",
            title: "Frontend API Client Basics",
            difficulty: "easy",
          },
        ],
      },
      {
        id: "frontend-implementation",
        title: "Level 2 - Implementation",
        lessons: [
          {
            id: "frontend_auth_token_storage",
            title: "Frontend Auth Token Storage",
            difficulty: "medium",
          },
          {
            id: "frontend_loading_error_states",
            title: "Frontend Loading and Error States",
            difficulty: "medium",
          },
          {
            id: "frontend_markdown_rendering",
            title: "Frontend Markdown Rendering",
            difficulty: "medium",
          },
        ],
      },
      {
        id: "frontend-debugging",
        title: "Level 3 - Debugging",
        lessons: [
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
          {
            id: "stale_state_after_refresh",
            title: "Stale State After Refresh",
            difficulty: "hard",
          },
        ],
      },
      {
        id: "frontend-production",
        title: "Level 4 - Production",
        lessons: [
          {
            id: "frontend_stream_reconnect_strategy",
            title: "Frontend Stream Reconnect Strategy",
            difficulty: "production",
          },
          {
            id: "frontend_security_xss_markdown",
            title: "Frontend Security for Markdown and XSS",
            difficulty: "production",
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
        id: "ai-foundations",
        title: "Level 1 - Foundations",
        lessons: [
          { id: "ai_prompting_basics", title: "AI Prompting Basics", difficulty: "easy" },
          {
            id: "ai_context_window_basics",
            title: "AI Context Window Basics",
            difficulty: "easy",
          },
        ],
      },
      {
        id: "ai-implementation",
        title: "Level 2 - Implementation",
        lessons: [
          {
            id: "openai_streaming_basics",
            title: "OpenAI Streaming Basics",
            difficulty: "medium",
          },
          { id: "ai_structured_outputs", title: "AI Structured Outputs", difficulty: "medium" },
          {
            id: "ai_prompt_builder_design",
            title: "AI Prompt Builder Design",
            difficulty: "medium",
          },
        ],
      },
      {
        id: "ai-debugging",
        title: "Level 3 - Debugging",
        lessons: [
          {
            id: "openai_rate_limit_handling",
            title: "OpenAI Rate Limit Handling",
            difficulty: "hard",
          },
          { id: "partial_stream_failure", title: "Partial Stream Failure", difficulty: "hard" },
          {
            id: "invalid_json_from_model",
            title: "Invalid JSON from Model",
            difficulty: "hard",
          },
        ],
      },
      {
        id: "ai-production",
        title: "Level 4 - Production",
        lessons: [
          {
            id: "ai_safe_error_handling",
            title: "AI Safe Error Handling",
            difficulty: "production",
          },
          {
            id: "ai_evaluation_and_regression_tests",
            title: "AI Evaluation and Regression Tests",
            difficulty: "production",
          },
        ],
      },
    ],
  },
];
