import os
import logging
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

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expires_at, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expires_at, "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


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
