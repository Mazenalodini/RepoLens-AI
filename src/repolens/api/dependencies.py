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
    """Create an AI provider if an API key is configured."""
    api_key = os.environ.get("REPOLENS_AI_API_KEY")
    if not api_key:
        logger.info("REPOLENS_AI_API_KEY not set — AI review disabled.")
        return None

    try:
        from repolens.infrastructure.google_ai_provider import GoogleAIProvider

        return GoogleAIProvider(api_key=api_key)
    except Exception:
        logger.exception("Failed to create AI provider — AI review disabled.")
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
