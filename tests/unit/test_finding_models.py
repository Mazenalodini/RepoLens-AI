"""Unit tests for Finding domain models."""

from repolens.domain.finding import (
    Finding,
    FindingCategory,
    FindingSeverity,
    FindingsResult,
)


def test_finding_creation() -> None:
    finding = Finding(
        rule_id="TEST_RULE",
        category=FindingCategory.TESTING,
        severity=FindingSeverity.HIGH,
        title="Test title",
        description="Test description",
        evidence_keys=(("a", "b"),),
        source_analyzer="test_analyzer",
        recommendation="Fix it",
    )
    assert finding.rule_id == "TEST_RULE"
    assert finding.category == FindingCategory.TESTING
    assert finding.severity == FindingSeverity.HIGH
    assert finding.recommendation == "Fix it"


def test_finding_id_is_deterministic() -> None:
    f1 = Finding(
        rule_id="RULE_A",
        category=FindingCategory.REPOSITORY,
        severity=FindingSeverity.MEDIUM,
        title="Title",
        description="Desc",
        evidence_keys=(("key1", "key2"),),
        source_analyzer="analyzer_x",
    )
    f2 = Finding(
        rule_id="RULE_A",
        category=FindingCategory.REPOSITORY,
        severity=FindingSeverity.MEDIUM,
        title="Title",
        description="Desc",
        evidence_keys=(("key1", "key2"),),
        source_analyzer="analyzer_x",
    )
    assert f1.finding_id == f2.finding_id
    assert len(f1.finding_id) == 16


def test_finding_id_differs_for_different_evidence() -> None:
    f1 = Finding(
        rule_id="RULE_A",
        category=FindingCategory.REPOSITORY,
        severity=FindingSeverity.MEDIUM,
        title="Title",
        description="Desc",
        evidence_keys=(("key1",),),
        source_analyzer="analyzer_x",
    )
    f2 = Finding(
        rule_id="RULE_A",
        category=FindingCategory.REPOSITORY,
        severity=FindingSeverity.MEDIUM,
        title="Title",
        description="Desc",
        evidence_keys=(("key2",),),
        source_analyzer="analyzer_x",
    )
    assert f1.finding_id != f2.finding_id


def test_finding_id_differs_for_different_rules() -> None:
    f1 = Finding(
        rule_id="RULE_A",
        category=FindingCategory.REPOSITORY,
        severity=FindingSeverity.MEDIUM,
        title="Title",
        description="Desc",
        evidence_keys=(("key1",),),
        source_analyzer="analyzer_x",
    )
    f2 = Finding(
        rule_id="RULE_B",
        category=FindingCategory.REPOSITORY,
        severity=FindingSeverity.MEDIUM,
        title="Title",
        description="Desc",
        evidence_keys=(("key1",),),
        source_analyzer="analyzer_x",
    )
    assert f1.finding_id != f2.finding_id


def test_finding_is_frozen() -> None:
    finding = Finding(
        rule_id="RULE",
        category=FindingCategory.TESTING,
        severity=FindingSeverity.LOW,
        title="T",
        description="D",
        evidence_keys=(),
        source_analyzer="a",
    )
    try:
        finding.title = "changed"  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except AttributeError:
        pass


def test_finding_category_values() -> None:
    expected = {
        "repository", "architecture", "code_quality", "testing",
        "git", "documentation", "dependency", "security_hygiene",
    }
    actual = {c.value for c in FindingCategory}
    assert actual == expected


def test_finding_severity_values() -> None:
    expected = {"critical", "high", "medium", "low", "info"}
    actual = {s.value for s in FindingSeverity}
    assert actual == expected


def test_findings_result_total() -> None:
    f1 = Finding(
        rule_id="R1",
        category=FindingCategory.TESTING,
        severity=FindingSeverity.HIGH,
        title="T1",
        description="D1",
        evidence_keys=(),
        source_analyzer="a",
    )
    f2 = Finding(
        rule_id="R2",
        category=FindingCategory.REPOSITORY,
        severity=FindingSeverity.LOW,
        title="T2",
        description="D2",
        evidence_keys=(),
        source_analyzer="a",
    )
    result = FindingsResult(findings=(f1, f2))
    assert result.total_findings == 2


def test_findings_result_by_severity() -> None:
    f1 = Finding(
        rule_id="R1",
        category=FindingCategory.TESTING,
        severity=FindingSeverity.HIGH,
        title="T1",
        description="D1",
        evidence_keys=(),
        source_analyzer="a",
    )
    f2 = Finding(
        rule_id="R2",
        category=FindingCategory.REPOSITORY,
        severity=FindingSeverity.LOW,
        title="T2",
        description="D2",
        evidence_keys=(),
        source_analyzer="a",
    )
    result = FindingsResult(findings=(f1, f2))
    assert len(result.by_severity(FindingSeverity.HIGH)) == 1
    assert len(result.by_severity(FindingSeverity.LOW)) == 1
    assert len(result.by_severity(FindingSeverity.MEDIUM)) == 0


def test_findings_result_by_category() -> None:
    f1 = Finding(
        rule_id="R1",
        category=FindingCategory.TESTING,
        severity=FindingSeverity.HIGH,
        title="T1",
        description="D1",
        evidence_keys=(),
        source_analyzer="a",
    )
    result = FindingsResult(findings=(f1,))
    assert len(result.by_category(FindingCategory.TESTING)) == 1
    assert len(result.by_category(FindingCategory.REPOSITORY)) == 0


def test_findings_result_empty() -> None:
    result = FindingsResult(findings=())
    assert result.total_findings == 0
    assert result.by_severity(FindingSeverity.HIGH) == ()
