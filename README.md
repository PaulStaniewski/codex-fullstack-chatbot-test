# Codex Fullstack Chatbot Test

This repository is used to test AI coding agents (Codex) on a realistic fullstack application.

## Goal

Build a production-style AI chatbot application with:

- FastAPI backend
- React frontend
- PostgreSQL database
- JWT authentication
- Streaming chat (SSE)
- Docker Compose

## Purpose

This project is intentionally designed as a benchmark to evaluate:

- backend architecture
- frontend integration
- authentication
- streaming
- persistence
- containerization
- automated tests

## Development approach

The system will be built incrementally using AI coding agents.

Each feature will be implemented as a separate task.

## Backend

The backend lives in `backend/` and exposes a FastAPI API with JWT authentication,
PostgreSQL persistence, SQLAlchemy models, and Alembic migrations.

Run locally:

```bash
cd backend
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Run with Docker Compose:

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.
