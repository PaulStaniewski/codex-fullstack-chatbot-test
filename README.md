# Fullstack AI Chatbot Benchmark

A fullstack AI chatbot demo and benchmark project built with FastAPI, React, PostgreSQL, JWT authentication, Server-Sent Events streaming, and Docker Compose.

The repository is intentionally small but production-shaped: it includes auth, persistence, conversation management, streaming AI responses, frontend state restoration, rate limiting, Docker setup, and backend tests.

## Architecture

```text
Browser
  |
  | React + Vite frontend
  | - auth screens
  | - conversation sidebar
  | - SSE chat UI
  v
FastAPI backend
  |
  | JWT auth
  | REST API + /chat-stream SSE
  | SQLAlchemy models
  v
PostgreSQL

FastAPI backend ---> OpenAI Responses API
                 streams text deltas back to browser
```

## Tech Stack

- Frontend: React, Vite, plain CSS
- Backend: FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL
- Auth: JWT bearer tokens
- AI: OpenAI Responses API streaming
- Streaming: Server-Sent Events via `EventSource`
- Containers: Docker Compose
- Tests: pytest, FastAPI TestClient

## Features

- Register and log in with JWT auth
- Persist JWT in `localStorage`
- Create, select, rename, and delete conversations
- Restore last active conversation after refresh
- Send chat messages and stream assistant responses live
- Persist user and assistant messages
- Dark/light theme toggle with saved preference
- Responsive modern chat UI
- Basic in-memory per-user stream rate limiting
- Basic in-memory per-IP failed login rate limiting
- Message length guard for chat requests
- Safe SSE error messages for OpenAI failures

## Project Structure

```text
backend/
  app/
    routes/              FastAPI route modules
    auth.py              JWT/password helpers
    database.py          SQLAlchemy engine/session
    models.py            User, Conversation, Message
    schemas.py           Pydantic schemas
  alembic/               Database migrations
  tests/                 Backend test suite
  Dockerfile
  requirements.txt

frontend/
  src/
    components/          React UI components
    App.jsx              Main app state and API orchestration
    api.js               API helpers
    styles.css           Theme and layout styles
  Dockerfile
  package.json

docker-compose.yml
.env.example
```

## Environment Variables

Copy `.env.example` to `.env` and fill in local values:

```bash
cp .env.example .env
```

| Variable | Purpose | Example |
| --- | --- | --- |
| `APP_ENV` | Runtime environment (`development`, `test`, `production`) | `development` |
| `DATABASE_URL` | Backend database URL for local development | `postgresql+psycopg://chatbot:chatbot@localhost:5432/chatbot` |
| `JWT_SECRET_KEY` | Secret used to sign JWTs (required in all environments) | `dev-only-jwt-secret-change-this` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `60` |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Refresh token lifetime | `10080` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed frontend origins for CORS | `http://localhost:5173,http://127.0.0.1:5173` |
| `OPENAI_API_KEY` | OpenAI API key for real streaming responses | empty in example |
| `OPENAI_MODEL` | Model used by the backend | `gpt-5.4-mini` |
| `POSTGRES_DB` | Docker Postgres database name | `chatbot` |
| `POSTGRES_USER` | Docker Postgres user | `chatbot` |
| `POSTGRES_PASSWORD` | Docker Postgres password | `chatbot` |

Do not commit real secrets. Keep local credentials in `.env`.
In `production`, the backend now fails fast if `JWT_SECRET_KEY` is missing or set to a known insecure default value.
The backend also configures CORS from `CORS_ALLOWED_ORIGINS` and expects explicit origins when credentials are enabled.

## Docker Usage

Start the full stack:

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- PostgreSQL: `localhost:5432`

Stop services:

```bash
docker compose down
```

Remove the database volume:

```bash
docker compose down -v
```

The default Compose stack uses the `dev` Dockerfile targets and keeps hot reload / bind mounts enabled for local development.

Production-style image builds are available without changing the dev workflow:

```bash
docker build --target production -t chatbot-backend:prod ./backend
docker build --target production -t chatbot-frontend:prod ./frontend
```

The backend production target runs Uvicorn without reload as a non-root user. The frontend production target builds static Vite assets and serves them with nginx, including an `/api` proxy to the backend service name for container-network deployments.

## Local Development

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

The Vite dev server proxies `/api/*` requests to the backend. The proxy target defaults to `http://localhost:8000` and can be changed with `VITE_API_PROXY_TARGET`.

## Running Tests

Backend tests:

```bash
cd backend
python -m pytest
```

Frontend production build check:

```bash
cd frontend
npm run build
```

GitHub Actions CI runs both backend tests and the frontend production build on pushes and pull requests.

## API Summary

### Auth

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/register` | Create user account |
| `POST` | `/login` | Return JWT access + refresh tokens |
| `POST` | `/refresh` | Exchange refresh token for a new access token |
| `POST` | `/logout` | Validate current token and return success (stateless logout contract) |

### Health

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Verify the API is alive and can execute a database query |

### Conversations

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/conversations` | List current user's conversations |
| `POST` | `/conversations` | Create conversation |
| `PATCH` | `/conversations/{conversation_id}` | Rename owned conversation |
| `DELETE` | `/conversations/{conversation_id}` | Delete owned conversation and messages |

### Messages

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/messages?conversation_id=...` | List messages for an owned conversation |
| `POST` | `/messages` | Create message directly |

### Chat

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/chat-stream?conversation_id=...&message=...&token=...` | Stream assistant response over SSE |

Most endpoints use `Authorization: Bearer <token>`. The streaming endpoint accepts `token` as a query parameter because browser `EventSource` cannot set custom headers.

## Core Flows

### Auth Flow

1. User registers with email and password.
2. User logs in and receives a JWT access token and refresh token.
3. Frontend stores both tokens in `localStorage`.
4. Protected REST requests send `Authorization: Bearer <access_token>`.
5. If an access token expires, the frontend calls `/refresh` once and retries the original request.
6. Frontend logout clears tokens, selected conversation, and local UI state.
7. `POST /logout` validates the token and returns success, but does not revoke JWTs yet because auth is currently stateless access-token-only.

### SSE Streaming Flow

1. User submits a message in the selected conversation.
2. Frontend opens `EventSource` to `/chat-stream`.
3. Backend authenticates the query token and validates ownership.
4. Backend persists the user message.
5. Backend sends the conversation context plus new message to the OpenAI Responses API with streaming enabled.
6. Text deltas are emitted to the browser as SSE `data:` chunks.
7. When streaming completes, backend persists the assistant message.
8. If OpenAI fails, backend emits a safe SSE error and does not persist an assistant message.

### Conversation Persistence

The frontend stores the active `conversation_id` in `localStorage`. On reload, it fetches conversations and restores the saved conversation if it still exists. If it was deleted or no longer belongs to the user, the saved id is cleared and the UI safely shows an empty chat state.

### Rate Limiting

`/chat-stream` has a simple in-memory per-user rate limit. It is designed for this benchmark and helps prevent accidental abuse during local demos. It is not distributed across multiple backend instances and should be replaced with Redis or another shared store for production deployments.

The endpoint also rejects messages over 2000 characters before persistence or OpenAI calls.

`/login` also has a simple in-memory per-IP failed-attempt rate limit. It protects against repeated brute-force attempts during local development/demo usage. Like chat rate limiting, this limiter is per-process and not shared across replicas, so it should be replaced with a shared store (for example Redis) in production multi-instance deployments.

## Known Limitations

- In-memory rate limiting resets when the backend restarts.
- Rate limiting is not shared across multiple backend replicas.
- `EventSource` sends the JWT in the query string because custom headers are not supported.
- The frontend uses simple `prompt()` / `confirm()` dialogs for conversation rename/delete.
- No refresh token flow is implemented.
- No frontend test suite is included.
- OpenAI errors are intentionally hidden from the user behind safe generic messages.

## Next Improvements

- Replace in-memory rate limiting with Redis.
- Add refresh tokens and token rotation.
- Add frontend tests with Playwright or Testing Library.
- Add markdown rendering and code block formatting.
- Add model selection and system prompt configuration.
