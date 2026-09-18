"""RepoLens AI — Markdown Report Generator.

Produces a structured Markdown report from AnalysisResult.
Side-effect free: returns ReportArtifact without writing files.
"""

from repolens.domain.analysis import AnalysisResult
from repolens.domain.evidence import MeasuredMetric, ObservedFact
from repolens.domain.report import ReportArtifact


class MarkdownReportGenerator:
    """Generates a structured Markdown report."""

    @property
    def format_name(self) -> str:
        return "markdown"

    def generate(self, analysis: AnalysisResult) -> ReportArtifact:
        """Generate a Markdown report from the analysis result."""
        sections: list[str] = []
        snap = analysis.snapshot
        info = snap.repository_info

        sections.append(f"# Repository Analysis: {info.full_name}\n")

        # 1. Executive Summary
        sections.append("## Executive Summary\n")
        sections.append(self._executive_summary(analysis))

        # 2. Repository Overview
        sections.append("\n## Repository Overview\n")
        sections.append(f"- **Owner:** {info.owner}")
        sections.append(f"- **Name:** {info.name}")
        sections.append(f"- **URL:** {info.url}")
        sections.append(f"- **Source:** {info.source_type}")

        # 3. Technology Stack
        sections.append("\n## Technology Stack\n")
        if snap.language_counts:
            sections.append("| Language | Files |")
            sections.append("|----------|-------|")
            for lang, count in snap.language_counts:
                sections.append(f"| {lang} | {count} |")
        else:
            sections.append("No language data available.")

        # 4. Project Structure
        sections.append("\n## Project Structure\n")
        sections.append(
            f"- **Total files:** {snap.total_files}"
        )
        sections.append(
            f"- **Total directories:** {snap.total_directories}"
        )
        sections.append(
            f"- **Total size:** {snap.total_size_bytes:,} bytes"
        )
        if snap.classification_counts:
            sections.append("\n| Classification | Count |")
            sections.append("|----------------|-------|")
            for cls, count in snap.classification_counts:
                sections.append(f"| {cls.value} | {count} |")

        # 5. Architecture Analysis
        sections.append("\n## Architecture Analysis\n")
        sections.append(
            "*Architecture analysis not yet available.*"
        )

        # 6. Code Quality
        sections.append("\n## Code Quality\n")
        sections.append(
            self._evidence_md(analysis, "code_quality")
        )

        # 7. Testing
        sections.append("\n## Testing\n")
        sections.append(
            self._evidence_md(analysis, "testing_intelligence")
        )

        # 8. Git Health
        sections.append("\n## Git Health\n")
        sections.append("*Git health analysis not yet available.*")

        # 9. Documentation
        sections.append("\n## Documentation\n")
        sections.append(self._documentation_md(analysis))

        # 10. Dependencies
        sections.append("\n## Dependencies\n")
        sections.append(
            "*Dependency analysis not yet available.*"
        )

        # 11. Findings
        sections.append("\n## Findings\n")
        sections.append(self._findings_md(analysis))

        # 12. AI Engineering Review
        sections.append("\n## AI Engineering Review\n")
        sections.append(self._ai_review_md(analysis))

        # 13. Recommendations
        sections.append("\n## Recommendations\n")
        sections.append(self._recommendations_md(analysis))

        # 14. Analysis Metadata
        sections.append("\n## Analysis Metadata\n")
        sections.append(
            f"- **Generated at:** {analysis.timestamp}"
        )
        sections.append(
            f"- **Total evidence:** "
            f"{analysis.pipeline_result.total_evidence}"
        )
        sections.append(
            f"- **Total findings:** "
            f"{analysis.findings_result.total_findings}"
        )
        for aid, result in analysis.pipeline_result.results:
            sections.append(
                f"- **Analyzer `{aid}`:** {result.status.value}"
            )

        content = "\n".join(sections) + "\n"
        repo_name = info.name
        return ReportArtifact(
            format="markdown",
            content=content,
            filename=f"{repo_name}_report.md",
        )

    @staticmethod
    def _executive_summary(analysis: AnalysisResult) -> str:
        ai = analysis.ai_review_result
        if ai and ai.is_successful and ai.review:
            return ai.review.executive_summary
        total = analysis.findings_result.total_findings
        return (
            f"Analysis of {analysis.snapshot.repository_info.full_name} "
            f"completed with {total} finding(s)."
        )

    @staticmethod
    def _evidence_md(
        analysis: AnalysisResult,
        analyzer_id: str,
    ) -> str:
        result = analysis.pipeline_result.get_result(analyzer_id)
        if result is None:
            return f"*{analyzer_id} analysis not available.*"
        lines: list[str] = []
        for e in result.evidence:
            if isinstance(e, ObservedFact):
                lines.append(f"- {e.description}")
            elif isinstance(e, MeasuredMetric):
                lines.append(f"- **{e.name}:** {e.value}")
        return "\n".join(lines) if lines else "No evidence."

    @staticmethod
    def _documentation_md(analysis: AnalysisResult) -> str:
        result = analysis.pipeline_result.get_result(
            "repository_health",
        )
        if result is None:
            return "*Documentation analysis not available.*"
        lines: list[str] = []
        for e in result.evidence:
            if isinstance(e, ObservedFact) and (
                "README" in e.description
                or "documentation" in e.description.lower()
            ):
                lines.append(f"- {e.description}")
        return (
            "\n".join(lines) if lines
            else "No documentation evidence."
        )

    @staticmethod
    def _findings_md(analysis: AnalysisResult) -> str:
        findings = analysis.findings_result.findings
        if not findings:
            return "No findings."
        lines: list[str] = []
        for f in findings:
            lines.append(
                f"### [{f.severity.value.upper()}] {f.title}\n"
            )
            lines.append(f"- **Rule:** `{f.rule_id}`")
            lines.append(f"- **Category:** {f.category.value}")
            lines.append(f"- **Description:** {f.description}")
            if f.recommendation:
                lines.append(
                    f"- **Recommendation:** {f.recommendation}"
                )
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _ai_review_md(analysis: AnalysisResult) -> str:
        ai = analysis.ai_review_result
        if ai is None:
            return "*AI review was not requested.*"
        if not ai.is_successful or ai.review is None:
            return (
                f"*AI review unavailable: {ai.error or 'unknown'}*"
            )
        review = ai.review
        lines: list[str] = [
            f"**Provider:** {review.provider_model}\n",
            f"**Overall:** {review.overall_assessment}\n",
        ]
        if review.strengths:
            lines.append("**Strengths:**\n")
            for s in review.strengths:
                lines.append(f"- {s}")
            lines.append("")
        if review.concerns:
            lines.append("**Concerns:**\n")
            for c in review.concerns:
                lines.append(f"- {c}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _recommendations_md(analysis: AnalysisResult) -> str:
        recs: list[str] = []
        ai = analysis.ai_review_result
        if ai and ai.is_successful and ai.review:
            for r in ai.review.recommendations:
                recs.append(f"- {r}")
        for f in analysis.findings_result.findings:
            if f.recommendation:
                recs.append(
                    f"- [{f.rule_id}] {f.recommendation}"
                )
        return "\n".join(recs) if recs else "No recommendations."
