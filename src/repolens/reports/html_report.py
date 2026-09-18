"""RepoLens AI — HTML Report Generator.

Produces a self-contained HTML report with embedded CSS from AnalysisResult.
Side-effect free: returns ReportArtifact without writing files.
No external template engine (Jinja2). Pure Python string composition.
"""

import html

from repolens.domain.analysis import AnalysisResult
from repolens.domain.evidence import MeasuredMetric, ObservedFact
from repolens.domain.report import ReportArtifact

# Severity → badge color mapping
_SEVERITY_COLORS = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#d97706",
    "low": "#2563eb",
    "info": "#6b7280",
}

_CSS = """\
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, sans-serif;
    line-height: 1.6; color: #1f2937; background: #f9fafb;
}
.container { max-width: 960px; margin: 0 auto; padding: 2rem; }
h1 { font-size: 1.8rem; margin-bottom: 0.5rem; color: #111827; }
h2 {
    font-size: 1.3rem; margin: 2rem 0 0.75rem; padding-bottom: 0.5rem;
    border-bottom: 2px solid #e5e7eb; color: #374151;
}
h3 { font-size: 1.1rem; margin: 1rem 0 0.5rem; color: #4b5563; }
p, li { margin-bottom: 0.5rem; }
ul { padding-left: 1.5rem; }
table {
    width: 100%; border-collapse: collapse; margin: 0.75rem 0;
}
th, td {
    text-align: left; padding: 0.5rem 0.75rem;
    border-bottom: 1px solid #e5e7eb;
}
th { background: #f3f4f6; font-weight: 600; font-size: 0.9rem; }
.badge {
    display: inline-block; padding: 0.15rem 0.5rem;
    border-radius: 0.25rem; color: #fff; font-size: 0.8rem;
    font-weight: 600; text-transform: uppercase;
}
.summary-box {
    background: #eff6ff; border-left: 4px solid #3b82f6;
    padding: 1rem; margin: 1rem 0; border-radius: 0 0.25rem 0.25rem 0;
}
.finding-card {
    background: #fff; border: 1px solid #e5e7eb;
    border-radius: 0.5rem; padding: 1rem; margin: 0.75rem 0;
}
.meta { color: #6b7280; font-size: 0.85rem; }
.footer {
    margin-top: 3rem; padding-top: 1rem;
    border-top: 1px solid #e5e7eb; color: #9ca3af;
    font-size: 0.8rem;
}
"""


def _esc(text: str) -> str:
    """Escape text for safe HTML embedding."""
    return html.escape(str(text))


class HTMLReportGenerator:
    """Generates a self-contained HTML report with embedded CSS."""

    @property
    def format_name(self) -> str:
        return "html"

    def generate(self, analysis: AnalysisResult) -> ReportArtifact:
        """Generate an HTML report from the analysis result."""
        snap = analysis.snapshot
        info = snap.repository_info

        body_parts: list[str] = []
        body_parts.append(
            f"<h1>Repository Analysis: {_esc(info.full_name)}</h1>"
        )

        body_parts.append(self._executive_summary(analysis))
        body_parts.append(self._repository_overview(analysis))
        body_parts.append(self._technology_stack(analysis))
        body_parts.append(self._project_structure(analysis))
        body_parts.append(
            '<h2>Architecture Analysis</h2>'
            '<p class="meta">Architecture analysis '
            "not yet available.</p>"
        )
        body_parts.append(self._evidence_section(
            analysis, "code_quality", "Code Quality",
        ))
        body_parts.append(self._evidence_section(
            analysis, "testing_intelligence", "Testing",
        ))
        body_parts.append(
            '<h2>Git Health</h2>'
            '<p class="meta">Git health analysis '
            "not yet available.</p>"
        )
        body_parts.append(self._documentation(analysis))
        body_parts.append(
            '<h2>Dependencies</h2>'
            '<p class="meta">Dependency analysis '
            "not yet available.</p>"
        )
        body_parts.append(self._findings(analysis))
        body_parts.append(self._ai_review(analysis))
        body_parts.append(self._recommendations(analysis))
        body_parts.append(self._metadata(analysis))

        body = "\n".join(body_parts)

        page = (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n<head>\n'
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" '
            'content="width=device-width, initial-scale=1.0">\n'
            f"<title>Analysis: {_esc(info.full_name)}</title>\n"
            f"<style>{_CSS}</style>\n"
            "</head>\n<body>\n"
            f'<div class="container">\n{body}\n</div>\n'
            "</body>\n</html>"
        )

        return ReportArtifact(
            format="html",
            content=page,
            filename=f"{info.name}_report.html",
        )

    # --- Section builders ---

    @staticmethod
    def _executive_summary(analysis: AnalysisResult) -> str:
        ai = analysis.ai_review_result
        if ai and ai.is_successful and ai.review:
            text = _esc(ai.review.executive_summary)
        else:
            total = analysis.findings_result.total_findings
            name = _esc(
                analysis.snapshot.repository_info.full_name
            )
            text = (
                f"Analysis of {name} "
                f"completed with {total} finding(s)."
            )
        return (
            "<h2>Executive Summary</h2>\n"
            f'<div class="summary-box"><p>{text}</p></div>'
        )

    @staticmethod
    def _repository_overview(analysis: AnalysisResult) -> str:
        info = analysis.snapshot.repository_info
        return (
            "<h2>Repository Overview</h2>\n<ul>\n"
            f"<li><strong>Owner:</strong> {_esc(info.owner)}</li>\n"
            f"<li><strong>Name:</strong> {_esc(info.name)}</li>\n"
            f"<li><strong>URL:</strong> {_esc(info.url)}</li>\n"
            f"<li><strong>Source:</strong> "
            f"{_esc(info.source_type)}</li>\n"
            "</ul>"
        )

    @staticmethod
    def _technology_stack(analysis: AnalysisResult) -> str:
        snap = analysis.snapshot
        parts = ["<h2>Technology Stack</h2>\n"]
        if snap.language_counts:
            parts.append("<table>\n<tr><th>Language</th>"
                         "<th>Files</th></tr>\n")
            for lang, count in snap.language_counts:
                parts.append(
                    f"<tr><td>{_esc(lang)}</td>"
                    f"<td>{count}</td></tr>\n"
                )
            parts.append("</table>")
        else:
            parts.append(
                '<p class="meta">No language data available.</p>'
            )
        return "".join(parts)

    @staticmethod
    def _project_structure(analysis: AnalysisResult) -> str:
        snap = analysis.snapshot
        parts = [
            "<h2>Project Structure</h2>\n<ul>\n",
            f"<li><strong>Total files:</strong> "
            f"{snap.total_files}</li>\n",
            f"<li><strong>Total directories:</strong> "
            f"{snap.total_directories}</li>\n",
            f"<li><strong>Total size:</strong> "
            f"{snap.total_size_bytes:,} bytes</li>\n",
            "</ul>\n",
        ]
        if snap.classification_counts:
            parts.append(
                "<table>\n<tr><th>Classification</th>"
                "<th>Count</th></tr>\n"
            )
            for cls, count in snap.classification_counts:
                parts.append(
                    f"<tr><td>{_esc(cls.value)}</td>"
                    f"<td>{count}</td></tr>\n"
                )
            parts.append("</table>")
        return "".join(parts)

    @staticmethod
    def _evidence_section(
        analysis: AnalysisResult,
        analyzer_id: str,
        title: str,
    ) -> str:
        result = analysis.pipeline_result.get_result(analyzer_id)
        parts = [f"<h2>{_esc(title)}</h2>\n"]
        if result is None:
            parts.append(
                f'<p class="meta">{_esc(title)} analysis '
                f"not available.</p>"
            )
            return "".join(parts)
        parts.append("<ul>\n")
        for e in result.evidence:
            if isinstance(e, ObservedFact):
                parts.append(
                    f"<li>{_esc(e.description)}</li>\n"
                )
            elif isinstance(e, MeasuredMetric):
                parts.append(
                    f"<li><strong>{_esc(e.name)}:</strong> "
                    f"{_esc(str(e.value))}</li>\n"
                )
        parts.append("</ul>")
        return "".join(parts)

    @staticmethod
    def _documentation(analysis: AnalysisResult) -> str:
        result = analysis.pipeline_result.get_result(
            "repository_health",
        )
        parts = ["<h2>Documentation</h2>\n"]
        if result is None:
            parts.append(
                '<p class="meta">'
                "Documentation analysis not available.</p>"
            )
            return "".join(parts)
        items: list[str] = []
        for e in result.evidence:
            if isinstance(e, ObservedFact) and (
                "README" in e.description
                or "documentation" in e.description.lower()
            ):
                items.append(
                    f"<li>{_esc(e.description)}</li>"
                )
        if items:
            parts.append("<ul>\n" + "\n".join(items) + "\n</ul>")
        else:
            parts.append(
                '<p class="meta">'
                "No documentation evidence.</p>"
            )
        return "".join(parts)

    @staticmethod
    def _findings(analysis: AnalysisResult) -> str:
        findings = analysis.findings_result.findings
        parts = ["<h2>Findings</h2>\n"]
        if not findings:
            parts.append(
                '<p class="meta">No findings.</p>'
            )
            return "".join(parts)
        for f in findings:
            color = _SEVERITY_COLORS.get(
                f.severity.value, "#6b7280",
            )
            parts.append(
                f'<div class="finding-card">\n'
                f'<h3><span class="badge" '
                f'style="background:{color}">'
                f"{_esc(f.severity.value)}</span> "
                f"{_esc(f.title)}</h3>\n"
                f'<p class="meta">Rule: {_esc(f.rule_id)} '
                f"| Category: {_esc(f.category.value)} "
                f"| Analyzer: {_esc(f.source_analyzer)}</p>\n"
                f"<p>{_esc(f.description)}</p>\n"
            )
            if f.recommendation:
                parts.append(
                    f"<p><strong>Recommendation:</strong> "
                    f"{_esc(f.recommendation)}</p>\n"
                )
            parts.append("</div>\n")
        return "".join(parts)

    @staticmethod
    def _ai_review(analysis: AnalysisResult) -> str:
        parts = ["<h2>AI Engineering Review</h2>\n"]
        ai = analysis.ai_review_result
        if ai is None:
            parts.append(
                '<p class="meta">'
                "AI review was not requested.</p>"
            )
            return "".join(parts)
        if not ai.is_successful or ai.review is None:
            error = _esc(ai.error or "unknown")
            parts.append(
                f'<p class="meta">'
                f"AI review unavailable: {error}</p>"
            )
            return "".join(parts)
        review = ai.review
        parts.append(
            f'<p class="meta">'
            f"Provider: {_esc(review.provider_model)}</p>\n"
        )
        parts.append(
            f"<p><strong>Overall:</strong> "
            f"{_esc(review.overall_assessment)}</p>\n"
        )
        if review.strengths:
            parts.append("<h3>Strengths</h3>\n<ul>\n")
            for s in review.strengths:
                parts.append(f"<li>{_esc(s)}</li>\n")
            parts.append("</ul>\n")
        if review.concerns:
            parts.append("<h3>Concerns</h3>\n<ul>\n")
            for c in review.concerns:
                parts.append(f"<li>{_esc(c)}</li>\n")
            parts.append("</ul>\n")
        return "".join(parts)

    @staticmethod
    def _recommendations(analysis: AnalysisResult) -> str:
        parts = ["<h2>Recommendations</h2>\n"]
        recs: list[str] = []
        ai = analysis.ai_review_result
        if ai and ai.is_successful and ai.review:
            for r in ai.review.recommendations:
                recs.append(f"<li>{_esc(r)}</li>")
        for f in analysis.findings_result.findings:
            if f.recommendation:
                recs.append(
                    f"<li>[{_esc(f.rule_id)}] "
                    f"{_esc(f.recommendation)}</li>"
                )
        if recs:
            parts.append(
                "<ul>\n" + "\n".join(recs) + "\n</ul>"
            )
        else:
            parts.append(
                '<p class="meta">No recommendations.</p>'
            )
        return "".join(parts)

    @staticmethod
    def _metadata(analysis: AnalysisResult) -> str:
        parts = [
            "<h2>Analysis Metadata</h2>\n<ul>\n",
            f"<li><strong>Generated at:</strong> "
            f"{_esc(analysis.timestamp)}</li>\n",
            f"<li><strong>Total evidence:</strong> "
            f"{analysis.pipeline_result.total_evidence}</li>\n",
            f"<li><strong>Total findings:</strong> "
            f"{analysis.findings_result.total_findings}</li>\n",
        ]
        for aid, result in analysis.pipeline_result.results:
            parts.append(
                f"<li><strong>Analyzer "
                f"<code>{_esc(aid)}</code>:</strong> "
                f"{_esc(result.status.value)}</li>\n"
            )
        parts.append("</ul>\n")
        parts.append(
            '<div class="footer">'
            "Generated by RepoLens AI</div>"
        )
        return "".join(parts)
