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
    refresh_token, refresh_session = auth.create_refresh_session(db, user.id)
    db.commit()
    return schemas.Token(
        access_token=auth.create_access_token(str(user.id), session_id=refresh_session.id),
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=schemas.Token)
def refresh_access_token(refresh_in: schemas.RefreshRequest, db: Session = Depends(get_db)):
    access_token, refresh_token, _refresh_session = auth.rotate_refresh_session(
        db,
        refresh_in.refresh_token,
    )
    db.commit()
    return schemas.Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/stream-token", response_model=schemas.StreamToken)
def issue_stream_token(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    stream_token, token_record = auth.create_stream_token(db, current_user.id)
    db.commit()
    return schemas.StreamToken(stream_token=stream_token, expires_at=token_record.expires_at)


@router.get("/me", response_model=schemas.UserRead)
def read_current_user(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@router.post("/logout")
def logout_user(
    token: str = Depends(auth.oauth2_scheme),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    session_id = auth.get_session_id_from_access_token(token)
    auth.revoke_refresh_session(db, session_id, current_user.id)
    db.commit()
    return {"success": True}
