"""RepoLens AI — Analysis Result Domain Model.

Aggregates all analysis outputs into a single immutable structure
consumed by the AI Context Builder and Report Engine.
"""

from dataclasses import dataclass

from repolens.domain.ai_models import AIReviewResult
from repolens.domain.analyzer import PipelineResult
from repolens.domain.discovery import RepositorySnapshot
from repolens.domain.finding import FindingsResult


@dataclass(frozen=True)
class AnalysisResult:
    """Complete, immutable analysis result.

    Aggregates the snapshot, pipeline evidence, findings, and optional
    AI review into a single structure that reports consume.
    """

    snapshot: RepositorySnapshot
    pipeline_result: PipelineResult
    findings_result: FindingsResult
    ai_review_result: AIReviewResult | None
    timestamp: str  # ISO 8601
