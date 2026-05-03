import os
import logging
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Mapping

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.observability import get_request_id


DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
DEFAULT_REFRESH_TOKEN_EXPIRE_MINUTES = 10080
DEFAULT_STREAM_TOKEN_EXPIRE_SECONDS = 60
PRODUCTION_ENV_NAMES = {"prod", "production"}
INSECURE_JWT_SECRET_VALUES = {
    "change-me-in-production",
    "dev-secret-key",
    "test-secret-key",
    "development-secret",
    "dev-only-jwt-secret-change-this",
}
logger = logging.getLogger(__name__)


def _resolve_auth_settings(environ: Mapping[str, str] | None = None) -> tuple[str, str, int, int]:
    env = environ or os.environ
    app_env = env.get("APP_ENV", "development").strip().lower()
    secret_key = (env.get("JWT_SECRET_KEY") or "").strip()
    algorithm = (env.get("JWT_ALGORITHM") or DEFAULT_JWT_ALGORITHM).strip()
    expire_minutes = int(
        (env.get("ACCESS_TOKEN_EXPIRE_MINUTES") or str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)).strip()
    )
    refresh_expire_minutes = int(
        (env.get("REFRESH_TOKEN_EXPIRE_MINUTES") or str(DEFAULT_REFRESH_TOKEN_EXPIRE_MINUTES)).strip()
    )

    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY must be set in the environment.")

    if app_env in PRODUCTION_ENV_NAMES and secret_key in INSECURE_JWT_SECRET_VALUES:
        raise RuntimeError("JWT_SECRET_KEY is unsafe for production APP_ENV.")

    return secret_key, algorithm, expire_minutes, refresh_expire_minutes


SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES = _resolve_auth_settings()
STREAM_TOKEN_EXPIRE_SECONDS = int(
    os.getenv("STREAM_TOKEN_EXPIRE_SECONDS", str(DEFAULT_STREAM_TOKEN_EXPIRE_SECONDS))
)

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, session_id: str | None = None) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expires_at, "type": "access"}
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str, session_id: str | None = None) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expires_at, "type": "refresh"}
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def create_refresh_session(db: Session, user_id: int) -> tuple[str, models.RefreshSession]:
    session_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_refresh_token(str(user_id), session_id=session_id)
    refresh_session = models.RefreshSession(
        id=session_id,
        user_id=user_id,
        token_hash=hash_token(refresh_token),
        expires_at=expires_at,
    )
    db.add(refresh_session)
    db.flush()
    return refresh_token, refresh_session


def _refresh_credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_refresh_session_from_token(db: Session, refresh_token: str) -> models.RefreshSession:
    credentials_error = _refresh_credentials_error()
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        token_type = payload.get("type")
        session_id = payload.get("sid")
        if subject is None or token_type != "refresh" or not session_id:
            raise credentials_error
        user_id = int(subject)
    except (JWTError, ValueError):
        logger.info(
            "auth.failure",
            extra={"request_id": get_request_id(), "reason": "invalid_refresh_token"},
        )
        raise credentials_error from None

    refresh_session = db.get(models.RefreshSession, str(session_id))
    now = datetime.now(timezone.utc)
    if (
        refresh_session is None
        or refresh_session.user_id != user_id
        or refresh_session.token_hash != hash_token(refresh_token)
        or refresh_session.revoked_at is not None
        or _normalize_datetime(refresh_session.expires_at) <= now
    ):
        logger.info(
            "auth.failure",
            extra={
                "request_id": get_request_id(),
                "reason": "refresh_session_invalid",
                "user_id": user_id,
            },
        )
        raise credentials_error

    return refresh_session


def rotate_refresh_session(
    db: Session,
    refresh_token: str,
) -> tuple[str, str, models.RefreshSession]:
    refresh_session = get_refresh_session_from_token(db, refresh_token)
    now = datetime.now(timezone.utc)
    refresh_session.revoked_at = now
    next_refresh_token, next_session = create_refresh_session(db, refresh_session.user_id)
    refresh_session.replaced_by_session_id = next_session.id
    access_token = create_access_token(str(refresh_session.user_id), session_id=next_session.id)
    db.flush()
    return access_token, next_refresh_token, next_session


def revoke_refresh_session(db: Session, session_id: str | None, user_id: int) -> int:
    now = datetime.now(timezone.utc)
    query = db.query(models.RefreshSession).filter(
        models.RefreshSession.user_id == user_id,
        models.RefreshSession.revoked_at.is_(None),
    )
    if session_id:
        query = query.filter(models.RefreshSession.id == session_id)

    revoked_count = 0
    for refresh_session in query.all():
        refresh_session.revoked_at = now
        revoked_count += 1
    db.flush()
    return revoked_count


def create_stream_token(db: Session, user_id: int) -> tuple[str, models.StreamToken]:
    token = secrets.token_urlsafe(32)
    stream_token = models.StreamToken(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=STREAM_TOKEN_EXPIRE_SECONDS),
    )
    db.add(stream_token)
    db.flush()
    return token, stream_token


def consume_stream_token(db: Session, token: str) -> models.User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate stream token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    stream_token = (
        db.query(models.StreamToken)
        .filter(models.StreamToken.token_hash == hash_token(token))
        .first()
    )
    now = datetime.now(timezone.utc)
    if (
        stream_token is None
        or stream_token.used_at is not None
        or _normalize_datetime(stream_token.expires_at) <= now
    ):
        logger.info(
            "auth.failure",
            extra={"request_id": get_request_id(), "reason": "stream_token_invalid"},
        )
        raise credentials_error

    user = db.get(models.User, stream_token.user_id)
    if user is None:
        logger.info(
            "auth.failure",
            extra={
                "request_id": get_request_id(),
                "reason": "stream_token_user_not_found",
                "user_id": stream_token.user_id,
            },
        )
        raise credentials_error

    stream_token.used_at = now
    db.flush()
    return user


def get_user_from_sse_token(db: Session, token: str) -> models.User:
    try:
        user = consume_stream_token(db, token)
        db.commit()
        return user
    except HTTPException:
        db.rollback()
        return get_user_from_token(db, token)


def get_session_id_from_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") != "access":
        return None
    session_id = payload.get("sid")
    return str(session_id) if session_id else None


def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def get_subject_from_token(token: str, expected_type: str = "access") -> str:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        token_type = payload.get("type")
        if subject is None or token_type != expected_type:
            logger.info(
                "auth.failure",
                extra={
                    "request_id": get_request_id(),
                    "reason": "invalid_token_subject_or_type",
                    "expected_token_type": expected_type,
                },
            )
            raise credentials_error
    except JWTError:
        logger.info(
            "auth.failure",
            extra={
                "request_id": get_request_id(),
                "reason": "jwt_decode_failed",
                "expected_token_type": expected_type,
            },
        )
        raise credentials_error from None
    return str(subject)


def get_user_from_token(db: Session, token: str) -> models.User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = int(get_subject_from_token(token, expected_type="access"))
    except ValueError:
        logger.info(
            "auth.failure",
            extra={"request_id": get_request_id(), "reason": "non_integer_subject"},
        )
        raise credentials_error from None

    user = db.get(models.User, user_id)
    if user is None:
        logger.info(
            "auth.failure",
            extra={"request_id": get_request_id(), "reason": "user_not_found", "user_id": user_id},
        )
        raise credentials_error
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    return get_user_from_token(db, token)
