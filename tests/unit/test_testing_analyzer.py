"""Unit tests for TestingIntelligenceAnalyzer."""

from repolens.analyzers.testing import TestingIntelligenceAnalyzer
from repolens.domain.analyzer import AnalyzerStatus
from repolens.domain.discovery import (
    FileClassification,
    FileDescriptor,
    RepositorySnapshot,
)
from repolens.domain.evidence import MeasuredMetric, ObservedFact
from repolens.domain.repository import RepositoryInfo
from repolens.domain.source_reader import (
    BoundedSourceReader,
    CumulativeLimitExceededError,
    FileTooLargeError,
)

FC = FileClassification


class MockSourceReader(BoundedSourceReader):
    """Test double for BoundedSourceReader."""

    def __init__(self, files: dict[str, str | Exception]) -> None:
        self._files = files

    def read_descriptor(self, descriptor) -> str:
        result = self._files.get(descriptor.path, "")
        if isinstance(result, Exception):
            raise result
        return result


def _fd(
    path: str,
    ext: str = ".py",
    lang: str | None = "Python",
    cls: FileClassification = FC.SOURCE,
    size: int = 100,
) -> FileDescriptor:
    name = path.rsplit("/", 1)[-1]
    return FileDescriptor(path, name, ext, size, lang, cls)


def _make_snapshot(
    files: tuple[FileDescriptor, ...] = (),
) -> RepositorySnapshot:
    return RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
        files=files,
        directories=(),
        project_metadata=None,
        total_files=len(files),
        total_directories=0,
        total_size_bytes=sum(f.size_bytes for f in files),
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )


# --- Basic behavior ---


def test_analyzer_id() -> None:
    analyzer = TestingIntelligenceAnalyzer()
    assert analyzer.analyzer_id == "testing_intelligence"


def test_empty_repository() -> None:
    analyzer = TestingIntelligenceAnalyzer()
    result = analyzer.analyze(_make_snapshot())
    assert result.status == AnalyzerStatus.SUCCESS

    metrics = {
        e.name: e.value
        for e in result.evidence
        if isinstance(e, MeasuredMetric)
    }
    assert metrics["test_file_count"] == 0
    assert metrics["test_directory_count"] == 0

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "No test files detected in repository" in facts
    assert "No test configuration detected" in facts


# --- Test file detection ---


def test_detects_test_files() -> None:
    files = (
        _fd("tests/test_main.py", cls=FC.TEST),
        _fd("tests/test_utils.py", cls=FC.TEST),
        _fd("src/main.py"),
    )
    analyzer = TestingIntelligenceAnalyzer()
    result = analyzer.analyze(_make_snapshot(files))

    metrics = {
        e.name: e.value
        for e in result.evidence
        if isinstance(e, MeasuredMetric)
    }
    assert metrics["test_file_count"] == 2


# --- Test directory detection ---


def test_detects_test_directories() -> None:
    files = (
        _fd("tests/test_a.py", cls=FC.TEST),
        _fd("tests/test_b.py", cls=FC.TEST),
    )
    analyzer = TestingIntelligenceAnalyzer()
    result = analyzer.analyze(_make_snapshot(files))

    metrics = {
        e.name: e.value
        for e in result.evidence
        if isinstance(e, MeasuredMetric)
    }
    assert metrics["test_directory_count"] == 1

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "Test directory detected: tests" in facts


def test_test_files_without_dedicated_directory() -> None:
    files = (_fd("test_main.py", cls=FC.TEST),)
    analyzer = TestingIntelligenceAnalyzer()
    result = analyzer.analyze(_make_snapshot(files))

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "Test files found but no dedicated test directory" in facts


# --- Framework detection ---


def test_detects_pytest_framework() -> None:
    files = (_fd("tests/test_a.py", cls=FC.TEST),)
    reader = MockSourceReader({
        "tests/test_a.py": "import pytest\n\ndef test_x(): pass",
    })
    analyzer = TestingIntelligenceAnalyzer(source_reader=reader)
    result = analyzer.analyze(_make_snapshot(files))

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "Python test framework detected: pytest" in facts


def test_detects_unittest_framework() -> None:
    files = (_fd("tests/test_a.py", cls=FC.TEST),)
    content = (
        "import unittest\n\n"
        "class Test(unittest.TestCase): pass"
    )
    reader = MockSourceReader({"tests/test_a.py": content})
    analyzer = TestingIntelligenceAnalyzer(source_reader=reader)
    result = analyzer.analyze(_make_snapshot(files))

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "Python test framework detected: unittest" in facts


def test_detects_both_frameworks() -> None:
    files = (
        _fd("tests/test_a.py", cls=FC.TEST),
        _fd("tests/test_b.py", cls=FC.TEST),
    )
    reader = MockSourceReader({
        "tests/test_a.py": "import pytest",
        "tests/test_b.py": "import unittest",
    })
    analyzer = TestingIntelligenceAnalyzer(source_reader=reader)
    result = analyzer.analyze(_make_snapshot(files))

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "Python test framework detected: pytest" in facts
    assert "Python test framework detected: unittest" in facts


def test_no_framework_detected_without_reader() -> None:
    files = (_fd("tests/test_a.py", cls=FC.TEST),)
    analyzer = TestingIntelligenceAnalyzer()
    result = analyzer.analyze(_make_snapshot(files))

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "No Python test framework detected" in facts


def test_no_framework_detected_with_non_python_test() -> None:
    files = (
        _fd("tests/test_a.js", ext=".js", lang="JavaScript", cls=FC.TEST),
    )
    reader = MockSourceReader({
        "tests/test_a.js": "const test = require('jest')",
    })
    analyzer = TestingIntelligenceAnalyzer(source_reader=reader)
    result = analyzer.analyze(_make_snapshot(files))

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "No Python test framework detected" in facts


# --- Configuration detection ---


def test_detects_pytest_ini() -> None:
    files = (
        _fd("pytest.ini", ext=".ini", lang=None, cls=FC.CONFIGURATION, size=50),
    )
    analyzer = TestingIntelligenceAnalyzer()
    result = analyzer.analyze(_make_snapshot(files))

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "Test configuration file detected: pytest.ini" in facts
    assert "No test configuration detected" not in facts


def test_detects_conftest() -> None:
    files = (_fd("conftest.py", size=50),)
    analyzer = TestingIntelligenceAnalyzer()
    result = analyzer.analyze(_make_snapshot(files))

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "Test configuration file detected: conftest.py" in facts


def test_detects_pytest_config_in_pyproject_toml() -> None:
    files = (
        _fd(
            "pyproject.toml", ext=".toml", lang="TOML",
            cls=FC.CONFIGURATION, size=200,
        ),
    )
    reader = MockSourceReader({
        "pyproject.toml": (
            "[tool.pytest.ini_options]\ntestpaths = ['tests']"
        ),
    })
    analyzer = TestingIntelligenceAnalyzer(source_reader=reader)
    result = analyzer.analyze(_make_snapshot(files))

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "Pytest configuration detected in pyproject.toml" in facts


def test_no_config_when_pyproject_has_no_pytest_section() -> None:
    files = (
        _fd(
            "pyproject.toml", ext=".toml", lang="TOML",
            cls=FC.CONFIGURATION, size=200,
        ),
    )
    reader = MockSourceReader({
        "pyproject.toml": "[build-system]\nrequires = ['setuptools']",
    })
    analyzer = TestingIntelligenceAnalyzer(source_reader=reader)
    result = analyzer.analyze(_make_snapshot(files))

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "No test configuration detected" in facts


# --- Resilience ---


def test_framework_detection_survives_read_error() -> None:
    files = (_fd("tests/test_a.py", cls=FC.TEST),)
    reader = MockSourceReader({
        "tests/test_a.py": FileTooLargeError("too large"),
    })
    analyzer = TestingIntelligenceAnalyzer(source_reader=reader)
    result = analyzer.analyze(_make_snapshot(files))

    assert result.status == AnalyzerStatus.SUCCESS
    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "No Python test framework detected" in facts


def test_config_detection_survives_read_error() -> None:
    files = (
        _fd(
            "pyproject.toml", ext=".toml", lang="TOML",
            cls=FC.CONFIGURATION, size=2000000,
        ),
    )
    reader = MockSourceReader({
        "pyproject.toml": CumulativeLimitExceededError("limit"),
    })
    analyzer = TestingIntelligenceAnalyzer(source_reader=reader)
    result = analyzer.analyze(_make_snapshot(files))

    assert result.status == AnalyzerStatus.SUCCESS


# --- Determinism ---


def test_output_is_deterministic() -> None:
    files = (
        _fd("tests/test_a.py", cls=FC.TEST),
        _fd("tests/test_b.py", cls=FC.TEST),
    )
    reader = MockSourceReader({
        "tests/test_a.py": "import pytest",
        "tests/test_b.py": "import unittest",
    })
    analyzer = TestingIntelligenceAnalyzer(source_reader=reader)
    snapshot = _make_snapshot(files)
    r1 = analyzer.analyze(snapshot)
    r2 = analyzer.analyze(snapshot)
    assert r1.evidence == r2.evidence


# --- Absence ---


def test_absence_evidence_for_non_python_repo() -> None:
    files = (
        _fd("index.js", ext=".js", lang="JavaScript"),
    )
    analyzer = TestingIntelligenceAnalyzer()
    result = analyzer.analyze(_make_snapshot(files))

    facts = [
        e.description for e in result.evidence if isinstance(e, ObservedFact)
    ]
    assert "No test files detected in repository" in facts
    assert "No test configuration detected" in facts
