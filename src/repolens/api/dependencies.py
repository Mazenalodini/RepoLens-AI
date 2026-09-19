"""RepoLens AI — API Dependency Injection.

Provides singleton service instances to FastAPI route handlers via Depends().
"""

import logging
import os
from functools import lru_cache

from repolens.application.analysis_service import AnalysisService
from repolens.domain.ai_provider import AIProvider
from repolens.infrastructure.analysis_store import SQLiteAnalysisStore
from repolens.infrastructure.database import (
    create_db_engine,
    create_session_factory,
    create_tables,
)
from repolens.infrastructure.github_source import GitHubRepositorySource

logger = logging.getLogger(__name__)


def _create_ai_provider() -> AIProvider | None:
    """Create an AI provider based on configuration."""
    provider_type = os.environ.get("REPOLENS_AI_PROVIDER", "").strip().lower()
    google_key = os.environ.get("REPOLENS_AI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    if provider_type:
        if provider_type == "google":
            if not google_key:
                logger.error("REPOLENS_AI_PROVIDER=google but REPOLENS_AI_API_KEY is not set.")
                return None
            return _init_google_provider(google_key)
        elif provider_type == "openrouter":
            if not openrouter_key:
                logger.error("REPOLENS_AI_PROVIDER=openrouter but OPENROUTER_API_KEY is not set.")
                return None
            return _init_openrouter_provider(openrouter_key)
        else:
            logger.error(
                "Invalid REPOLENS_AI_PROVIDER configuration: '%s'. "
                "Must be 'google' or 'openrouter'.",
                provider_type,
            )
            return None

    # Auto-detect
    if google_key:
        logger.info("Auto-detected Google AI Provider.")
        return _init_google_provider(google_key)

    if openrouter_key:
        logger.info("Auto-detected OpenRouter AI Provider.")
        return _init_openrouter_provider(openrouter_key)

    logger.info("No AI provider configured — AI review disabled.")
    return None


def _init_google_provider(api_key: str) -> AIProvider | None:
    try:
        from repolens.infrastructure.google_ai_provider import GoogleAIProvider

        provider = GoogleAIProvider(api_key=api_key)
        logger.info("Activated AI provider: %s", provider.provider_name)
        return provider
    except Exception:
        logger.exception("Failed to create Google AI provider — AI review disabled.")
        return None


def _init_openrouter_provider(api_key: str) -> AIProvider | None:
    try:
        from repolens.infrastructure.openrouter_ai_provider import OpenRouterAIProvider

        provider = OpenRouterAIProvider(api_key=api_key)
        logger.info("Activated AI provider: %s", provider.provider_name)
        return provider
    except Exception:
        logger.exception("Failed to create OpenRouter AI provider — AI review disabled.")
        return None


@lru_cache(maxsize=1)
def get_analysis_service() -> AnalysisService:
    """Create and cache the singleton AnalysisService."""
    engine = create_db_engine()
    create_tables(engine)
    session_factory = create_session_factory(engine)

    store = SQLiteAnalysisStore(session_factory)
    source = GitHubRepositorySource()
    ai_provider = _create_ai_provider()

    return AnalysisService(
        source=source,
        store=store,
        ai_provider=ai_provider,
    )
