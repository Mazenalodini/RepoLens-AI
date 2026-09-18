"""RepoLens AI — Analyzer Domain Models.

Defines the contract for repository analyzers and the immutable structures
for their results and pipeline execution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from repolens.domain.discovery import RepositorySnapshot
from repolens.domain.evidence import Evidence


class AnalyzerStatus(Enum):
    """The execution outcome of a specific analyzer."""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class AnalyzerResult:
    """Immutable result from a single analyzer execution.

    Evidence is guaranteed to be deterministically ordered.
    """

    status: AnalyzerStatus
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Ensure evidence is deterministically ordered."""
        if self.evidence:
            sorted_evidence = tuple(sorted(self.evidence, key=lambda e: e.sort_key))
            # Bypass frozen restriction for initialization
            object.__setattr__(self, "evidence", sorted_evidence)


class Analyzer(Protocol):
    """Protocol for all concrete repository analyzers."""

    @property
    def analyzer_id(self) -> str:
        """Unique identifier for this analyzer."""
        ...

    def analyze(self, snapshot: RepositorySnapshot) -> AnalyzerResult:
        """Execute the analyzer against the repository snapshot."""
        ...


@dataclass(frozen=True)
class PipelineResult:
    """Immutable, deterministic result of the entire analyzer pipeline execution.

    Results are ordered deterministically by the analyzer execution sequence.
    """

    results: tuple[tuple[str, AnalyzerResult], ...]
    is_successful: bool

    @property
    def evidence(self) -> tuple[Evidence, ...]:
        """Return a deterministically ordered collection of all gathered evidence."""
        all_evidence = []
        for _, result in self.results:
            all_evidence.extend(result.evidence)
        return tuple(sorted(all_evidence, key=lambda e: e.sort_key))

    @property
    def total_evidence(self) -> int:
        """Calculate the total pieces of evidence gathered across all analyzers."""
        return len(self.evidence)

    def get_result(self, analyzer_id: str) -> AnalyzerResult | None:
        """Retrieve the result for a specific analyzer."""
        for ident, result in self.results:
            if ident == analyzer_id:
                return result
        return None
