"""RepoLens AI — API Middleware.

Request-level controls: logging, timeout, and request-size enforcement.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

_MAX_REQUEST_BODY_BYTES = 4096  # 4 KB — analyses only need a URL


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request start/end with timing."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start = time.monotonic()
        logger.info(
            "→ %s %s",
            request.method,
            request.url.path,
        )

        response = await call_next(request)

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "← %s %s %d (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects request bodies that exceed the configured limit."""

    def __init__(self, app, max_bytes: int = _MAX_REQUEST_BODY_BYTES) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self._max_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request body too large",
                    "detail": f"Maximum body size is {self._max_bytes} bytes.",
                },
            )
        return await call_next(request)
