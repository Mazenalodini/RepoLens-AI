"""RepoLens AI — Persistence Domain Models.

Defines the AnalysisRecord (serializable analysis snapshot) and the
AnalysisStore protocol for persistence abstraction. Concrete implementations
belong in Infrastructure.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class AnalysisRecord:
    """Persistent representation of a completed or in-progress analysis.

    Mutable so the orchestrator can update status/results as the pipeline
    progresses. Stored and retrieved via AnalysisStore implementations.
    """

    id: str  # UUID
    repository_owner: str
    repository_name: str
    repository_url: str
    status: str  # "running" | "completed" | "failed"
    created_at: str  # ISO 8601

    # Updated after completion
    completed_at: str | None = None
    error_message: str | None = None

    # Snapshot summary
    total_files: int = 0
    total_directories: int = 0
    total_size_bytes: int = 0

    # Counts
    total_evidence: int = 0
    total_findings: int = 0

    # Serialized JSON data
    findings_json: str | None = None
    ai_review_json: str | None = None
    report_html: str | None = None
    report_json_content: str | None = None
    report_markdown: str | None = None
    pipeline_summary_json: str | None = None
    language_summary_json: str | None = None


class AnalysisStore(Protocol):
    """Protocol for persisting analysis records.

    Implementations must be safe for concurrent access.
    """

    def save(self, record: AnalysisRecord) -> None:
        """Save a new analysis record."""
        ...

    def update(self, record: AnalysisRecord) -> None:
        """Update an existing analysis record."""
        ...

    def get(self, analysis_id: str) -> AnalysisRecord | None:
        """Retrieve an analysis record by ID."""
        ...

    def list_recent(self, limit: int = 20) -> list[AnalysisRecord]:
        """Return the most recent analyses, ordered by creation time descending."""
        ...
