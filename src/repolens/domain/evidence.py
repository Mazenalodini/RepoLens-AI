"""RepoLens AI — Evidence Domain Models.

Provides deterministic and objective representations of facts and metrics
discovered within a repository.
"""

from dataclasses import dataclass
from typing import Protocol


class Evidence(Protocol):
    """Protocol for all objective repository evidence."""

    @property
    def sort_key(self) -> tuple[str, ...]:
        """Provide a deterministic sort key for the evidence."""
        ...


@dataclass(frozen=True)
class ObservedFact:
    """An objective, binary fact observed in the repository."""

    analyzer_id: str
    description: str
    location: str | None = None

    @property
    def sort_key(self) -> tuple[str, ...]:
        return (self.analyzer_id, "ObservedFact", self.description, self.location or "")


@dataclass(frozen=True)
class MeasuredMetric:
    """An objective, quantitative metric measured in the repository."""

    analyzer_id: str
    name: str
    value: float | int
    location: str | None = None

    @property
    def sort_key(self) -> tuple[str, ...]:
        return (self.analyzer_id, "MeasuredMetric", self.name, str(self.value), self.location or "")
