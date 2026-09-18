"""RepoLens AI — API Error Handling.

Maps domain exceptions to HTTP status codes and error responses.
Registered as FastAPI exception handlers at the application boundary.
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from repolens.domain.exceptions import (
    AcquisitionError,
    AcquisitionTimeoutError,
    ConcurrencyLimitError,
    PipelineError,
    RepoLensError,
    ReportError,
    RepositoryNotFoundError,
    RepositorySizeError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Domain exception → (HTTP status code, user-facing message)
_EXCEPTION_MAP: dict[type[RepoLensError], tuple[int, str]] = {
    ValidationError: (422, "Invalid input"),
    RepositoryNotFoundError: (404, "Repository not found"),
    AcquisitionTimeoutError: (504, "Repository acquisition timed out"),
    AcquisitionError: (502, "Repository acquisition failed"),
    RepositorySizeError: (422, "Repository exceeds size limit"),
    ConcurrencyLimitError: (429, "Too many concurrent analyses"),
    PipelineError: (500, "Analysis pipeline error"),
    ReportError: (500, "Report generation failed"),
}


async def repolens_error_handler(
    request: Request,
    exc: RepoLensError,
) -> JSONResponse:
    """Handle known RepoLens domain exceptions."""
    # Walk the MRO to find the most specific mapping
    for exc_type in type(exc).__mro__:
        if exc_type in _EXCEPTION_MAP:
            status_code, message = _EXCEPTION_MAP[exc_type]
            break
    else:
        status_code, message = 500, "Internal error"

    # Log server errors at ERROR level, client errors at WARNING
    if status_code >= 500:
        logger.error(
            "Server error [%d] for %s %s: %s",
            status_code,
            request.method,
            request.url.path,
            exc,
        )
    else:
        logger.warning(
            "Client error [%d] for %s %s: %s",
            status_code,
            request.method,
            request.url.path,
            exc,
        )

    return JSONResponse(
        status_code=status_code,
        content={"error": message, "detail": str(exc)},
    )


async def unexpected_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected, untyped exceptions."""
    logger.exception(
        "Unexpected error for %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": None,
        },
    )
