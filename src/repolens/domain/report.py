"""RepoLens AI — Report Domain Models.

Defines the report artifact and generator protocol.
Report generators are side-effect free: they return ReportArtifact
objects and never write files directly.
"""

from dataclasses import dataclass
from typing import Protocol

from repolens.domain.analysis import AnalysisResult


@dataclass(frozen=True)
class ReportArtifact:
    """Generated report output.

    Contains the rendered content and suggested filename.
    Writing to disk is the responsibility of a CLI/API boundary.
    """

    format: str  # "html", "json", "markdown"
    content: str
    filename: str


class ReportGenerator(Protocol):
    """Protocol for report generators.

    Generators must be side-effect free: they consume an AnalysisResult
    and return a ReportArtifact without performing I/O.
    """

    @property
    def format_name(self) -> str:
        """Report format identifier."""
        ...

    def generate(self, analysis: AnalysisResult) -> ReportArtifact:
        """Generate a report from the analysis result.

        Must tolerate missing optional data (e.g. AIReview).
        """
        ...
