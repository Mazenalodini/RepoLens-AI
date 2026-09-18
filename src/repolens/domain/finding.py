"""RepoLens AI — Finding Domain Models.

Defines the normalized Finding model, categories, severities, and the
protocol for deterministic finding rules.
"""

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from repolens.domain.evidence import Evidence


class FindingCategory(Enum):
    """Categories for findings, aligned with PROJECT_SPEC analysis domains."""

    REPOSITORY = "repository"
    ARCHITECTURE = "architecture"
    CODE_QUALITY = "code_quality"
    TESTING = "testing"
    GIT = "git"
    DOCUMENTATION = "documentation"
    DEPENDENCY = "dependency"
    SECURITY_HYGIENE = "security_hygiene"


class FindingSeverity(Enum):
    """Deterministic, explainable severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    """A normalized, rule-based finding derived from structured evidence.

    The finding_id is deterministically computed from the rule_id and
    source evidence sort keys, ensuring identical evidence and rules
    always produce the same identity.
    """

    rule_id: str
    category: FindingCategory
    severity: FindingSeverity
    title: str
    description: str
    evidence_keys: tuple[tuple[str, ...], ...]
    source_analyzer: str
    recommendation: str | None = None

    @property
    def finding_id(self) -> str:
        """Deterministic identity derived from rule and evidence."""
        hasher = hashlib.sha256()
        hasher.update(self.rule_id.encode("utf-8"))
        for key in self.evidence_keys:
            for part in key:
                hasher.update(part.encode("utf-8"))
        return hasher.hexdigest()[:16]


class FindingRule(Protocol):
    """Protocol for a deterministic finding rule.

    A rule evaluates structured evidence and produces zero or more findings.
    Rules must be pure: identical evidence input produces identical output.
    """

    @property
    def rule_id(self) -> str:
        """Unique identifier for this rule."""
        ...

    def evaluate(self, evidence: tuple[Evidence, ...]) -> list[Finding]:
        """Evaluate evidence and return findings. May return empty list."""
        ...


@dataclass(frozen=True)
class FindingsResult:
    """Immutable result of the findings engine evaluation."""

    findings: tuple[Finding, ...]

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    def by_severity(self, severity: FindingSeverity) -> tuple[Finding, ...]:
        """Return findings filtered by severity."""
        return tuple(f for f in self.findings if f.severity == severity)

    def by_category(self, category: FindingCategory) -> tuple[Finding, ...]:
        """Return findings filtered by category."""
        return tuple(f for f in self.findings if f.category == category)
