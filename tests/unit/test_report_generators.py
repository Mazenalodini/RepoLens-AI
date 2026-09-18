"""Unit tests for report generators (JSON, Markdown, HTML)."""

import json

from repolens.domain.ai_models import AIReview, AIReviewResult
from repolens.domain.analysis import AnalysisResult
from repolens.domain.analyzer import AnalyzerResult, AnalyzerStatus, PipelineResult
from repolens.domain.discovery import (
    FileClassification,
    FileDescriptor,
    ProjectMetadata,
    RepositorySnapshot,
)
from repolens.domain.evidence import MeasuredMetric, ObservedFact
from repolens.domain.finding import (
    Finding,
    FindingCategory,
    FindingSeverity,
    FindingsResult,
)
from repolens.domain.repository import RepositoryInfo
from repolens.reports.html_report import HTMLReportGenerator
from repolens.reports.json_report import JSONReportGenerator
from repolens.reports.markdown_report import MarkdownReportGenerator


def _make_analysis(
    *,
    ai_review: AIReviewResult | None = None,
    findings: tuple[Finding, ...] = (),
    evidence: tuple = (),
) -> AnalysisResult:
    snapshot = RepositorySnapshot(
        repository_info=RepositoryInfo(
            "owner", "repo",
            "https://github.com/owner/repo",
            "https://github.com/owner/repo.git",
        ),
        files=(
            FileDescriptor(
                "main.py", "main.py", ".py", 100,
                "Python", FileClassification.SOURCE,
            ),
        ),
        directories=(),
        project_metadata=ProjectMetadata("myproj", "1.0"),
        total_files=1,
        total_directories=0,
        total_size_bytes=100,
        extension_counts=((".py", 1),),
        language_counts=(("Python", 1),),
        classification_counts=(
            (FileClassification.SOURCE, 1),
        ),
    )
    pipeline = PipelineResult(
        results=(
            (
                "repository_health",
                AnalyzerResult(
                    status=AnalyzerStatus.SUCCESS,
                    evidence=evidence,
                ),
            ),
        ),
        is_successful=True,
    )
    return AnalysisResult(
        snapshot=snapshot,
        pipeline_result=pipeline,
        findings_result=FindingsResult(findings=findings),
        ai_review_result=ai_review,
        timestamp="2026-09-18T22:00:00Z",
    )


def _make_ai_success() -> AIReviewResult:
    return AIReviewResult(
        review=AIReview(
            executive_summary="Good project overall.",
            strengths=("Clean code", "Good tests"),
            concerns=("No CI",),
            recommendations=("Add CI", "Improve docs"),
            overall_assessment="Healthy repository.",
            provider_model="gemini-2.5-flash",
        ),
        error=None,
        is_successful=True,
    )


def _make_ai_failure() -> AIReviewResult:
    return AIReviewResult(
        review=None,
        error="Provider timeout",
        is_successful=False,
    )


def _make_finding() -> Finding:
    return Finding(
        rule_id="NO_README",
        category=FindingCategory.DOCUMENTATION,
        severity=FindingSeverity.HIGH,
        title="No README found",
        description="Repository has no README.",
        evidence_keys=(),
        source_analyzer="repository_health",
        recommendation="Add a README.md.",
    )


# ===================================================
# JSON Report
# ===================================================


class TestJSONReport:
    """Tests for JSONReportGenerator."""

    def test_format_name(self) -> None:
        gen = JSONReportGenerator()
        assert gen.format_name == "json"

    def test_generates_valid_json(self) -> None:
        analysis = _make_analysis()
        artifact = JSONReportGenerator().generate(analysis)
        data = json.loads(artifact.content)
        assert isinstance(data, dict)
        assert artifact.format == "json"
        assert artifact.filename == "repo_report.json"

    def test_contains_all_sections(self) -> None:
        analysis = _make_analysis(
            ai_review=_make_ai_success(),
        )
        artifact = JSONReportGenerator().generate(analysis)
        data = json.loads(artifact.content)
        expected_keys = {
            "report_metadata",
            "executive_summary",
            "repository_overview",
            "technology_stack",
            "project_structure",
            "project_metadata",
            "code_quality",
            "testing",
            "repository_health",
            "git_health",
            "documentation",
            "dependencies",
            "architecture",
            "findings",
            "ai_engineering_review",
            "recommendations",
        }
        assert expected_keys.issubset(data.keys())

    def test_missing_ai_review(self) -> None:
        analysis = _make_analysis(ai_review=None)
        artifact = JSONReportGenerator().generate(analysis)
        data = json.loads(artifact.content)
        assert data["ai_engineering_review"]["status"] == (
            "not_requested"
        )

    def test_ai_review_failure(self) -> None:
        analysis = _make_analysis(
            ai_review=_make_ai_failure(),
        )
        artifact = JSONReportGenerator().generate(analysis)
        data = json.loads(artifact.content)
        assert data["ai_engineering_review"]["status"] == (
            "unavailable"
        )

    def test_ai_review_success(self) -> None:
        analysis = _make_analysis(
            ai_review=_make_ai_success(),
        )
        artifact = JSONReportGenerator().generate(analysis)
        data = json.loads(artifact.content)
        ai = data["ai_engineering_review"]
        assert ai["status"] == "available"
        assert ai["executive_summary"] == (
            "Good project overall."
        )

    def test_findings_included(self) -> None:
        finding = _make_finding()
        analysis = _make_analysis(findings=(finding,))
        artifact = JSONReportGenerator().generate(analysis)
        data = json.loads(artifact.content)
        assert data["findings"]["total"] == 1
        assert data["findings"]["items"][0]["rule_id"] == (
            "NO_README"
        )

    def test_empty_findings(self) -> None:
        analysis = _make_analysis()
        artifact = JSONReportGenerator().generate(analysis)
        data = json.loads(artifact.content)
        assert data["findings"]["total"] == 0
        assert data["findings"]["items"] == []

    def test_deterministic(self) -> None:
        analysis = _make_analysis(
            ai_review=_make_ai_success(),
            findings=(_make_finding(),),
        )
        gen = JSONReportGenerator()
        a1 = gen.generate(analysis)
        a2 = gen.generate(analysis)
        assert a1.content == a2.content

    def test_metadata_preserved(self) -> None:
        analysis = _make_analysis()
        artifact = JSONReportGenerator().generate(analysis)
        data = json.loads(artifact.content)
        assert data["report_metadata"]["generated_at"] == (
            "2026-09-18T22:00:00Z"
        )

    def test_recommendations_combined(self) -> None:
        finding = _make_finding()
        analysis = _make_analysis(
            ai_review=_make_ai_success(),
            findings=(finding,),
        )
        artifact = JSONReportGenerator().generate(analysis)
        data = json.loads(artifact.content)
        recs = data["recommendations"]["items"]
        sources = {r["source"] for r in recs}
        assert "ai" in sources
        assert "finding" in sources


# ===================================================
# Markdown Report
# ===================================================


class TestMarkdownReport:
    """Tests for MarkdownReportGenerator."""

    def test_format_name(self) -> None:
        gen = MarkdownReportGenerator()
        assert gen.format_name == "markdown"

    def test_generates_markdown(self) -> None:
        analysis = _make_analysis()
        artifact = MarkdownReportGenerator().generate(analysis)
        assert artifact.format == "markdown"
        assert artifact.filename == "repo_report.md"
        assert "# Repository Analysis:" in artifact.content

    def test_contains_section_headings(self) -> None:
        analysis = _make_analysis(
            ai_review=_make_ai_success(),
        )
        artifact = MarkdownReportGenerator().generate(analysis)
        expected_headings = [
            "## Executive Summary",
            "## Repository Overview",
            "## Technology Stack",
            "## Project Structure",
            "## Architecture Analysis",
            "## Code Quality",
            "## Testing",
            "## Git Health",
            "## Documentation",
            "## Dependencies",
            "## Findings",
            "## AI Engineering Review",
            "## Recommendations",
            "## Analysis Metadata",
        ]
        for heading in expected_headings:
            assert heading in artifact.content, (
                f"Missing: {heading}"
            )

    def test_missing_ai_review(self) -> None:
        analysis = _make_analysis(ai_review=None)
        artifact = MarkdownReportGenerator().generate(analysis)
        assert "not requested" in artifact.content

    def test_ai_review_failure(self) -> None:
        analysis = _make_analysis(
            ai_review=_make_ai_failure(),
        )
        artifact = MarkdownReportGenerator().generate(analysis)
        assert "unavailable" in artifact.content

    def test_findings_rendered(self) -> None:
        finding = _make_finding()
        analysis = _make_analysis(findings=(finding,))
        artifact = MarkdownReportGenerator().generate(analysis)
        assert "NO_README" in artifact.content
        assert "No README found" in artifact.content

    def test_empty_findings(self) -> None:
        analysis = _make_analysis()
        artifact = MarkdownReportGenerator().generate(analysis)
        assert "No findings" in artifact.content

    def test_deterministic(self) -> None:
        analysis = _make_analysis(
            ai_review=_make_ai_success(),
        )
        gen = MarkdownReportGenerator()
        a1 = gen.generate(analysis)
        a2 = gen.generate(analysis)
        assert a1.content == a2.content


# ===================================================
# HTML Report
# ===================================================


class TestHTMLReport:
    """Tests for HTMLReportGenerator."""

    def test_format_name(self) -> None:
        gen = HTMLReportGenerator()
        assert gen.format_name == "html"

    def test_generates_html(self) -> None:
        analysis = _make_analysis()
        artifact = HTMLReportGenerator().generate(analysis)
        assert artifact.format == "html"
        assert artifact.filename == "repo_report.html"
        assert "<!DOCTYPE html>" in artifact.content
        assert "<html" in artifact.content

    def test_contains_section_headings(self) -> None:
        analysis = _make_analysis(
            ai_review=_make_ai_success(),
        )
        artifact = HTMLReportGenerator().generate(analysis)
        expected_h2 = [
            "Executive Summary",
            "Repository Overview",
            "Technology Stack",
            "Project Structure",
            "Code Quality",
            "Testing",
            "Git Health",
            "Documentation",
            "Dependencies",
            "Findings",
            "AI Engineering Review",
            "Recommendations",
            "Analysis Metadata",
        ]
        for heading in expected_h2:
            assert heading in artifact.content, (
                f"Missing: {heading}"
            )

    def test_missing_ai_review(self) -> None:
        analysis = _make_analysis(ai_review=None)
        artifact = HTMLReportGenerator().generate(analysis)
        assert "not requested" in artifact.content

    def test_ai_review_failure(self) -> None:
        analysis = _make_analysis(
            ai_review=_make_ai_failure(),
        )
        artifact = HTMLReportGenerator().generate(analysis)
        assert "unavailable" in artifact.content

    def test_findings_rendered(self) -> None:
        finding = _make_finding()
        analysis = _make_analysis(findings=(finding,))
        artifact = HTMLReportGenerator().generate(analysis)
        assert "NO_README" in artifact.content
        assert "No README found" in artifact.content

    def test_empty_findings(self) -> None:
        analysis = _make_analysis()
        artifact = HTMLReportGenerator().generate(analysis)
        assert "No findings" in artifact.content

    def test_html_escapes_untrusted_data(self) -> None:
        """Repository-derived text must be HTML-escaped."""
        snapshot = RepositorySnapshot(
            repository_info=RepositoryInfo(
                "<script>alert('xss')</script>",
                "repo",
                "https://github.com/owner/repo",
                "https://github.com/owner/repo.git",
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
        analysis = AnalysisResult(
            snapshot=snapshot,
            pipeline_result=PipelineResult(
                results=(), is_successful=True,
            ),
            findings_result=FindingsResult(findings=()),
            ai_review_result=None,
            timestamp="2026-01-01T00:00:00Z",
        )
        artifact = HTMLReportGenerator().generate(analysis)
        assert "<script>" not in artifact.content
        assert "&lt;script&gt;" in artifact.content

    def test_deterministic(self) -> None:
        analysis = _make_analysis(
            ai_review=_make_ai_success(),
        )
        gen = HTMLReportGenerator()
        a1 = gen.generate(analysis)
        a2 = gen.generate(analysis)
        assert a1.content == a2.content

    def test_embedded_css(self) -> None:
        analysis = _make_analysis()
        artifact = HTMLReportGenerator().generate(analysis)
        assert "<style>" in artifact.content

    def test_severity_badges(self) -> None:
        finding = _make_finding()
        analysis = _make_analysis(findings=(finding,))
        artifact = HTMLReportGenerator().generate(analysis)
        assert 'class="badge"' in artifact.content

    def test_evidence_in_sections(self) -> None:
        analysis = _make_analysis(evidence=(
            ObservedFact(
                "repository_health", "README detected",
            ),
            MeasuredMetric(
                "repository_health", "total_files", 5,
            ),
        ))
        artifact = HTMLReportGenerator().generate(analysis)
        # README fact appears in the Documentation section
        assert "README detected" in artifact.content
        # Metric appears in evidence count in metadata
        assert "Total evidence:</strong> 2" in artifact.content
