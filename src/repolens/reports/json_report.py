"""RepoLens AI — JSON Report Generator.

Produces a structured JSON report from AnalysisResult.
Side-effect free: returns ReportArtifact without writing files.
"""

import json

from repolens.domain.analysis import AnalysisResult
from repolens.domain.evidence import MeasuredMetric, ObservedFact
from repolens.domain.report import ReportArtifact


class JSONReportGenerator:
    """Generates a structured JSON report."""

    @property
    def format_name(self) -> str:
        return "json"

    def generate(self, analysis: AnalysisResult) -> ReportArtifact:
        """Generate a JSON report from the analysis result."""
        report = self._build_report_dict(analysis)
        content = json.dumps(report, indent=2, ensure_ascii=False)
        repo_name = analysis.snapshot.repository_info.name
        return ReportArtifact(
            format="json",
            content=content,
            filename=f"{repo_name}_report.json",
        )

    def _build_report_dict(
        self,
        analysis: AnalysisResult,
    ) -> dict:
        """Build the complete report dictionary."""
        snap = analysis.snapshot
        info = snap.repository_info

        return {
            "report_metadata": {
                "generated_at": analysis.timestamp,
                "format_version": "1.0",
                "repository": info.full_name,
            },
            "executive_summary": self._executive_summary(analysis),
            "repository_overview": {
                "owner": info.owner,
                "name": info.name,
                "url": info.url,
                "source_type": info.source_type,
            },
            "technology_stack": {
                "languages": [
                    {"language": lang, "file_count": count}
                    for lang, count in snap.language_counts
                ],
            },
            "project_structure": {
                "total_files": snap.total_files,
                "total_directories": snap.total_directories,
                "total_size_bytes": snap.total_size_bytes,
                "classifications": [
                    {"classification": cls.value, "count": count}
                    for cls, count in snap.classification_counts
                ],
                "extensions": [
                    {"extension": ext, "count": count}
                    for ext, count in snap.extension_counts
                ],
            },
            "project_metadata": self._project_metadata(snap),
            "code_quality": self._evidence_section(
                analysis, "code_quality",
            ),
            "testing": self._evidence_section(
                analysis, "testing_intelligence",
            ),
            "repository_health": self._evidence_section(
                analysis, "repository_health",
            ),
            "git_health": {"status": "not_available"},
            "documentation": self._documentation_section(analysis),
            "dependencies": {"status": "not_available"},
            "architecture": {"status": "not_available"},
            "findings": self._findings_section(analysis),
            "ai_engineering_review": self._ai_review_section(
                analysis,
            ),
            "recommendations": self._recommendations_section(
                analysis,
            ),
        }

    @staticmethod
    def _executive_summary(analysis: AnalysisResult) -> dict:
        ai = analysis.ai_review_result
        if ai and ai.is_successful and ai.review:
            return {
                "source": "ai",
                "text": ai.review.executive_summary,
            }
        total = analysis.findings_result.total_findings
        return {
            "source": "deterministic",
            "text": (
                f"Analysis of {analysis.snapshot.repository_info.full_name} "
                f"completed with {total} finding(s)."
            ),
        }

    @staticmethod
    def _project_metadata(snap) -> dict:
        if snap.project_metadata:
            return {
                "name": snap.project_metadata.name,
                "version": snap.project_metadata.version,
            }
        return {"status": "not_detected"}

    @staticmethod
    def _evidence_section(
        analysis: AnalysisResult,
        analyzer_id: str,
    ) -> dict:
        result = analysis.pipeline_result.get_result(analyzer_id)
        if result is None:
            return {"status": "not_available"}
        items = []
        for e in result.evidence:
            if isinstance(e, ObservedFact):
                items.append({
                    "type": "fact",
                    "description": e.description,
                    "location": e.location,
                })
            elif isinstance(e, MeasuredMetric):
                items.append({
                    "type": "metric",
                    "name": e.name,
                    "value": e.value,
                    "location": e.location,
                })
        return {
            "status": result.status.value,
            "evidence": items,
        }

    @staticmethod
    def _documentation_section(analysis: AnalysisResult) -> dict:
        result = analysis.pipeline_result.get_result(
            "repository_health",
        )
        if result is None:
            return {"status": "not_available"}
        items = []
        for e in result.evidence:
            if isinstance(e, ObservedFact) and (
                "README" in e.description
                or "documentation" in e.description.lower()
            ):
                items.append({"description": e.description})
        return {"evidence": items} if items else {
            "status": "no_documentation_evidence",
        }

    @staticmethod
    def _findings_section(analysis: AnalysisResult) -> dict:
        findings = analysis.findings_result.findings
        return {
            "total": len(findings),
            "items": [
                {
                    "finding_id": f.finding_id,
                    "rule_id": f.rule_id,
                    "category": f.category.value,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "source_analyzer": f.source_analyzer,
                }
                for f in findings
            ],
        }

    @staticmethod
    def _ai_review_section(analysis: AnalysisResult) -> dict:
        ai = analysis.ai_review_result
        if ai is None:
            return {"status": "not_requested"}
        if not ai.is_successful or ai.review is None:
            return {
                "status": "unavailable",
                "error": ai.error,
            }
        review = ai.review
        return {
            "status": "available",
            "provider_model": review.provider_model,
            "executive_summary": review.executive_summary,
            "strengths": list(review.strengths),
            "concerns": list(review.concerns),
            "recommendations": list(review.recommendations),
            "overall_assessment": review.overall_assessment,
        }

    @staticmethod
    def _recommendations_section(
        analysis: AnalysisResult,
    ) -> dict:
        recs: list[dict] = []
        # AI recommendations
        ai = analysis.ai_review_result
        if ai and ai.is_successful and ai.review:
            for r in ai.review.recommendations:
                recs.append({"source": "ai", "text": r})
        # Findings recommendations
        for f in analysis.findings_result.findings:
            if f.recommendation:
                recs.append({
                    "source": "finding",
                    "rule_id": f.rule_id,
                    "text": f.recommendation,
                })
        return {"items": recs}
