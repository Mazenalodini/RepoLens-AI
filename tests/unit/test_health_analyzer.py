"""Unit tests for RepositoryHealthAnalyzer."""

from unittest.mock import patch

import pytest

from repolens.analyzers.health import RepositoryHealthAnalyzer
from repolens.domain.analyzer import AnalyzerStatus
from repolens.domain.discovery import (
    DirectoryDescriptor,
    FileClassification,
    FileDescriptor,
    ProjectMetadata,
    RepositorySnapshot,
)
from repolens.domain.evidence import MeasuredMetric, ObservedFact
from repolens.domain.repository import RepositoryInfo


@pytest.fixture
def empty_snapshot() -> RepositorySnapshot:
    return RepositorySnapshot(
        repository_info=RepositoryInfo(
            owner="test",
            name="empty",
            url="https://github.com/test/empty",
            clone_url="https://github.com/test/empty.git",
        ),
        files=(),
        directories=(),
        project_metadata=None,
        total_files=0,
        total_directories=0,
        total_size_bytes=0,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )


@pytest.fixture
def rich_snapshot() -> RepositorySnapshot:
    return RepositorySnapshot(
        repository_info=RepositoryInfo(
            owner="test",
            name="rich",
            url="https://github.com/test/rich",
            clone_url="https://github.com/test/rich.git",
        ),
        files=(
            FileDescriptor(
                "README.md", "README.md", ".md", 100, "Markdown", FileClassification.DOCUMENTATION
            ),
            FileDescriptor("main.py", "main.py", ".py", 500, "Python", FileClassification.SOURCE),
            FileDescriptor(
                "test_main.py", "test_main.py", ".py", 300, "Python", FileClassification.TEST
            ),
            FileDescriptor(
                "pyproject.toml",
                "pyproject.toml",
                ".toml",
                200,
                "TOML",
                FileClassification.CONFIGURATION,
            ),
        ),
        directories=(DirectoryDescriptor("src", "src"),),
        project_metadata=ProjectMetadata(name="rich", version="1.0.0"),
        total_files=4,
        total_directories=1,
        total_size_bytes=1100,
        extension_counts=((".py", 2), (".md", 1), (".toml", 1)),
        language_counts=(("Python", 2), ("Markdown", 1), ("TOML", 1)),
        classification_counts=(
            (FileClassification.SOURCE, 1),
            (FileClassification.TEST, 1),
            (FileClassification.DOCUMENTATION, 1),
            (FileClassification.CONFIGURATION, 1),
        ),
    )


def test_health_analyzer_empty_snapshot(empty_snapshot: RepositorySnapshot) -> None:
    analyzer = RepositoryHealthAnalyzer()
    result = analyzer.analyze(empty_snapshot)

    assert result.status == AnalyzerStatus.SUCCESS

    # Verify metrics are zero
    metrics = {e.name: e.value for e in result.evidence if isinstance(e, MeasuredMetric)}
    assert metrics["total_files"] == 0
    assert metrics["total_directories"] == 0
    assert metrics["total_size_bytes"] == 0
    assert metrics["total_source_files"] == 0
    assert metrics["total_test_files"] == 0
    assert metrics["total_documentation_files"] == 0
    assert metrics["total_configuration_files"] == 0

    # Verify negative facts are present
    facts = [e.description for e in result.evidence if isinstance(e, ObservedFact)]
    assert "No test files detected" in facts
    assert "README not detected" in facts
    assert "Project metadata not detected" in facts

    # Verify analyzer_id
    assert all(e.analyzer_id == "repository_health" for e in result.evidence)


def test_health_analyzer_rich_snapshot(rich_snapshot: RepositorySnapshot) -> None:
    analyzer = RepositoryHealthAnalyzer()
    result = analyzer.analyze(rich_snapshot)

    assert result.status == AnalyzerStatus.SUCCESS

    # Verify metrics
    metrics = {e.name: e.value for e in result.evidence if isinstance(e, MeasuredMetric)}
    assert metrics["total_files"] == 4
    assert metrics["total_directories"] == 1
    assert metrics["total_size_bytes"] == 1100
    assert metrics["total_source_files"] == 1
    assert metrics["total_test_files"] == 1
    assert metrics["total_documentation_files"] == 1
    assert metrics["total_configuration_files"] == 1

    # Verify positive facts
    facts = [e.description for e in result.evidence if isinstance(e, ObservedFact)]
    assert "Tests detected" in facts
    assert "README detected" in facts
    assert "Project metadata detected" in facts

    # Verify analyzer_id
    assert all(e.analyzer_id == "repository_health" for e in result.evidence)


def test_health_analyzer_evidence_ordering_is_deterministic(
    rich_snapshot: RepositorySnapshot,
) -> None:
    analyzer = RepositoryHealthAnalyzer()
    result1 = analyzer.analyze(rich_snapshot)
    result2 = analyzer.analyze(rich_snapshot)

    # Identical snapshots must produce identical evidence in identical order
    assert result1.evidence == result2.evidence

    # Verify it matches the sorting rules applied by __post_init__ in AnalyzerResult
    # (MeasuredMetric < ObservedFact), etc.
    assert isinstance(result1.evidence[0], MeasuredMetric)


def test_health_analyzer_performs_no_io(rich_snapshot: RepositorySnapshot) -> None:
    # Explicitly verify that no filesystem or network IO is attempted.
    # The analyzer should only rely on the provided snapshot data.
    with (
        patch("builtins.open") as mock_open,
        patch("os.stat") as mock_os_stat,
        patch("pathlib.Path.exists") as mock_path_exists,
    ):
        analyzer = RepositoryHealthAnalyzer()
        result = analyzer.analyze(rich_snapshot)

        # Verify successful analysis
        assert result.status == AnalyzerStatus.SUCCESS

        # Verify that no IO operations were called
        mock_open.assert_not_called()
        mock_os_stat.assert_not_called()
        mock_path_exists.assert_not_called()
