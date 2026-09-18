"""RepoLens AI — AI Domain Models.

Provider-agnostic data models for AI context building and review output.
These models never contain raw file content, secrets, or provider-specific logic.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AIContext:
    """Selected, minimized context sent to the AI provider.

    Contains only structured summaries and metadata.
    Never contains raw file content, credentials, or secrets.
    All repository-derived text is treated as untrusted.
    """

    repository_name: str
    repository_url: str
    total_files: int
    total_size_bytes: int
    language_summary: tuple[tuple[str, int], ...]
    classification_summary: tuple[tuple[str, int], ...]
    evidence_summary: tuple[str, ...]
    findings_summary: tuple[str, ...]
    project_metadata_name: str | None
    project_metadata_version: str | None


@dataclass(frozen=True)
class AIReview:
    """Validated, structured AI interpretation.

    This is explicitly non-deterministic output. It must never be
    injected back into Evidence or Finding as objective fact.
    """

    executive_summary: str
    strengths: tuple[str, ...]
    concerns: tuple[str, ...]
    recommendations: tuple[str, ...]
    overall_assessment: str
    provider_model: str


@dataclass(frozen=True)
class AIReviewResult:
    """Result of an AI review attempt.

    Wraps success or explicit failure so consumers (reports) can
    distinguish between 'AI unavailable' and 'AI succeeded'.
    """

    review: AIReview | None
    error: str | None
    is_successful: bool
