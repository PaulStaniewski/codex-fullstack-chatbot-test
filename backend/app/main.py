import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.observability import request_id_middleware
from app.routes import (
    auth_routes,
    chat_routes,
    conversation_routes,
    lesson_routes,
    message_routes,
    progress_routes,
)


app = FastAPI(title="Fullstack Chatbot API")
app.middleware("http")(request_id_middleware)


def _get_allowed_origins() -> list[str]:
    raw_origins = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(conversation_routes.router)
app.include_router(lesson_routes.router)
app.include_router(message_routes.router)
app.include_router(progress_routes.router)


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
