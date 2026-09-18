"""RepoLens AI — Analysis Service.

Full pipeline orchestrator: validates URL, acquires repository, discovers,
analyzes, generates findings, optionally invokes AI review, generates reports,
and persists everything. Owns workspace lifecycle and concurrency control.
"""

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from threading import Semaphore

from repolens.analyzers import (
    CodeQualityAnalyzer,
    RepositoryHealthAnalyzer,
    TestingIntelligenceAnalyzer,
)
from repolens.application.ai_advisor import AIAdvisor
from repolens.application.ai_context_builder import AIContextBuilder
from repolens.application.finding_rules import get_default_rules
from repolens.application.findings_engine import FindingRuleRegistry, FindingsEngine
from repolens.application.pipeline import AnalyzerPipeline, AnalyzerRegistry
from repolens.domain.ai_models import AIReviewResult
from repolens.domain.ai_provider import AIProvider
from repolens.domain.analysis import AnalysisResult
from repolens.domain.exceptions import (
    ConcurrencyLimitError,
    RepoLensError,
    RepositorySizeError,
)
from repolens.domain.persistence import AnalysisRecord, AnalysisStore
from repolens.domain.report import ReportArtifact
from repolens.domain.repository import RepositorySource
from repolens.infrastructure.source_reader import WorkspaceSourceReader
from repolens.reports import (
    HTMLReportGenerator,
    JSONReportGenerator,
    MarkdownReportGenerator,
)

logger = logging.getLogger(__name__)

_DEFAULT_MAX_CONCURRENT = 2
_DEFAULT_MAX_REPO_SIZE = 100_000_000  # 100 MB


class AnalysisService:
    """Orchestrates the complete analysis pipeline.

    Coordinates: URL validation → acquisition → discovery → analysis →
    findings → AI review → report generation → persistence.

    Thread-safe via semaphore-bounded concurrency.
    """

    def __init__(
        self,
        source: RepositorySource,
        store: AnalysisStore,
        ai_provider: AIProvider | None = None,
        *,
        max_concurrent: int | None = None,
        max_repo_size_bytes: int | None = None,
    ) -> None:
        self._source = source
        self._store = store
        self._ai_provider = ai_provider

        concurrent = (
            max_concurrent
            if max_concurrent is not None
            else int(
                os.environ.get(
                    "REPOLENS_MAX_CONCURRENT_ANALYSES",
                    str(_DEFAULT_MAX_CONCURRENT),
                )
            )
        )
        self._semaphore = Semaphore(concurrent)
        self._max_repo_size = max_repo_size_bytes or _DEFAULT_MAX_REPO_SIZE

    def analyze(
        self,
        repository_url: str,
        *,
        include_ai_review: bool = True,
        report_format: str = "html",
    ) -> str:
        """Run the full analysis pipeline and persist results.

        Args:
            repository_url: GitHub repository URL.
            include_ai_review: Whether to include AI review.
            report_format: Primary report format ("html", "json", "markdown").

        Returns:
            Analysis ID (UUID string).

        Raises:
            ConcurrencyLimitError: If all analysis slots are occupied.
            ValidationError: If the URL is invalid.
            AcquisitionError: If repository cloning fails.
            RepositorySizeError: If the repository exceeds the size limit.
        """
        analysis_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        # Try to acquire a concurrency slot (non-blocking)
        if not self._semaphore.acquire(blocking=False):
            raise ConcurrencyLimitError(
                "Maximum concurrent analyses reached. Please try again later."
            )

        try:
            return self._run_analysis(
                analysis_id=analysis_id,
                repository_url=repository_url,
                include_ai_review=include_ai_review,
                report_format=report_format,
                created_at=now,
            )
        finally:
            self._semaphore.release()

    def _run_analysis(
        self,
        *,
        analysis_id: str,
        repository_url: str,
        include_ai_review: bool,
        report_format: str,
        created_at: str,
    ) -> str:
        """Execute the analysis pipeline within a concurrency slot."""
        # Import here to avoid circular; parse is a standalone function
        from repolens.infrastructure.github_source import parse_github_url

        # Step 1: Validate URL
        info = parse_github_url(repository_url)

        # Create initial record
        record = AnalysisRecord(
            id=analysis_id,
            repository_owner=info.owner,
            repository_name=info.name,
            repository_url=info.url,
            status="running",
            created_at=created_at,
        )
        self._store.save(record)

        logger.info(
            "Starting analysis %s for %s",
            analysis_id,
            info.full_name,
        )

        workspace = None
        try:
            # Step 2: Acquire repository
            workspace = self._source.acquire(repository_url)

            # Step 3: Discover repository
            from repolens.application.discovery import RepositoryDiscoveryService

            discovery = RepositoryDiscoveryService()
            snapshot = discovery.discover(workspace)

            # Step 4: Check repository size limit
            if snapshot.total_size_bytes > self._max_repo_size:
                raise RepositorySizeError(
                    f"Repository size ({snapshot.total_size_bytes:,} bytes) "
                    f"exceeds limit ({self._max_repo_size:,} bytes)."
                )

            # Step 5: Build and run analyzer pipeline
            source_reader = WorkspaceSourceReader(workspace, snapshot)

            analyzer_registry = AnalyzerRegistry()
            analyzer_registry.register(RepositoryHealthAnalyzer())
            analyzer_registry.register(CodeQualityAnalyzer(source_reader=source_reader))
            analyzer_registry.register(
                TestingIntelligenceAnalyzer(source_reader=source_reader)
            )

            pipeline = AnalyzerPipeline(analyzer_registry)
            pipeline_result = pipeline.run(snapshot)

            # Step 6: Run findings engine
            rule_registry = FindingRuleRegistry()
            for rule in get_default_rules():
                rule_registry.register(rule)

            findings_engine = FindingsEngine(rule_registry)
            findings_result = findings_engine.evaluate(pipeline_result.evidence)

            # Step 7: AI review (optional)
            ai_review_result: AIReviewResult | None = None
            if include_ai_review and self._ai_provider is not None:
                context_builder = AIContextBuilder()
                context = context_builder.build(
                    snapshot, pipeline_result, findings_result
                )
                advisor = AIAdvisor(self._ai_provider)
                ai_review_result = advisor.review(context)

            # Step 8: Assemble AnalysisResult
            analysis_result = AnalysisResult(
                snapshot=snapshot,
                pipeline_result=pipeline_result,
                findings_result=findings_result,
                ai_review_result=ai_review_result,
                timestamp=created_at,
            )

            # Step 9: Generate reports
            reports: dict[str, ReportArtifact] = {}
            for generator in (
                HTMLReportGenerator(),
                JSONReportGenerator(),
                MarkdownReportGenerator(),
            ):
                try:
                    artifact = generator.generate(analysis_result)
                    reports[generator.format_name] = artifact
                except Exception:
                    logger.exception(
                        "Report generator '%s' failed.",
                        generator.format_name,
                    )

            # Step 10: Update record with results
            record.status = "completed"
            record.completed_at = datetime.now(UTC).isoformat()
            record.total_files = snapshot.total_files
            record.total_directories = snapshot.total_directories
            record.total_size_bytes = snapshot.total_size_bytes
            record.total_evidence = pipeline_result.total_evidence
            record.total_findings = findings_result.total_findings

            # Serialize findings
            record.findings_json = json.dumps(
                [
                    {
                        "rule_id": f.rule_id,
                        "finding_id": f.finding_id,
                        "category": f.category.value,
                        "severity": f.severity.value,
                        "title": f.title,
                        "description": f.description,
                        "source_analyzer": f.source_analyzer,
                        "recommendation": f.recommendation,
                    }
                    for f in findings_result.findings
                ],
                ensure_ascii=False,
            )

            # Serialize AI review
            if ai_review_result and ai_review_result.is_successful and ai_review_result.review:
                record.ai_review_json = json.dumps(
                    {
                        "executive_summary": ai_review_result.review.executive_summary,
                        "strengths": list(ai_review_result.review.strengths),
                        "concerns": list(ai_review_result.review.concerns),
                        "recommendations": list(ai_review_result.review.recommendations),
                        "overall_assessment": ai_review_result.review.overall_assessment,
                        "provider_model": ai_review_result.review.provider_model,
                    },
                    ensure_ascii=False,
                )

            # Store reports
            if "html" in reports:
                record.report_html = reports["html"].content
            if "json" in reports:
                record.report_json_content = reports["json"].content
            if "markdown" in reports:
                record.report_markdown = reports["markdown"].content

            # Serialize language summary
            record.language_summary_json = json.dumps(
                [{"language": lang, "count": count} for lang, count in snapshot.language_counts],
                ensure_ascii=False,
            )

            # Pipeline summary
            record.pipeline_summary_json = json.dumps(
                [
                    {
                        "analyzer_id": aid,
                        "status": result.status.value,
                        "evidence_count": len(result.evidence),
                        "errors": list(result.errors),
                    }
                    for aid, result in pipeline_result.results
                ],
                ensure_ascii=False,
            )

            self._store.update(record)

            logger.info(
                "Analysis %s completed: %d evidence, %d findings",
                analysis_id,
                pipeline_result.total_evidence,
                findings_result.total_findings,
            )

            return analysis_id

        except RepoLensError:
            # Known domain errors — update record and re-raise
            record.status = "failed"
            record.completed_at = datetime.now(UTC).isoformat()
            record.error_message = str(
                # Re-fetch the current exception
                __import__("sys").exc_info()[1]
            )
            try:
                self._store.update(record)
            except Exception:
                logger.exception("Failed to update error status for %s", analysis_id)
            raise

        except Exception as exc:
            # Unexpected errors
            record.status = "failed"
            record.completed_at = datetime.now(UTC).isoformat()
            record.error_message = f"Unexpected error: {exc}"
            try:
                self._store.update(record)
            except Exception:
                logger.exception("Failed to update error status for %s", analysis_id)
            raise

        finally:
            # Step 11: Guaranteed workspace cleanup
            if workspace is not None:
                try:
                    workspace.cleanup()
                except Exception:
                    logger.exception(
                        "Workspace cleanup failed for analysis %s",
                        analysis_id,
                    )

    def get_analysis(self, analysis_id: str) -> AnalysisRecord | None:
        """Retrieve a stored analysis record."""
        return self._store.get(analysis_id)

    def list_analyses(self, limit: int = 20) -> list[AnalysisRecord]:
        """List recent analyses."""
        return self._store.list_recent(limit=limit)
