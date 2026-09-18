"""Unit tests for CodeQualityAnalyzer."""

import pytest

from repolens.analyzers.code_quality import CodeQualityAnalyzer
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
    DiscoveredFileAccessError,
    FileModifiedError,
    FileTooLargeError,
)


class MockSourceReader(BoundedSourceReader):
    def __init__(self, file_contents: dict[str, str | Exception]) -> None:
        self.file_contents = file_contents
        self.bytes_read = 0

    def read_descriptor(self, descriptor: FileDescriptor) -> str:
        if descriptor.path not in self.file_contents:
            raise DiscoveredFileAccessError(f"Not discovered: {descriptor.path}")
        content = self.file_contents[descriptor.path]
        if isinstance(content, Exception):
            raise content
        self.bytes_read += len(content)
        return content


@pytest.fixture
def empty_snapshot() -> RepositorySnapshot:
    return RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
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


def test_code_quality_analyzer_empty_repository(empty_snapshot: RepositorySnapshot) -> None:
    reader = MockSourceReader({})
    analyzer = CodeQualityAnalyzer(reader)
    result = analyzer.analyze(empty_snapshot)

    assert result.status == AnalyzerStatus.SUCCESS
    metrics = {e.name: e.value for e in result.evidence if isinstance(e, MeasuredMetric)}
    assert metrics["python_source_file_count"] == 0
    assert metrics["python_source_lines"] == 0
    assert metrics["function_count"] == 0
    assert metrics["class_count"] == 0


def test_code_quality_analyzer_valid_python() -> None:
    desc = FileDescriptor("main.py", "main.py", ".py", 100, "Python", FileClassification.SOURCE)
    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
        files=(desc,),
        directories=(),
        project_metadata=None,
        total_files=1,
        total_directories=0,
        total_size_bytes=100,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )

    code = """
class A:
    def method_one(self):
        def nested():
            pass
        pass

async def top_level_async():
    class NestedClass:
        pass
    pass
"""
    reader = MockSourceReader({"main.py": code})
    analyzer = CodeQualityAnalyzer(reader)
    result = analyzer.analyze(snapshot)

    assert result.status == AnalyzerStatus.SUCCESS
    metrics = {e.name: e.value for e in result.evidence if isinstance(e, MeasuredMetric)}
    assert metrics["python_source_file_count"] == 1
    assert metrics["python_source_lines"] == len(code.splitlines())

    # 1 top level async, 1 method, 1 nested function = 3 functions
    assert metrics["function_count"] == 3
    # 1 top level class, 1 nested class = 2 classes
    assert metrics["class_count"] == 2

    assert all(e.analyzer_id == "code_quality" for e in result.evidence)


def test_code_quality_analyzer_syntax_error() -> None:
    desc = FileDescriptor("bad.py", "bad.py", ".py", 50, "Python", FileClassification.SOURCE)
    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
        files=(desc,),
        directories=(),
        project_metadata=None,
        total_files=1,
        total_directories=0,
        total_size_bytes=50,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )
    code = "def oops(:"  # invalid syntax
    reader = MockSourceReader({"bad.py": code})
    analyzer = CodeQualityAnalyzer(reader)
    result = analyzer.analyze(snapshot)

    assert result.status == AnalyzerStatus.SUCCESS

    metrics = {e.name: e.value for e in result.evidence if isinstance(e, MeasuredMetric)}
    # File count and lines are preserved even on syntax error
    assert metrics["python_source_file_count"] == 1
    assert metrics["python_source_lines"] == 1
    # But no functions/classes are counted
    assert metrics["function_count"] == 0
    assert metrics["class_count"] == 0

    facts = [e.description for e in result.evidence if isinstance(e, ObservedFact)]
    assert "Syntax error in bad.py" in facts


def test_code_quality_analyzer_ignores_non_python() -> None:
    desc1 = FileDescriptor(
        "main.js", "main.js", ".js", 100, "JavaScript", FileClassification.SOURCE
    )
    desc2 = FileDescriptor("test.py", "test.py", ".py", 100, "Python", FileClassification.TEST)
    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
        files=(desc1, desc2),
        directories=(),
        project_metadata=None,
        total_files=2,
        total_directories=0,
        total_size_bytes=200,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )
    # The reader shouldn't even be called
    reader = MockSourceReader({})
    analyzer = CodeQualityAnalyzer(reader)
    result = analyzer.analyze(snapshot)

    assert result.status == AnalyzerStatus.SUCCESS
    metrics = {e.name: e.value for e in result.evidence if isinstance(e, MeasuredMetric)}
    assert metrics["python_source_file_count"] == 0


def test_code_quality_analyzer_resource_limits() -> None:
    f1 = FileDescriptor("a.py", "a.py", ".py", 100, "Python", FileClassification.SOURCE)
    f2 = FileDescriptor("b.py", "b.py", ".py", 2000000, "Python", FileClassification.SOURCE)
    f3 = FileDescriptor("c.py", "c.py", ".py", 100, "Python", FileClassification.SOURCE)
    f4 = FileDescriptor("d.py", "d.py", ".py", 100, "Python", FileClassification.SOURCE)

    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
        files=(f1, f2, f3, f4),
        directories=(),
        project_metadata=None,
        total_files=4,
        total_directories=0,
        total_size_bytes=2000300,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )

    reader = MockSourceReader(
        {
            "a.py": "def a(): pass",
            "b.py": FileTooLargeError("Too large"),
            "c.py": FileModifiedError("File shrank"),
            "d.py": CumulativeLimitExceededError("Budget exhausted"),
        }
    )

    analyzer = CodeQualityAnalyzer(reader)
    result = analyzer.analyze(snapshot)

    assert result.status == AnalyzerStatus.SUCCESS

    # f1 is processed, f2 skipped, f3 halted, f4 skipped
    metrics = {e.name: e.value for e in result.evidence if isinstance(e, MeasuredMetric)}
    assert metrics["python_source_file_count"] == 1
    assert metrics["function_count"] == 1

    facts = [e.description for e in result.evidence if isinstance(e, ObservedFact)]
    assert "Python source file exceeds the 1 MB per-file limit: b.py" in facts
    assert "Analysis halted for file due to concurrent modification: c.py" in facts
    assert "Analysis halted: the 5 MB cumulative read limit was reached" in facts

    # Crucially, ensure no "Syntax error" was emitted for skipped/halted files
    assert not any("Syntax error" in f for f in facts)


def test_code_quality_analyzer_deterministic_ordering() -> None:
    f1 = FileDescriptor("z.py", "z.py", ".py", 100, "Python", FileClassification.SOURCE)
    f2 = FileDescriptor("a.py", "a.py", ".py", 100, "Python", FileClassification.SOURCE)

    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo("o", "r", "u", "c"),
        files=(f1, f2),  # passed out of order
        directories=(),
        project_metadata=None,
        total_files=2,
        total_directories=0,
        total_size_bytes=200,
        extension_counts=(),
        language_counts=(),
        classification_counts=(),
    )

    class TrackingReader(BoundedSourceReader):
        def __init__(self):
            self.read_order = []

        def read_descriptor(self, descriptor: FileDescriptor) -> str:
            self.read_order.append(descriptor.path)
            return "pass"

    reader = TrackingReader()
    analyzer = CodeQualityAnalyzer(reader)
    analyzer.analyze(snapshot)

    # Must process a.py before z.py deterministically
    assert reader.read_order == ["a.py", "z.py"]
