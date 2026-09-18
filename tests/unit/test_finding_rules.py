"""Unit tests for individual finding rules."""

from repolens.application.finding_rules import (
    LowTestRatioRule,
    NoProjectMetadataRule,
    NoReadmeRule,
    NoTestConfigurationRule,
    NoTestFrameworkRule,
    NoTestsRule,
    get_default_rules,
)
from repolens.domain.evidence import MeasuredMetric, ObservedFact
from repolens.domain.finding import FindingCategory, FindingSeverity

# --- NoReadmeRule ---


def test_no_readme_triggers_on_readme_not_detected() -> None:
    evidence = (ObservedFact("repository_health", "README not detected"),)
    findings = NoReadmeRule().evaluate(evidence)
    assert len(findings) == 1
    assert findings[0].rule_id == "NO_README"
    assert findings[0].category == FindingCategory.DOCUMENTATION
    assert findings[0].severity == FindingSeverity.HIGH
    assert findings[0].source_analyzer == "repository_health"
    assert findings[0].recommendation is not None


def test_no_readme_does_not_trigger_when_readme_present() -> None:
    evidence = (ObservedFact("repository_health", "README detected"),)
    findings = NoReadmeRule().evaluate(evidence)
    assert len(findings) == 0


def test_no_readme_does_not_trigger_on_empty_evidence() -> None:
    findings = NoReadmeRule().evaluate(())
    assert len(findings) == 0


# --- NoTestsRule ---


def test_no_tests_triggers_on_no_test_files() -> None:
    evidence = (ObservedFact("repository_health", "No test files detected"),)
    findings = NoTestsRule().evaluate(evidence)
    assert len(findings) == 1
    assert findings[0].rule_id == "NO_TESTS"
    assert findings[0].category == FindingCategory.TESTING
    assert findings[0].severity == FindingSeverity.HIGH


def test_no_tests_does_not_trigger_when_tests_present() -> None:
    evidence = (ObservedFact("repository_health", "Tests detected"),)
    findings = NoTestsRule().evaluate(evidence)
    assert len(findings) == 0


# --- NoProjectMetadataRule ---


def test_no_metadata_triggers_on_not_detected() -> None:
    evidence = (ObservedFact("repository_health", "Project metadata not detected"),)
    findings = NoProjectMetadataRule().evaluate(evidence)
    assert len(findings) == 1
    assert findings[0].rule_id == "NO_PROJECT_METADATA"
    assert findings[0].category == FindingCategory.REPOSITORY
    assert findings[0].severity == FindingSeverity.MEDIUM


def test_no_metadata_does_not_trigger_when_detected() -> None:
    evidence = (ObservedFact("repository_health", "Project metadata detected"),)
    findings = NoProjectMetadataRule().evaluate(evidence)
    assert len(findings) == 0


# --- LowTestRatioRule ---


def test_low_test_ratio_triggers_below_threshold() -> None:
    evidence = (
        MeasuredMetric("repository_health", "total_source_files", 100),
        MeasuredMetric("repository_health", "total_test_files", 5),
    )
    findings = LowTestRatioRule().evaluate(evidence)
    assert len(findings) == 1
    assert findings[0].rule_id == "LOW_TEST_RATIO"
    assert findings[0].severity == FindingSeverity.MEDIUM
    assert "5 test file(s)" in findings[0].description
    assert "100 source file(s)" in findings[0].description


def test_low_test_ratio_does_not_trigger_above_threshold() -> None:
    evidence = (
        MeasuredMetric("repository_health", "total_source_files", 10),
        MeasuredMetric("repository_health", "total_test_files", 5),
    )
    findings = LowTestRatioRule().evaluate(evidence)
    assert len(findings) == 0


def test_low_test_ratio_does_not_trigger_with_zero_source() -> None:
    evidence = (
        MeasuredMetric("repository_health", "total_source_files", 0),
        MeasuredMetric("repository_health", "total_test_files", 0),
    )
    findings = LowTestRatioRule().evaluate(evidence)
    assert len(findings) == 0


def test_low_test_ratio_does_not_trigger_with_zero_tests() -> None:
    """Zero tests are handled by NoTestsRule, not LowTestRatioRule."""
    evidence = (
        MeasuredMetric("repository_health", "total_source_files", 10),
        MeasuredMetric("repository_health", "total_test_files", 0),
    )
    findings = LowTestRatioRule().evaluate(evidence)
    assert len(findings) == 0


def test_low_test_ratio_does_not_trigger_without_metrics() -> None:
    findings = LowTestRatioRule().evaluate(())
    assert len(findings) == 0


# --- NoTestFrameworkRule ---


def test_no_test_framework_triggers() -> None:
    evidence = (
        ObservedFact("testing_intelligence", "No Python test framework detected"),
    )
    findings = NoTestFrameworkRule().evaluate(evidence)
    assert len(findings) == 1
    assert findings[0].rule_id == "NO_TEST_FRAMEWORK"
    assert findings[0].severity == FindingSeverity.MEDIUM


def test_no_test_framework_ignores_other_analyzer() -> None:
    """Rule requires evidence from testing_intelligence specifically."""
    evidence = (
        ObservedFact("other_analyzer", "No Python test framework detected"),
    )
    findings = NoTestFrameworkRule().evaluate(evidence)
    assert len(findings) == 0


# --- NoTestConfigurationRule ---


def test_no_test_config_triggers() -> None:
    evidence = (
        ObservedFact("testing_intelligence", "No test configuration detected"),
    )
    findings = NoTestConfigurationRule().evaluate(evidence)
    assert len(findings) == 1
    assert findings[0].rule_id == "NO_TEST_CONFIGURATION"
    assert findings[0].severity == FindingSeverity.LOW


def test_no_test_config_ignores_other_analyzer() -> None:
    evidence = (
        ObservedFact("other_analyzer", "No test configuration detected"),
    )
    findings = NoTestConfigurationRule().evaluate(evidence)
    assert len(findings) == 0


# --- get_default_rules ---


def test_get_default_rules_returns_expected_count() -> None:
    rules = get_default_rules()
    assert len(rules) == 6


def test_get_default_rules_have_unique_ids() -> None:
    rules = get_default_rules()
    ids = [r.rule_id for r in rules]
    assert len(ids) == len(set(ids))


# --- Evidence traceability ---


def test_finding_preserves_evidence_keys() -> None:
    fact = ObservedFact("repository_health", "README not detected")
    findings = NoReadmeRule().evaluate((fact,))
    assert len(findings) == 1
    assert fact.sort_key in findings[0].evidence_keys


# --- Determinism ---


def test_rule_evaluation_is_deterministic() -> None:
    evidence = (ObservedFact("repository_health", "README not detected"),)
    f1 = NoReadmeRule().evaluate(evidence)
    f2 = NoReadmeRule().evaluate(evidence)
    assert f1[0].finding_id == f2[0].finding_id
    assert f1[0].title == f2[0].title
