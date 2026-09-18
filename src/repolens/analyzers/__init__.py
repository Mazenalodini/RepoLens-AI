"""RepoLens AI — Analyzers.

Each analyzer has a single primary responsibility and produces
structured, independently testable results.
"""

from repolens.analyzers.health import RepositoryHealthAnalyzer

__all__ = ["RepositoryHealthAnalyzer"]
