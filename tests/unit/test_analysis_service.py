"""Unit tests for AnalysisService."""

import json
from pathlib import Path

import pytest

from repolens.application.analysis_service import AnalysisService
from repolens.domain.exceptions import (
    ConcurrencyLimitError,
    RepositorySizeError,
    ValidationError,
)
from repolens.domain.persistence import AnalysisRecord
from repolens.domain.repository import RepositoryInfo, RepositoryWorkspace


class FakeStore:
    """In-memory store for testing."""

    def __init__(self) -> None:
        self._records: dict[str, AnalysisRecord] = {}

    def save(self, record: AnalysisRecord) -> None:
        self._records[record.id] = record

    def update(self, record: AnalysisRecord) -> None:
        self._records[record.id] = record

    def get(self, analysis_id: str) -> AnalysisRecord | None:
        return self._records.get(analysis_id)

    def list_recent(self, limit: int = 20) -> list[AnalysisRecord]:
        records = sorted(
            self._records.values(), key=lambda r: r.created_at, reverse=True
        )
        return records[:limit]


class FakeSource:
    """Fake repository source for testing."""

    def __init__(self, workspace: RepositoryWorkspace) -> None:
        self._workspace = workspace

    def acquire(self, source: str) -> RepositoryWorkspace:
        return self._workspace


@pytest.fixture
def workspace(tmp_path: Path) -> RepositoryWorkspace:
    """Create a minimal workspace with a README."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "README.md").write_text("# Test")
    (repo_dir / "main.py").write_text("print('hello')")

    info = RepositoryInfo(
        owner="test-owner",
        name="test-repo",
        url="https://github.com/test-owner/test-repo",
        clone_url="https://github.com/test-owner/test-repo.git",
    )
    return RepositoryWorkspace(root=repo_dir, info=info)


@pytest.fixture
def service(workspace: RepositoryWorkspace) -> AnalysisService:
    """Create an AnalysisService with mocked dependencies."""
    source = FakeSource(workspace)
    store = FakeStore()
    return AnalysisService(
        source=source,
        store=store,
        ai_provider=None,
        max_concurrent=2,
    )


class TestAnalyze:
    def test_successful_analysis(self, service: AnalysisService) -> None:
        analysis_id = service.analyze(
            "https://github.com/test-owner/test-repo",
            include_ai_review=False,
        )
        assert analysis_id is not None

        record = service.get_analysis(analysis_id)
        assert record is not None
        assert record.status == "completed"
        assert record.repository_owner == "test-owner"
        assert record.repository_name == "test-repo"
        assert record.completed_at is not None

    def test_findings_are_persisted(self, service: AnalysisService) -> None:
        analysis_id = service.analyze(
            "https://github.com/test-owner/test-repo",
            include_ai_review=False,
        )
        record = service.get_analysis(analysis_id)
        assert record is not None
        # findings_json should be a valid JSON list
        if record.findings_json:
            findings = json.loads(record.findings_json)
            assert isinstance(findings, list)

    def test_reports_are_generated(self, service: AnalysisService) -> None:
        analysis_id = service.analyze(
            "https://github.com/test-owner/test-repo",
            include_ai_review=False,
        )
        record = service.get_analysis(analysis_id)
        assert record is not None
        assert record.report_html is not None
        assert record.report_json_content is not None
        assert record.report_markdown is not None

    def test_invalid_url_fails(self, service: AnalysisService) -> None:
        with pytest.raises(ValidationError):
            service.analyze("not-a-github-url")

    def test_workspace_cleaned_up_on_success(
        self, workspace: RepositoryWorkspace, service: AnalysisService
    ) -> None:
        service.analyze(
            "https://github.com/test-owner/test-repo",
            include_ai_review=False,
        )
        # Workspace should be closed after analysis
        assert workspace.is_closed


class TestConcurrencyLimit:
    def test_concurrency_limit_exceeded(
        self, workspace: RepositoryWorkspace
    ) -> None:
        source = FakeSource(workspace)
        store = FakeStore()
        service = AnalysisService(
            source=source,
            store=store,
            ai_provider=None,
            max_concurrent=0,  # No slots available
        )
        # Semaphore(0) means acquire always fails
        with pytest.raises(ConcurrencyLimitError):
            service.analyze("https://github.com/test-owner/test-repo")


class TestRepositorySizeLimit:
    def test_oversized_repo_rejected(
        self, workspace: RepositoryWorkspace
    ) -> None:
        source = FakeSource(workspace)
        store = FakeStore()
        service = AnalysisService(
            source=source,
            store=store,
            ai_provider=None,
            max_repo_size_bytes=1,  # 1 byte limit
        )
        with pytest.raises(RepositorySizeError):
            service.analyze(
                "https://github.com/test-owner/test-repo",
                include_ai_review=False,
            )


class TestListAndGet:
    def test_list_analyses(self, service: AnalysisService) -> None:
        service.analyze(
            "https://github.com/test-owner/test-repo",
            include_ai_review=False,
        )
        results = service.list_analyses()
        assert len(results) == 1

    def test_get_missing_returns_none(self, service: AnalysisService) -> None:
        assert service.get_analysis("nonexistent") is None
