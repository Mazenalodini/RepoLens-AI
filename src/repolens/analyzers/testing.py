"""RepoLens AI — Testing Intelligence Analyzer.

Produces deterministic, structured evidence about the repository's testing
posture through static analysis of the discovery snapshot and file content.

Does NOT execute tests, claim coverage, or fabricate execution results.
"""

from repolens.domain.analyzer import Analyzer, AnalyzerResult, AnalyzerStatus
from repolens.domain.discovery import (
    FileClassification,
    RepositorySnapshot,
)
from repolens.domain.evidence import Evidence, MeasuredMetric, ObservedFact
from repolens.domain.source_reader import (
    BoundedSourceReader,
    CumulativeLimitExceededError,
    FileModifiedError,
    FileTooLargeError,
)

# Known test configuration files (lowercase for matching)
_TEST_CONFIG_FILES = frozenset({
    "pytest.ini",
    "conftest.py",
    "tox.ini",
    ".coveragerc",
})

# Patterns in pyproject.toml / setup.cfg that indicate pytest configuration
_PYTEST_TOML_MARKER = "[tool.pytest"
_PYTEST_CFG_MARKER = "[tool:pytest]"


class TestingIntelligenceAnalyzer(Analyzer):
    """Produces testing evidence from repository snapshot and source content.

    Analyzes:
    - Test file counts and locations
    - Test directory detection
    - Python test framework detection (pytest, unittest)
    - Test configuration file detection
    - Explicit absence evidence when nothing is found
    """

    __test__ = False

    def __init__(self, source_reader: BoundedSourceReader | None = None) -> None:
        self._source_reader = source_reader

    @property
    def analyzer_id(self) -> str:
        return "testing_intelligence"

    def analyze(self, snapshot: RepositorySnapshot) -> AnalyzerResult:
        evidence: list[Evidence] = []

        # 1. Test file detection
        test_files = [
            f for f in snapshot.files
            if f.classification == FileClassification.TEST
        ]
        test_files.sort(key=lambda f: f.path)

        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="test_file_count",
                value=len(test_files),
            )
        )

        # 2. Test directory detection
        test_dirs = set()
        for f in test_files:
            parts = f.path.split("/")
            if len(parts) > 1:
                test_dirs.add(parts[0])

        test_dir_names = sorted(test_dirs)
        evidence.append(
            MeasuredMetric(
                analyzer_id=self.analyzer_id,
                name="test_directory_count",
                value=len(test_dir_names),
            )
        )

        for dir_name in test_dir_names:
            evidence.append(
                ObservedFact(
                    analyzer_id=self.analyzer_id,
                    description=f"Test directory detected: {dir_name}",
                )
            )

        if not test_dir_names and test_files:
            evidence.append(
                ObservedFact(
                    analyzer_id=self.analyzer_id,
                    description="Test files found but no dedicated test directory",
                )
            )

        # 3. Test configuration detection
        config_detected = False
        for f in snapshot.files:
            name_lower = f.name.lower()
            if name_lower in _TEST_CONFIG_FILES:
                evidence.append(
                    ObservedFact(
                        analyzer_id=self.analyzer_id,
                        description=f"Test configuration file detected: {f.path}",
                    )
                )
                config_detected = True

        # Check pyproject.toml / setup.cfg for pytest markers
        config_detected = self._check_config_files(
            snapshot, evidence, config_detected
        )

        if not config_detected:
            evidence.append(
                ObservedFact(
                    analyzer_id=self.analyzer_id,
                    description="No test configuration detected",
                )
            )

        # 4. Framework detection (from test file content if reader available)
        frameworks_detected = self._detect_frameworks(
            test_files, evidence
        )

        if not frameworks_detected and test_files:
            evidence.append(
                ObservedFact(
                    analyzer_id=self.analyzer_id,
                    description="No Python test framework detected",
                )
            )

        if not test_files:
            evidence.append(
                ObservedFact(
                    analyzer_id=self.analyzer_id,
                    description="No test files detected in repository",
                )
            )

        return AnalyzerResult(
            status=AnalyzerStatus.SUCCESS,
            evidence=tuple(evidence),
        )

    def _check_config_files(
        self,
        snapshot: RepositorySnapshot,
        evidence: list[Evidence],
        already_detected: bool,
    ) -> bool:
        """Check pyproject.toml and setup.cfg for pytest configuration markers."""
        config_detected = already_detected

        if self._source_reader is None:
            return config_detected

        for f in snapshot.files:
            if f.name.lower() in ("pyproject.toml", "setup.cfg"):
                try:
                    content = self._source_reader.read_descriptor(f)
                    content_lower = content.lower()
                    if (
                        _PYTEST_TOML_MARKER in content_lower
                        or _PYTEST_CFG_MARKER in content_lower
                    ):
                        evidence.append(
                            ObservedFact(
                                analyzer_id=self.analyzer_id,
                                description=(
                                    f"Pytest configuration detected in {f.path}"
                                ),
                            )
                        )
                        config_detected = True
                except (
                    FileTooLargeError,
                    CumulativeLimitExceededError,
                    FileModifiedError,
                ):
                    continue

        return config_detected

    def _detect_frameworks(
        self,
        test_files: list,
        evidence: list[Evidence],
    ) -> bool:
        """Detect test frameworks from test file content patterns."""
        if self._source_reader is None or not test_files:
            return False

        pytest_detected = False
        unittest_detected = False

        for descriptor in test_files:
            if descriptor.language != "Python":
                continue
            try:
                content = self._source_reader.read_descriptor(descriptor)
            except (
                FileTooLargeError,
                CumulativeLimitExceededError,
                FileModifiedError,
            ):
                continue

            if not pytest_detected and "import pytest" in content:
                pytest_detected = True
            if not unittest_detected and "import unittest" in content:
                unittest_detected = True

            if pytest_detected and unittest_detected:
                break

        if pytest_detected:
            evidence.append(
                ObservedFact(
                    analyzer_id=self.analyzer_id,
                    description="Python test framework detected: pytest",
                )
            )
        if unittest_detected:
            evidence.append(
                ObservedFact(
                    analyzer_id=self.analyzer_id,
                    description="Python test framework detected: unittest",
                )
            )

        return pytest_detected or unittest_detected
