"""Unit tests for SQLiteAnalysisStore."""

from pathlib import Path

import pytest

from repolens.domain.persistence import AnalysisRecord
from repolens.infrastructure.analysis_store import SQLiteAnalysisStore
from repolens.infrastructure.database import (
    create_db_engine,
    create_session_factory,
    create_tables,
)


@pytest.fixture
def store(tmp_path: Path) -> SQLiteAnalysisStore:
    """Create a fresh SQLite store backed by a temp file."""
    db_path = tmp_path / "test.db"
    engine = create_db_engine(f"sqlite:///{db_path}")
    create_tables(engine)
    factory = create_session_factory(engine)
    return SQLiteAnalysisStore(factory)


def _make_record(
    analysis_id: str = "test-id-1",
    status: str = "running",
) -> AnalysisRecord:
    return AnalysisRecord(
        id=analysis_id,
        repository_owner="owner",
        repository_name="repo",
        repository_url="https://github.com/owner/repo",
        status=status,
        created_at="2026-01-01T00:00:00+00:00",
    )


class TestSave:
    def test_save_and_get(self, store: SQLiteAnalysisStore) -> None:
        record = _make_record()
        store.save(record)

        result = store.get("test-id-1")
        assert result is not None
        assert result.id == "test-id-1"
        assert result.repository_owner == "owner"
        assert result.repository_name == "repo"
        assert result.status == "running"

    def test_get_missing_returns_none(self, store: SQLiteAnalysisStore) -> None:
        assert store.get("nonexistent") is None


class TestUpdate:
    def test_update_changes_fields(self, store: SQLiteAnalysisStore) -> None:
        record = _make_record()
        store.save(record)

        record.status = "completed"
        record.completed_at = "2026-01-01T00:05:00+00:00"
        record.total_findings = 3
        record.findings_json = '[{"title":"test"}]'
        store.update(record)

        result = store.get("test-id-1")
        assert result is not None
        assert result.status == "completed"
        assert result.completed_at == "2026-01-01T00:05:00+00:00"
        assert result.total_findings == 3
        assert result.findings_json == '[{"title":"test"}]'

    def test_update_missing_record_is_noop(
        self, store: SQLiteAnalysisStore
    ) -> None:
        record = _make_record(analysis_id="missing")
        # Should not raise
        store.update(record)


class TestListRecent:
    def test_empty_store(self, store: SQLiteAnalysisStore) -> None:
        assert store.list_recent() == []

    def test_ordering(self, store: SQLiteAnalysisStore) -> None:
        for i in range(5):
            record = _make_record(analysis_id=f"id-{i}")
            record.created_at = f"2026-01-01T00:0{i}:00+00:00"
            store.save(record)

        result = store.list_recent(limit=3)
        assert len(result) == 3
        # Most recent first
        assert result[0].id == "id-4"
        assert result[1].id == "id-3"
        assert result[2].id == "id-2"

    def test_limit(self, store: SQLiteAnalysisStore) -> None:
        for i in range(10):
            record = _make_record(analysis_id=f"id-{i:02d}")
            record.created_at = f"2026-01-01T00:{i:02d}:00+00:00"
            store.save(record)

        assert len(store.list_recent(limit=5)) == 5


class TestPersistenceRoundTrip:
    def test_all_fields_survive_roundtrip(
        self, store: SQLiteAnalysisStore
    ) -> None:
        record = AnalysisRecord(
            id="roundtrip-1",
            repository_owner="test-owner",
            repository_name="test-repo",
            repository_url="https://github.com/test-owner/test-repo",
            status="completed",
            created_at="2026-01-01T00:00:00+00:00",
            completed_at="2026-01-01T00:05:00+00:00",
            error_message=None,
            total_files=42,
            total_directories=7,
            total_size_bytes=123456,
            total_evidence=15,
            total_findings=3,
            findings_json='[{"rule_id":"TEST"}]',
            ai_review_json='{"summary":"Good"}',
            report_html="<h1>Report</h1>",
            report_json_content='{"report": true}',
            report_markdown="# Report",
            pipeline_summary_json='[{"status":"success"}]',
            language_summary_json='[{"language":"python","count":10}]',
        )
        store.save(record)

        result = store.get("roundtrip-1")
        assert result is not None
        assert result.total_files == 42
        assert result.total_directories == 7
        assert result.total_size_bytes == 123456
        assert result.total_evidence == 15
        assert result.total_findings == 3
        assert result.findings_json == '[{"rule_id":"TEST"}]'
        assert result.ai_review_json == '{"summary":"Good"}'
        assert result.report_html == "<h1>Report</h1>"
        assert result.report_json_content == '{"report": true}'
        assert result.report_markdown == "# Report"
        assert result.pipeline_summary_json == '[{"status":"success"}]'
        assert result.language_summary_json == '[{"language":"python","count":10}]'
