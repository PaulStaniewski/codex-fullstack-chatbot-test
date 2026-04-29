export const learningStructure = [
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
        id: "docker-reliability",
        title: "Level 2 - Reliability",
        lessons: [
          {
            id: "postgres_container_not_ready",
            title: "Postgres Container Not Ready",
            difficulty: "medium",
          },
          {
            id: "docker_healthcheck_missing",
            title: "Docker Healthcheck Missing",
            difficulty: "medium",
          },
        ],
      },
      {
        id: "docker-debugging",
        title: "Level 3 - Debugging",
        lessons: [
          {
            id: "docker_startup_race_condition",
            title: "Docker Compose Startup Race Condition",
            difficulty: "hard",
          },
        ],
      },
      {
        id: "docker-production",
        title: "Level 4 - Production",
        lessons: [
          {
            id: "docker_production_hardening",
            title: "Docker Production Hardening",
            difficulty: "production",
          },
        ],
      },
    ],
  },
];
