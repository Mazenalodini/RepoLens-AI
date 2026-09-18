"""RepoLens AI — FastAPI Application Factory.

Creates and configures the FastAPI application with all routes,
middleware, and exception handlers.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from repolens.api.dashboard import dashboard_router
from repolens.api.errors import repolens_error_handler, unexpected_error_handler
from repolens.api.middleware import RequestLoggingMiddleware, RequestSizeLimitMiddleware
from repolens.api.routes import router as api_router
from repolens.domain.exceptions import RepoLensError

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # --- Startup logging ---
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        logger.info("RepoLens AI API starting up")
        yield

    app = FastAPI(
        title="RepoLens AI",
        description="AI-Powered GitHub Repository Intelligence & Engineering Health Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # --- Middleware (order matters: last added = first executed) ---
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # --- Exception handlers ---
    app.add_exception_handler(RepoLensError, repolens_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)

    # --- Routers ---
    app.include_router(api_router)
    app.include_router(dashboard_router)

    return app
