"""Unit tests for AnalyzerPipeline and AnalyzerRegistry."""

import pytest

from repolens.application.pipeline import AnalyzerPipeline, AnalyzerRegistry
from repolens.domain.analyzer import AnalyzerResult, AnalyzerStatus
from repolens.domain.discovery import RepositorySnapshot
from repolens.domain.evidence import ObservedFact
from repolens.domain.exceptions import PipelineError
from repolens.domain.repository import RepositoryInfo


class DummyAnalyzerSuccess:
    @property
    def analyzer_id(self) -> str:
        return "success_analyzer"

    def analyze(self, snapshot: RepositorySnapshot) -> AnalyzerResult:
        return AnalyzerResult(
            status=AnalyzerStatus.SUCCESS,
            evidence=(ObservedFact(analyzer_id=self.analyzer_id, description="Success fact"),),
        )


class DummyAnalyzerFailure:
    @property
    def analyzer_id(self) -> str:
        return "failure_analyzer"

    def analyze(self, snapshot: RepositorySnapshot) -> AnalyzerResult:
        raise RuntimeError("Something went wrong internally.")


class DummyAnalyzerSystemExit:
    @property
    def analyzer_id(self) -> str:
        return "exit_analyzer"

    def analyze(self, snapshot: RepositorySnapshot) -> AnalyzerResult:
        raise SystemExit(1)


@pytest.fixture
def empty_snapshot() -> RepositorySnapshot:
    return RepositorySnapshot(
        repository_info=RepositoryInfo(
            owner="test",
            name="test",
            url="https://github.com/test/test",
            clone_url="https://github.com/test/test.git",
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


def test_registry_prevents_duplicate_names() -> None:
    registry = AnalyzerRegistry()
    registry.register(DummyAnalyzerSuccess())

    with pytest.raises(PipelineError, match="is already registered"):
        # Registering the same analyzer class (same analyzer_id property) again
        registry.register(DummyAnalyzerSuccess())


def test_pipeline_sequential_execution(empty_snapshot: RepositorySnapshot) -> None:
    registry = AnalyzerRegistry()
    registry.register(DummyAnalyzerSuccess())

    pipeline = AnalyzerPipeline(registry)
    result = pipeline.run(empty_snapshot)

    assert result.is_successful is True
    assert len(result.results) == 1
    assert result.results[0][0] == "success_analyzer"
    assert result.results[0][1].status == AnalyzerStatus.SUCCESS
    assert result.total_evidence == 1
    assert len(result.evidence) == 1
    assert result.evidence[0].analyzer_id == "success_analyzer"


def test_pipeline_failure_isolation(empty_snapshot: RepositorySnapshot) -> None:
    registry = AnalyzerRegistry()
    registry.register(DummyAnalyzerSuccess())
    registry.register(DummyAnalyzerFailure())  # Fails

    # We add another analyzer to ensure execution continues AFTER the failure
    class AnotherSuccess:
        @property
        def analyzer_id(self) -> str:
            return "another_success"

        def analyze(self, snapshot: RepositorySnapshot) -> AnalyzerResult:
            return AnalyzerResult(status=AnalyzerStatus.SUCCESS)

    registry.register(AnotherSuccess())

    pipeline = AnalyzerPipeline(registry)
    result = pipeline.run(empty_snapshot)

    assert result.is_successful is False
    assert len(result.results) == 3

    # First succeeded
    assert result.results[0][0] == "success_analyzer"
    assert result.results[0][1].status == AnalyzerStatus.SUCCESS

    # Second failed but was caught and isolated
    assert result.results[1][0] == "failure_analyzer"
    assert result.results[1][1].status == AnalyzerStatus.ERROR
    assert "RuntimeError: Something went wrong internally." in result.results[1][1].errors[0]

    # Third succeeded (proves isolation didn't abort pipeline)
    assert result.results[2][0] == "another_success"
    assert result.results[2][1].status == AnalyzerStatus.SUCCESS


def test_pipeline_does_not_swallow_system_exit(empty_snapshot: RepositorySnapshot) -> None:
    registry = AnalyzerRegistry()
    registry.register(DummyAnalyzerSystemExit())

    pipeline = AnalyzerPipeline(registry)

    # The pipeline should NOT catch SystemExit
    with pytest.raises(SystemExit):
        pipeline.run(empty_snapshot)
