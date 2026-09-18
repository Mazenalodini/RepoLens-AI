"""Unit tests for FindingsEngine and FindingRuleRegistry."""

import pytest

from repolens.application.finding_rules import get_default_rules
from repolens.application.findings_engine import FindingRuleRegistry, FindingsEngine
from repolens.domain.evidence import MeasuredMetric, ObservedFact
from repolens.domain.finding import (
    Finding,
    FindingCategory,
    FindingSeverity,
)


class StubRule:
    """A test rule that always produces one finding."""

    def __init__(self, rule_id: str = "STUB") -> None:
        self._rule_id = rule_id

    @property
    def rule_id(self) -> str:
        return self._rule_id

    def evaluate(self, evidence: tuple) -> list[Finding]:
        return [
            Finding(
                rule_id=self._rule_id,
                category=FindingCategory.REPOSITORY,
                severity=FindingSeverity.INFO,
                title="Stub finding",
                description="Always produced",
                evidence_keys=(),
                source_analyzer="stub",
            )
        ]


class FailingRule:
    """A test rule that always raises."""

    @property
    def rule_id(self) -> str:
        return "FAILING"

    def evaluate(self, evidence: tuple) -> list[Finding]:
        raise RuntimeError("Rule failure")


# --- FindingRuleRegistry ---


def test_registry_registers_rule() -> None:
    reg = FindingRuleRegistry()
    reg.register(StubRule())
    assert len(reg.rules) == 1


def test_registry_rejects_duplicate_rule_id() -> None:
    reg = FindingRuleRegistry()
    reg.register(StubRule("A"))
    with pytest.raises(ValueError, match="already registered"):
        reg.register(StubRule("A"))


def test_registry_preserves_insertion_order() -> None:
    reg = FindingRuleRegistry()
    reg.register(StubRule("A"))
    reg.register(StubRule("B"))
    reg.register(StubRule("C"))
    ids = [r.rule_id for r in reg.rules]
    assert ids == ["A", "B", "C"]


# --- FindingsEngine ---


def test_engine_evaluates_rules() -> None:
    reg = FindingRuleRegistry()
    reg.register(StubRule())
    engine = FindingsEngine(reg)
    result = engine.evaluate(())
    assert result.total_findings == 1


def test_engine_returns_empty_for_no_rules() -> None:
    reg = FindingRuleRegistry()
    engine = FindingsEngine(reg)
    result = engine.evaluate(())
    assert result.total_findings == 0


def test_engine_isolates_failing_rules() -> None:
    reg = FindingRuleRegistry()
    reg.register(StubRule("GOOD"))
    reg.register(FailingRule())
    engine = FindingsEngine(reg)
    result = engine.evaluate(())
    # The good rule still produces its finding
    assert result.total_findings == 1
    assert result.findings[0].rule_id == "GOOD"


def test_engine_multiple_findings_sorted_by_severity() -> None:
    class HighRule:
        @property
        def rule_id(self) -> str:
            return "HIGH_RULE"

        def evaluate(self, evidence: tuple) -> list[Finding]:
            return [
                Finding(
                    rule_id=self.rule_id,
                    category=FindingCategory.TESTING,
                    severity=FindingSeverity.HIGH,
                    title="High",
                    description="High severity",
                    evidence_keys=(),
                    source_analyzer="x",
                )
            ]

    class LowRule:
        @property
        def rule_id(self) -> str:
            return "LOW_RULE"

        def evaluate(self, evidence: tuple) -> list[Finding]:
            return [
                Finding(
                    rule_id=self.rule_id,
                    category=FindingCategory.TESTING,
                    severity=FindingSeverity.LOW,
                    title="Low",
                    description="Low severity",
                    evidence_keys=(),
                    source_analyzer="x",
                )
            ]

    reg = FindingRuleRegistry()
    # Register low first to verify sorting overrides insertion order
    reg.register(LowRule())
    reg.register(HighRule())
    engine = FindingsEngine(reg)
    result = engine.evaluate(())
    assert result.findings[0].severity == FindingSeverity.HIGH
    assert result.findings[1].severity == FindingSeverity.LOW


def test_engine_determinism() -> None:
    reg = FindingRuleRegistry()
    for rule in get_default_rules():
        reg.register(rule)
    engine = FindingsEngine(reg)
    evidence = (
        ObservedFact("repository_health", "README not detected"),
        ObservedFact("repository_health", "No test files detected"),
    )
    r1 = engine.evaluate(evidence)
    r2 = engine.evaluate(evidence)
    assert r1.total_findings == r2.total_findings
    for f1, f2 in zip(r1.findings, r2.findings, strict=True):
        assert f1.finding_id == f2.finding_id


def test_engine_empty_evidence_with_default_rules() -> None:
    reg = FindingRuleRegistry()
    for rule in get_default_rules():
        reg.register(rule)
    engine = FindingsEngine(reg)
    result = engine.evaluate(())
    # No evidence matches any rule
    assert result.total_findings == 0


def test_engine_unsupported_evidence_type() -> None:
    """Rules should gracefully ignore evidence they don't understand."""
    reg = FindingRuleRegistry()
    for rule in get_default_rules():
        reg.register(rule)
    engine = FindingsEngine(reg)
    evidence = (
        MeasuredMetric("unknown_analyzer", "unknown_metric", 42),
    )
    result = engine.evaluate(evidence)
    assert result.total_findings == 0
