import os
import time
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db
from app.observability import get_request_id


router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)
LOGIN_RATE_LIMIT_ERROR = "Too many login attempts. Please try again later."
LOGIN_FAILED_ATTEMPT_LIMIT = int(os.getenv("LOGIN_FAILED_ATTEMPT_LIMIT", "5"))
LOGIN_FAILED_ATTEMPT_WINDOW_SECONDS = int(os.getenv("LOGIN_FAILED_ATTEMPT_WINDOW_SECONDS", "300"))
_failed_login_buckets: dict[str, list[float]] = {}


def _resolve_client_ip(x_forwarded_for: str | None, client_host: str | None) -> str:
    if x_forwarded_for:
        forwarded_ip = x_forwarded_for.split(",")[0].strip()
        if forwarded_ip:
            return forwarded_ip
    if client_host:
        return client_host
    return "unknown"


def _get_recent_failed_attempts(ip: str) -> list[float]:
    now = time.monotonic()
    window_start = now - LOGIN_FAILED_ATTEMPT_WINDOW_SECONDS
    attempts = [
        timestamp
        for timestamp in _failed_login_buckets.get(ip, [])
        if timestamp > window_start
    ]
    _failed_login_buckets[ip] = attempts
    return attempts


def _is_login_rate_limited(ip: str) -> bool:
    attempts = _get_recent_failed_attempts(ip)
    return len(attempts) >= LOGIN_FAILED_ATTEMPT_LIMIT


def _record_failed_login_attempt(ip: str) -> None:
    attempts = _get_recent_failed_attempts(ip)
    attempts.append(time.monotonic())
    _failed_login_buckets[ip] = attempts


def _clear_failed_login_attempts(ip: str) -> None:
    _failed_login_buckets.pop(ip, None)


@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = models.User(
        email=user_in.email,
        hashed_password=auth.hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login_user(
    login_in: schemas.LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = _resolve_client_ip(
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
    )

    if _is_login_rate_limited(client_ip):
        logger.info(
            "auth.failure",
            extra={"request_id": get_request_id(), "reason": "login_rate_limited"},
        )
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=LOGIN_RATE_LIMIT_ERROR)

    user = auth.authenticate_user(db, login_in.email, login_in.password)
    if not user:
        _record_failed_login_attempt(client_ip)
        logger.info(
            "auth.failure",
            extra={"request_id": get_request_id(), "reason": "invalid_credentials"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    _clear_failed_login_attempts(client_ip)
    return schemas.Token(
        access_token=auth.create_access_token(str(user.id)),
        refresh_token=auth.create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=schemas.Token)
def refresh_access_token(refresh_in: schemas.RefreshRequest):
    user_id = auth.get_subject_from_token(refresh_in.refresh_token, expected_type="refresh")
    return schemas.Token(access_token=auth.create_access_token(user_id))


@router.get("/me", response_model=schemas.UserRead)
def read_current_user(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@router.post("/logout")
def logout_user(current_user: models.User = Depends(auth.get_current_user)):
    # Access-token-only JWT auth is currently stateless.
    # This endpoint validates the token and provides a stable logout contract
    # for auditability and future token/session revocation support.
    return {"success": True}
