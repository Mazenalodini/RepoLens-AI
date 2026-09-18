"""RepoLens AI — AI Context Builder.

Builds a minimized AIContext from structured analysis data.
Never includes raw file content, credentials, or secrets.
All repository-derived text is treated as untrusted input.
"""

import logging

from repolens.domain.ai_models import AIContext
from repolens.domain.analyzer import PipelineResult
from repolens.domain.discovery import RepositorySnapshot
from repolens.domain.evidence import MeasuredMetric, ObservedFact
from repolens.domain.finding import FindingsResult

logger = logging.getLogger(__name__)

# Maximum number of evidence/finding summaries to include in context
# to prevent prompt overflow.
_MAX_EVIDENCE_ITEMS = 50
_MAX_FINDING_ITEMS = 50


class AIContextBuilder:
    """Builds minimized AI context from analysis data.

    Context minimization rules:
    - No raw file content
    - No secrets or credential-like data
    - Only structured metadata and human-readable summaries
    - Evidence and findings capped at configured limits
    - Deterministic output for identical inputs
    """

    def __init__(
        self,
        *,
        max_evidence_items: int = _MAX_EVIDENCE_ITEMS,
        max_finding_items: int = _MAX_FINDING_ITEMS,
    ) -> None:
        self._max_evidence = max_evidence_items
        self._max_findings = max_finding_items

    def build(
        self,
        snapshot: RepositorySnapshot,
        pipeline_result: PipelineResult,
        findings_result: FindingsResult,
    ) -> AIContext:
        """Build a minimized AIContext from analysis data.

        Args:
            snapshot: Repository structure snapshot.
            pipeline_result: Pipeline evidence.
            findings_result: Findings from the findings engine.

        Returns:
            Minimized AIContext safe for AI provider consumption.
        """
        evidence_summary = self._summarize_evidence(pipeline_result)
        findings_summary = self._summarize_findings(findings_result)

        classification_summary = tuple(
            (cls.value, count)
            for cls, count in snapshot.classification_counts
        )

        return AIContext(
            repository_name=snapshot.repository_info.full_name,
            repository_url=snapshot.repository_info.url,
            total_files=snapshot.total_files,
            total_size_bytes=snapshot.total_size_bytes,
            language_summary=snapshot.language_counts,
            classification_summary=classification_summary,
            evidence_summary=evidence_summary,
            findings_summary=findings_summary,
            project_metadata_name=(
                snapshot.project_metadata.name
                if snapshot.project_metadata
                else None
            ),
            project_metadata_version=(
                snapshot.project_metadata.version
                if snapshot.project_metadata
                else None
            ),
        )

    def _summarize_evidence(
        self,
        pipeline_result: PipelineResult,
    ) -> tuple[str, ...]:
        """Produce human-readable evidence summaries.

        Evidence is capped at _max_evidence items.
        """
        summaries: list[str] = []
        for item in pipeline_result.evidence:
            if len(summaries) >= self._max_evidence:
                break
            if isinstance(item, ObservedFact):
                summaries.append(
                    f"[{item.analyzer_id}] {item.description}"
                )
            elif isinstance(item, MeasuredMetric):
                summaries.append(
                    f"[{item.analyzer_id}] {item.name} = {item.value}"
                )
        return tuple(summaries)

    def _summarize_findings(
        self,
        findings_result: FindingsResult,
    ) -> tuple[str, ...]:
        """Produce human-readable finding summaries.

        Findings are capped at _max_findings items.
        """
        summaries: list[str] = []
        for finding in findings_result.findings:
            if len(summaries) >= self._max_findings:
                break
            summaries.append(
                f"[{finding.severity.value.upper()}] "
                f"{finding.title}: {finding.description}"
            )
        return tuple(summaries)
