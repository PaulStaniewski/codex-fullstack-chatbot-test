import logging
import time
import uuid
from contextvars import ContextVar
from collections.abc import Callable

from fastapi import Request, Response


REQUEST_ID_HEADER = "X-Request-ID"
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
