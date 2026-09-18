"""RepoLens AI — Analyzer Pipeline Orchestration.

Manages the registration and sequential execution of analyzers, ensuring
failure isolation and deterministic evidence aggregation.
"""

import logging

from repolens.domain.analyzer import (
    Analyzer,
    AnalyzerResult,
    AnalyzerStatus,
    PipelineResult,
)
from repolens.domain.discovery import RepositorySnapshot
from repolens.domain.exceptions import PipelineError

logger = logging.getLogger(__name__)


class AnalyzerRegistry:
    """Explicit registry for analyzers."""

    def __init__(self) -> None:
        self._analyzers: list[Analyzer] = []
        self._ids: set[str] = set()

    def register(self, analyzer: Analyzer) -> None:
        """Register an analyzer. Raises PipelineError on duplicate ID."""
        if analyzer.analyzer_id in self._ids:
            raise PipelineError(f"Analyzer with ID '{analyzer.analyzer_id}' is already registered.")

        self._analyzers.append(analyzer)
        self._ids.add(analyzer.analyzer_id)

    @property
    def analyzers(self) -> tuple[Analyzer, ...]:
        """Return the registered analyzers in insertion order."""
        return tuple(self._analyzers)


class AnalyzerPipeline:
    """Orchestrates sequential analyzer execution and failure isolation."""

    def __init__(self, registry: AnalyzerRegistry) -> None:
        self.registry = registry

    def run(self, snapshot: RepositorySnapshot) -> PipelineResult:
        """Execute all registered analyzers sequentially against the snapshot.

        Provides failure isolation: if an analyzer raises an exception, it is
        caught, logged, and converted to an AnalyzerResult with ERROR status,
        allowing the pipeline to continue.
        """
        results: list[tuple[str, AnalyzerResult]] = []
        is_successful = True

        for analyzer in self.registry.analyzers:
            try:
                logger.info(f"Running analyzer: {analyzer.analyzer_id}")
                result = analyzer.analyze(snapshot)

                if result.status == AnalyzerStatus.ERROR:
                    is_successful = False

                results.append((analyzer.analyzer_id, result))

            except Exception as e:
                # Catch Exception (not BaseException) to isolate failures,
                # while allowing SystemExit/KeyboardInterrupt to bubble up.
                logger.exception(
                    f"Analyzer {analyzer.analyzer_id} failed with an unexpected error."
                )
                is_successful = False

                # Convert the exception to an explicit ERROR result
                error_msg = f"{type(e).__name__}: {e!s}"
                error_result = AnalyzerResult(
                    status=AnalyzerStatus.ERROR, evidence=(), errors=(error_msg,)
                )
                results.append((analyzer.analyzer_id, error_result))

        return PipelineResult(results=tuple(results), is_successful=is_successful)
