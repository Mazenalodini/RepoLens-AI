"""RepoLens AI — Report generation.

Transforms analysis results into HTML, JSON, and Markdown reports.
Report generation does not re-run analysis.
"""

from repolens.reports.html_report import HTMLReportGenerator
from repolens.reports.json_report import JSONReportGenerator
from repolens.reports.markdown_report import MarkdownReportGenerator

__all__ = [
    "HTMLReportGenerator",
    "JSONReportGenerator",
    "MarkdownReportGenerator",
]
