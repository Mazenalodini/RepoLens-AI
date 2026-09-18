"""RepoLens AI — HTTP API.

Handles HTTP requests, validation, response serialization,
and delegates to Application services. No direct analyzer implementation.
"""

from repolens.api.app import create_app

__all__ = ["create_app"]
