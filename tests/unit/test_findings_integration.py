"""Integration tests for the Evidence → Findings pipeline.

Verifies that evidence from analyzers flows correctly through the
Findings Engine and produces expected findings.
"""

from repolens.application.finding_rules import get_default_rules
from repolens.application.findings_engine import FindingRuleRegistry, FindingsEngine
from repolens.domain.analyzer import AnalyzerResult, AnalyzerStatus, PipelineResult
from repolens.domain.evidence import MeasuredMetric, ObservedFact
from repolens.domain.finding import FindingSeverity


def _make_engine() -> FindingsEngine:
    reg = FindingRuleRegistry()
    for rule in get_default_rules():
        reg.register(rule)
    return FindingsEngine(reg)


# --- Evidence → Findings Engine ---


def test_healthy_repo_produces_no_high_findings() -> None:
    """A repository with README, tests, and metadata produces no high-severity findings."""
    evidence = (
        ObservedFact("repository_health", "README detected"),
        ObservedFact("repository_health", "Tests detected"),
        ObservedFact("repository_health", "Project metadata detected"),
        MeasuredMetric("repository_health", "total_source_files", 20),
        MeasuredMetric("repository_health", "total_test_files", 10),
    )
    engine = _make_engine()
    result = engine.evaluate(evidence)
    high_findings = result.by_severity(FindingSeverity.HIGH)
    assert len(high_findings) == 0


def test_unhealthy_repo_produces_expected_findings() -> None:
    """A repo missing README, tests, and metadata triggers all relevant rules."""
    evidence = (
        ObservedFact("repository_health", "README not detected"),
        ObservedFact("repository_health", "No test files detected"),
        ObservedFact("repository_health", "Project metadata not detected"),
        MeasuredMetric("repository_health", "total_source_files", 10),
        MeasuredMetric("repository_health", "total_test_files", 0),
    )
    engine = _make_engine()
    result = engine.evaluate(evidence)

    rule_ids = {f.rule_id for f in result.findings}
    assert "NO_README" in rule_ids
    assert "NO_TESTS" in rule_ids
    assert "NO_PROJECT_METADATA" in rule_ids


def test_testing_intelligence_evidence_triggers_findings() -> None:
    """Testing intelligence evidence flows through the engine correctly."""
    evidence = (
        ObservedFact("testing_intelligence", "No Python test framework detected"),
        ObservedFact("testing_intelligence", "No test configuration detected"),
        MeasuredMetric("testing_intelligence", "test_file_count", 2),
    )
    engine = _make_engine()
    result = engine.evaluate(evidence)

    rule_ids = {f.rule_id for f in result.findings}
    assert "NO_TEST_FRAMEWORK" in rule_ids
    assert "NO_TEST_CONFIGURATION" in rule_ids


def test_pipeline_result_flows_into_findings() -> None:
    """PipelineResult.evidence integrates with FindingsEngine."""
    health_result = AnalyzerResult(
        status=AnalyzerStatus.SUCCESS,
        evidence=(
            ObservedFact("repository_health", "README not detected"),
            ObservedFact("repository_health", "Tests detected"),
            ObservedFact("repository_health", "Project metadata detected"),
            MeasuredMetric("repository_health", "total_source_files", 20),
            MeasuredMetric("repository_health", "total_test_files", 10),
        ),
    )
    testing_result = AnalyzerResult(
        status=AnalyzerStatus.SUCCESS,
        evidence=(
            MeasuredMetric("testing_intelligence", "test_file_count", 5),
            ObservedFact("testing_intelligence", "Python test framework detected: pytest"),
            ObservedFact("testing_intelligence", "No test configuration detected"),
        ),
    )
    pipeline = PipelineResult(
        results=(
            ("repository_health", health_result),
            ("testing_intelligence", testing_result),
        ),
        is_successful=True,
    )

    engine = _make_engine()
    result = engine.evaluate(pipeline.evidence)

    rule_ids = {f.rule_id for f in result.findings}
    # README missing → NO_README
    assert "NO_README" in rule_ids
    # Test config missing → NO_TEST_CONFIGURATION
    assert "NO_TEST_CONFIGURATION" in rule_ids
    # Tests exist and framework detected → no NO_TESTS or NO_TEST_FRAMEWORK
    assert "NO_TESTS" not in rule_ids
    assert "NO_TEST_FRAMEWORK" not in rule_ids


def test_low_test_ratio_with_pipeline_evidence() -> None:
    """Low test ratio detected through pipeline evidence."""
    health_result = AnalyzerResult(
        status=AnalyzerStatus.SUCCESS,
        evidence=(
            MeasuredMetric("repository_health", "total_source_files", 100),
            MeasuredMetric("repository_health", "total_test_files", 3),
            ObservedFact("repository_health", "README detected"),
            ObservedFact("repository_health", "Tests detected"),
            ObservedFact("repository_health", "Project metadata detected"),
        ),
    )
    pipeline = PipelineResult(
        results=(("repository_health", health_result),),
        is_successful=True,
    )

    engine = _make_engine()
    result = engine.evaluate(pipeline.evidence)

    rule_ids = {f.rule_id for f in result.findings}
    assert "LOW_TEST_RATIO" in rule_ids


def test_findings_ordering_is_deterministic() -> None:
    evidence = (
        ObservedFact("repository_health", "README not detected"),
        ObservedFact("repository_health", "No test files detected"),
        ObservedFact("repository_health", "Project metadata not detected"),
        ObservedFact("testing_intelligence", "No Python test framework detected"),
        ObservedFact("testing_intelligence", "No test configuration detected"),
    )
    engine = _make_engine()
    r1 = engine.evaluate(evidence)
    r2 = engine.evaluate(evidence)
    assert len(r1.findings) == len(r2.findings)
    for f1, f2 in zip(r1.findings, r2.findings, strict=True):
        assert f1.finding_id == f2.finding_id


def test_findings_sorted_by_severity_then_category() -> None:
    evidence = (
        ObservedFact("repository_health", "README not detected"),
        ObservedFact("repository_health", "Project metadata not detected"),
        ObservedFact("testing_intelligence", "No test configuration detected"),
    )
    engine = _make_engine()
    result = engine.evaluate(evidence)
    severities = [f.severity for f in result.findings]
    # HIGH should come before MEDIUM, MEDIUM before LOW
    severity_values = [
        {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}[s.value]
        for s in severities
    ]
    assert severity_values == sorted(severity_values)
