"""RepoLens AI — Finding Rules.

Deterministic rules that transform structured evidence into normalized findings.
Each rule has a single, documented responsibility.
"""

from repolens.domain.evidence import Evidence, MeasuredMetric, ObservedFact
from repolens.domain.finding import (
    Finding,
    FindingCategory,
    FindingRule,
    FindingSeverity,
)


class NoReadmeRule:
    """Produces a finding when the repository has no README."""

    @property
    def rule_id(self) -> str:
        return "NO_README"

    def evaluate(self, evidence: tuple[Evidence, ...]) -> list[Finding]:
        for item in evidence:
            if (
                isinstance(item, ObservedFact)
                and item.description == "README not detected"
            ):
                return [
                    Finding(
                        rule_id=self.rule_id,
                        category=FindingCategory.DOCUMENTATION,
                        severity=FindingSeverity.HIGH,
                        title="No README found",
                        description=(
                            "The repository does not contain a README file. "
                            "A README is essential for project discoverability "
                            "and contributor onboarding."
                        ),
                        evidence_keys=(item.sort_key,),
                        source_analyzer=item.analyzer_id,
                        recommendation=(
                            "Add a README.md with project description, "
                            "setup instructions, and usage examples."
                        ),
                    )
                ]
        return []


class NoTestsRule:
    """Produces a finding when no test files are detected."""

    @property
    def rule_id(self) -> str:
        return "NO_TESTS"

    def evaluate(self, evidence: tuple[Evidence, ...]) -> list[Finding]:
        for item in evidence:
            if (
                isinstance(item, ObservedFact)
                and item.description == "No test files detected"
            ):
                return [
                    Finding(
                        rule_id=self.rule_id,
                        category=FindingCategory.TESTING,
                        severity=FindingSeverity.HIGH,
                        title="No test files detected",
                        description=(
                            "The repository contains no files classified as tests. "
                            "Absence of tests increases the risk of undetected regressions."
                        ),
                        evidence_keys=(item.sort_key,),
                        source_analyzer=item.analyzer_id,
                        recommendation="Add unit tests for core functionality.",
                    )
                ]
        return []


class NoProjectMetadataRule:
    """Produces a finding when project metadata is not detected."""

    @property
    def rule_id(self) -> str:
        return "NO_PROJECT_METADATA"

    def evaluate(self, evidence: tuple[Evidence, ...]) -> list[Finding]:
        for item in evidence:
            if (
                isinstance(item, ObservedFact)
                and item.description == "Project metadata not detected"
            ):
                return [
                    Finding(
                        rule_id=self.rule_id,
                        category=FindingCategory.REPOSITORY,
                        severity=FindingSeverity.MEDIUM,
                        title="No project metadata detected",
                        description=(
                            "No standard project configuration file "
                            "(e.g. pyproject.toml, package.json) was detected. "
                            "This may hinder dependency management and packaging."
                        ),
                        evidence_keys=(item.sort_key,),
                        source_analyzer=item.analyzer_id,
                        recommendation=(
                            "Add a pyproject.toml or equivalent project manifest."
                        ),
                    )
                ]
        return []


class LowTestRatioRule:
    """Produces a finding when the test-to-source file ratio is below threshold."""

    THRESHOLD = 0.1

    @property
    def rule_id(self) -> str:
        return "LOW_TEST_RATIO"

    def evaluate(self, evidence: tuple[Evidence, ...]) -> list[Finding]:
        source_count: int | None = None
        test_count: int | None = None

        for item in evidence:
            if isinstance(item, MeasuredMetric):
                if item.name == "total_source_files":
                    source_count = int(item.value)
                elif item.name == "total_test_files":
                    test_count = int(item.value)

        if source_count is None or test_count is None:
            return []
        if source_count == 0:
            return []
        if test_count == 0:
            # NoTestsRule handles the zero-test case
            return []

        ratio = test_count / source_count
        if ratio < self.THRESHOLD:
            keys: list[tuple[str, ...]] = []
            for item in evidence:
                if isinstance(item, MeasuredMetric) and item.name in (
                    "total_source_files",
                    "total_test_files",
                ):
                    keys.append(item.sort_key)
            return [
                Finding(
                    rule_id=self.rule_id,
                    category=FindingCategory.TESTING,
                    severity=FindingSeverity.MEDIUM,
                    title="Low test-to-source file ratio",
                    description=(
                        f"The repository has {test_count} test file(s) "
                        f"for {source_count} source file(s) "
                        f"(ratio: {ratio:.2f}). "
                        f"A ratio below {self.THRESHOLD} suggests "
                        f"insufficient test coverage breadth."
                    ),
                    evidence_keys=tuple(keys),
                    source_analyzer="repository_health",
                    recommendation="Increase test coverage for critical modules.",
                )
            ]
        return []


class NoTestFrameworkRule:
    """Produces a finding when no test framework is detected."""

    @property
    def rule_id(self) -> str:
        return "NO_TEST_FRAMEWORK"

    def evaluate(self, evidence: tuple[Evidence, ...]) -> list[Finding]:
        for item in evidence:
            if (
                isinstance(item, ObservedFact)
                and item.description == "No Python test framework detected"
                and item.analyzer_id == "testing_intelligence"
            ):
                return [
                    Finding(
                        rule_id=self.rule_id,
                        category=FindingCategory.TESTING,
                        severity=FindingSeverity.MEDIUM,
                        title="No test framework detected",
                        description=(
                            "No recognized Python test framework (pytest, unittest) "
                            "was detected in the repository's test files."
                        ),
                        evidence_keys=(item.sort_key,),
                        source_analyzer=item.analyzer_id,
                        recommendation=(
                            "Adopt a standard test framework such as pytest."
                        ),
                    )
                ]
        return []


class NoTestConfigurationRule:
    """Produces a finding when no test configuration is detected."""

    @property
    def rule_id(self) -> str:
        return "NO_TEST_CONFIGURATION"

    def evaluate(self, evidence: tuple[Evidence, ...]) -> list[Finding]:
        for item in evidence:
            if (
                isinstance(item, ObservedFact)
                and item.description == "No test configuration detected"
                and item.analyzer_id == "testing_intelligence"
            ):
                return [
                    Finding(
                        rule_id=self.rule_id,
                        category=FindingCategory.TESTING,
                        severity=FindingSeverity.LOW,
                        title="No test configuration detected",
                        description=(
                            "No test configuration file "
                            "(pytest.ini, setup.cfg [tool:pytest], "
                            "pyproject.toml [tool.pytest]) was detected."
                        ),
                        evidence_keys=(item.sort_key,),
                        source_analyzer=item.analyzer_id,
                        recommendation=(
                            "Add a [tool.pytest.ini_options] section to "
                            "pyproject.toml for consistent test configuration."
                        ),
                    )
                ]
        return []


def get_default_rules() -> list[FindingRule]:
    """Return the default set of finding rules."""
    return [
        NoReadmeRule(),
        NoTestsRule(),
        NoProjectMetadataRule(),
        LowTestRatioRule(),
        NoTestFrameworkRule(),
        NoTestConfigurationRule(),
    ]
