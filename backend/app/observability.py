import logging
import os
import time
import uuid
from contextvars import ContextVar
from collections.abc import Callable

from fastapi import Request, Response


REQUEST_ID_HEADER = "X-Request-ID"
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    ),
}
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger(__name__)


def get_request_id() -> str | None:
    return _request_id.get()


def set_request_id(request_id: str | None):
    return _request_id.set(request_id)


def reset_request_id(token) -> None:
    _request_id.reset(token)


def resolve_request_id(request: Request) -> str:
    incoming_request_id = request.headers.get(REQUEST_ID_HEADER, "").strip()
    return incoming_request_id or str(uuid.uuid4())


def _split_env_origins(value: str | None) -> list[str]:
    if not value:
        return []
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def build_content_security_policy() -> str:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    is_production = app_env in {"prod", "production"}

    connect_sources = ["'self'"]
    if not is_production:
        connect_sources.extend(
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "ws://localhost:5173",
                "ws://127.0.0.1:5173",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ]
        )
        connect_sources.extend(_split_env_origins(os.getenv("CORS_ALLOWED_ORIGINS")))

    directives = {
        "default-src": ["'self'"],
        "base-uri": ["'self'"],
        "object-src": ["'none'"],
        "frame-ancestors": ["'none'"],
        "script-src": ["'self'"],
        "style-src": ["'self'"],
        "img-src": ["'self'", "data:", "blob:"],
        "font-src": ["'self'", "data:"],
        "connect-src": sorted(set(connect_sources)),
        "form-action": ["'self'"],
    }
    if is_production:
        directives["upgrade-insecure-requests"] = []

    return "; ".join(
        directive if not values else f"{directive} {' '.join(values)}"
        for directive, values in directives.items()
    )


def apply_security_headers(response: Response) -> None:
    response.headers["Content-Security-Policy"] = build_content_security_policy()
    for header_name, header_value in SECURITY_HEADERS.items():
        response.headers[header_name] = header_value


async def security_headers_middleware(request: Request, call_next: Callable) -> Response:
    response = await call_next(request)
    apply_security_headers(response)
    return response


async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    request_id = resolve_request_id(request)
    request.state.request_id = request_id
    token = set_request_id(request_id)
    started_at = time.perf_counter()

    logger.info(
        "request.start",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        },
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "request.error",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        reset_request_id(token)
        raise

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers[REQUEST_ID_HEADER] = request_id
    logger.info(
        "request.end",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    reset_request_id(token)
    return response
