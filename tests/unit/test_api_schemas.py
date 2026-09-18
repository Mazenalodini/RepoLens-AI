"""Unit tests for API schemas."""

import pytest
from pydantic import ValidationError

from repolens.api.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    ErrorResponse,
    FindingItem,
    FindingsResponse,
    HealthResponse,
    ReportResponse,
)


class TestAnalysisRequest:
    def test_valid_request(self) -> None:
        req = AnalysisRequest(repository_url="https://github.com/owner/repo")
        assert req.repository_url == "https://github.com/owner/repo"
        assert req.include_ai_review is True
        assert req.report_format == "html"

    def test_custom_options(self) -> None:
        req = AnalysisRequest(
            repository_url="https://github.com/a/b",
            include_ai_review=False,
            report_format="json",
        )
        assert req.include_ai_review is False
        assert req.report_format == "json"

    def test_empty_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AnalysisRequest(repository_url="")

    def test_missing_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AnalysisRequest()


class TestAnalysisResponse:
    def test_minimal_response(self) -> None:
        resp = AnalysisResponse(
            analysis_id="abc",
            repository_name="owner/repo",
            repository_url="https://github.com/owner/repo",
            status="completed",
            created_at="2026-01-01T00:00:00+00:00",
        )
        assert resp.analysis_id == "abc"
        assert resp.ai_review_available is False
        assert resp.error_message is None


class TestFindingItem:
    def test_finding_item(self) -> None:
        item = FindingItem(
            rule_id="NO_README",
            finding_id="abc123",
            category="documentation",
            severity="high",
            title="No README",
            description="Missing README",
            source_analyzer="repository_health",
        )
        assert item.recommendation is None

    def test_with_recommendation(self) -> None:
        item = FindingItem(
            rule_id="NO_TESTS",
            finding_id="def456",
            category="testing",
            severity="high",
            title="No tests",
            description="No tests",
            source_analyzer="testing_intelligence",
            recommendation="Add tests",
        )
        assert item.recommendation == "Add tests"


class TestFindingsResponse:
    def test_empty_findings(self) -> None:
        resp = FindingsResponse(analysis_id="abc", total=0, findings=[])
        assert resp.total == 0
        assert resp.findings == []


class TestReportResponse:
    def test_report_response(self) -> None:
        resp = ReportResponse(
            analysis_id="abc",
            format="html",
            content="<h1>Report</h1>",
            filename="report.html",
        )
        assert resp.format == "html"


class TestHealthResponse:
    def test_defaults(self) -> None:
        resp = HealthResponse()
        assert resp.status == "ok"
        assert resp.version == "0.1.0"


class TestErrorResponse:
    def test_error_response(self) -> None:
        resp = ErrorResponse(error="Bad request", detail="Invalid URL")
        assert resp.error == "Bad request"
        assert resp.detail == "Invalid URL"

    def test_no_detail(self) -> None:
        resp = ErrorResponse(error="Server error")
        assert resp.detail is None
