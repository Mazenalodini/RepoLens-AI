"""RepoLens AI — Server-Rendered Dashboard.

Minimal HTML dashboard served by FastAPI. Uses pure Python string
composition — no template engine dependency. Same-origin API access.
"""

import html
import json
import logging

from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from repolens.api.dependencies import get_analysis_service
from repolens.application.analysis_service import AnalysisService
from repolens.domain.exceptions import RepoLensError

logger = logging.getLogger(__name__)

dashboard_router = APIRouter()

_CSS = """\
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, sans-serif;
    line-height: 1.6; color: #1f2937; background: #f1f5f9;
}
.container { max-width: 960px; margin: 0 auto; padding: 2rem; }
header {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    color: white; padding: 1.5rem 2rem;
}
header h1 { font-size: 1.5rem; font-weight: 600; }
header p { color: #94a3b8; font-size: 0.875rem; margin-top: 0.25rem; }
nav { margin-top: 0.75rem; }
nav a {
    color: #93c5fd; text-decoration: none; margin-right: 1.5rem;
    font-size: 0.875rem;
}
nav a:hover { color: #bfdbfe; }
.card {
    background: white; border-radius: 8px; padding: 1.5rem;
    margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.card h2 {
    font-size: 1.15rem; margin-bottom: 1rem;
    padding-bottom: 0.5rem; border-bottom: 2px solid #e2e8f0;
    color: #334155;
}
h3 { font-size: 1rem; margin: 1rem 0 0.5rem; color: #475569; }
input[type="text"] {
    width: 100%; padding: 0.625rem 0.75rem; border: 1px solid #cbd5e1;
    border-radius: 6px; font-size: 0.95rem; margin-bottom: 0.75rem;
}
input[type="text"]:focus {
    outline: none; border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
}
button, .btn {
    display: inline-block; padding: 0.625rem 1.25rem;
    background: #2563eb; color: white; border: none;
    border-radius: 6px; font-size: 0.875rem; cursor: pointer;
    text-decoration: none; font-weight: 500;
}
button:hover, .btn:hover { background: #1d4ed8; }
.btn-sm { padding: 0.375rem 0.75rem; font-size: 0.8rem; }
.btn-outline {
    background: transparent; color: #2563eb;
    border: 1px solid #2563eb;
}
.btn-outline:hover { background: #eff6ff; }
table { width: 100%; border-collapse: collapse; margin: 0.5rem 0; }
th, td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
th { font-size: 0.8rem; color: #64748b; text-transform: uppercase; font-weight: 600; }
td { font-size: 0.875rem; }
.badge {
    display: inline-block; padding: 0.15rem 0.5rem;
    border-radius: 9999px; font-size: 0.75rem; font-weight: 600;
}
.badge-completed { background: #dcfce7; color: #166534; }
.badge-failed { background: #fee2e2; color: #991b1b; }
.badge-running { background: #fef3c7; color: #92400e; }
.severity-critical { background: #fee2e2; color: #991b1b; }
.severity-high { background: #ffedd5; color: #9a3412; }
.severity-medium { background: #fef3c7; color: #92400e; }
.severity-low { background: #dbeafe; color: #1e40af; }
.severity-info { background: #f1f5f9; color: #475569; }
.empty-state { text-align: center; padding: 2rem; color: #94a3b8; }
.error-box {
    background: #fee2e2; border: 1px solid #fca5a5;
    border-radius: 6px; padding: 1rem; margin-bottom: 1rem;
    color: #991b1b; font-size: 0.875rem;
}
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.detail-item label { display: block; font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 600; }
.detail-item span { font-size: 1rem; color: #1e293b; }
.ai-section { background: #f0f9ff; border-radius: 8px; padding: 1rem; margin-top: 0.75rem; }
.ai-section h3 { color: #0369a1; }
ul { padding-left: 1.5rem; }
li { margin-bottom: 0.35rem; font-size: 0.875rem; }
.report-frame { width: 100%; border: 1px solid #e2e8f0; border-radius: 6px; min-height: 400px; }
footer { text-align: center; padding: 1rem; color: #94a3b8; font-size: 0.8rem; }
"""


def _layout(title: str, content: str) -> str:
    """Wrap content in the standard dashboard layout."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — RepoLens AI</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>RepoLens AI</h1>
  <p>AI-Powered Repository Intelligence</p>
  <nav>
    <a href="/">Dashboard</a>
    <a href="/api/v1/health">API Health</a>
  </nav>
</header>
<div class="container">
{content}
</div>
<footer>RepoLens AI v0.1.0 — Evidence First, AI-Assisted</footer>
</body>
</html>"""


@dashboard_router.get("/", response_class=HTMLResponse)
async def dashboard_home(
    service: AnalysisService = Depends(get_analysis_service),
) -> HTMLResponse:
    """Dashboard home page: new analysis form + recent analyses."""
    records = service.list_analyses(limit=20)

    # New analysis form
    form = """\
<div class="card">
  <h2>New Analysis</h2>
  <form method="POST" action="/dashboard/analyze">
    <input type="text" name="repository_url"
           placeholder="https://github.com/owner/repository"
           required>
    <button type="submit">Analyze Repository</button>
  </form>
</div>"""

    # Recent analyses table
    if records:
        rows = ""
        for r in records:
            badge_cls = f"badge-{r.status}"
            name = html.escape(f"{r.repository_owner}/{r.repository_name}")
            rows += f"""\
<tr>
  <td><a href="/dashboard/analyses/{html.escape(r.id)}">{name}</a></td>
  <td><span class="badge {badge_cls}">{html.escape(r.status)}</span></td>
  <td>{r.total_findings}</td>
  <td>{'Yes' if r.ai_review_json else 'No'}</td>
  <td>{html.escape(r.created_at[:19])}</td>
</tr>"""

        table = f"""\
<div class="card">
  <h2>Recent Analyses</h2>
  <table>
    <thead>
      <tr><th>Repository</th><th>Status</th><th>Findings</th><th>AI Review</th><th>Created</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""
    else:
        table = """\
<div class="card">
  <h2>Recent Analyses</h2>
  <div class="empty-state">No analyses yet. Start one above!</div>
</div>"""

    return HTMLResponse(_layout("Dashboard", form + table))


@dashboard_router.post(
    "/dashboard/analyze", response_class=HTMLResponse, response_model=None
)
async def dashboard_submit_analysis(
    repository_url: str = Form(...),
    service: AnalysisService = Depends(get_analysis_service),
) -> HTMLResponse:
    """Handle analysis form submission."""
    try:
        analysis_id = service.analyze(
            repository_url=repository_url,
            include_ai_review=True,
        )
        return RedirectResponse(
            url=f"/dashboard/analyses/{analysis_id}",
            status_code=303,
        )
    except RepoLensError as exc:
        error_html = f"""\
<div class="error-box">Analysis failed: {html.escape(str(exc))}</div>
<a class="btn btn-outline" href="/">← Back to Dashboard</a>"""
        return HTMLResponse(_layout("Error", error_html))


@dashboard_router.get(
    "/dashboard/analyses/{analysis_id}",
    response_class=HTMLResponse,
)
async def dashboard_analysis_detail(
    analysis_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> HTMLResponse:
    """Analysis detail page."""
    record = service.get_analysis(analysis_id)
    if record is None:
        return HTMLResponse(
            _layout("Not Found", '<div class="card"><p>Analysis not found.</p></div>'),
            status_code=404,
        )

    badge_cls = f"badge-{record.status}"
    name = html.escape(f"{record.repository_owner}/{record.repository_name}")

    # Details grid
    details = f"""\
<div class="card">
  <h2>{name} <span class="badge {badge_cls}">{html.escape(record.status)}</span></h2>
  <div class="detail-grid">
    <div class="detail-item">
      <label>Analysis ID</label>
      <span>{html.escape(record.id)}</span>
    </div>
    <div class="detail-item">
      <label>Repository URL</label>
      <span><a href="{html.escape(record.repository_url)}" target="_blank">{html.escape(record.repository_url)}</a></span>
    </div>
    <div class="detail-item">
      <label>Files</label>
      <span>{record.total_files:,}</span>
    </div>
    <div class="detail-item">
      <label>Size</label>
      <span>{record.total_size_bytes:,} bytes</span>
    </div>
    <div class="detail-item">
      <label>Evidence</label>
      <span>{record.total_evidence}</span>
    </div>
    <div class="detail-item">
      <label>Findings</label>
      <span>{record.total_findings}</span>
    </div>
    <div class="detail-item">
      <label>Created</label>
      <span>{html.escape(record.created_at[:19])}</span>
    </div>
    <div class="detail-item">
      <label>Completed</label>
      <span>{html.escape(record.completed_at[:19]) if record.completed_at else '—'}</span>
    </div>
  </div>"""

    if record.error_message:
        details += f"""\
  <div class="error-box" style="margin-top:1rem">
    {html.escape(record.error_message)}
  </div>"""

    details += "</div>"

    # AI Review section
    ai_section = ""
    if record.ai_review_json:
        try:
            review = json.loads(record.ai_review_json)
            strengths = "".join(
                f"<li>{html.escape(s)}</li>" for s in review.get("strengths", [])
            )
            concerns = "".join(
                f"<li>{html.escape(c)}</li>" for c in review.get("concerns", [])
            )
            recs = "".join(
                f"<li>{html.escape(r)}</li>"
                for r in review.get("recommendations", [])
            )
            ai_section = f"""\
<div class="card">
  <h2>AI Engineering Review</h2>
  <div class="ai-section">
    <h3>Executive Summary</h3>
    <p>{html.escape(review.get('executive_summary', ''))}</p>
    <h3>Strengths</h3>
    <ul>{strengths or '<li>None identified</li>'}</ul>
    <h3>Concerns</h3>
    <ul>{concerns or '<li>None identified</li>'}</ul>
    <h3>Recommendations</h3>
    <ul>{recs or '<li>None</li>'}</ul>
    <h3>Overall Assessment</h3>
    <p>{html.escape(review.get('overall_assessment', ''))}</p>
    <p style="margin-top:0.5rem;font-size:0.8rem;color:#64748b;">
      Model: {html.escape(review.get('provider_model', 'unknown'))}
    </p>
  </div>
</div>"""
        except (json.JSONDecodeError, TypeError):
            ai_section = ""
    else:
        ai_section = """\
<div class="card">
  <h2>AI Engineering Review</h2>
  <div class="empty-state">AI review not available for this analysis.</div>
</div>"""

    # Navigation links
    nav = f"""\
<div class="card">
  <a class="btn btn-sm" href="/dashboard/analyses/{html.escape(analysis_id)}/findings">View Findings</a>
  <a class="btn btn-sm btn-outline" href="/dashboard/analyses/{html.escape(analysis_id)}/report">View Report</a>
  <a class="btn btn-sm btn-outline" href="/">← Dashboard</a>
</div>"""

    return HTMLResponse(
        _layout(name, details + ai_section + nav)
    )


@dashboard_router.get(
    "/dashboard/analyses/{analysis_id}/findings",
    response_class=HTMLResponse,
)
async def dashboard_findings(
    analysis_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> HTMLResponse:
    """Findings page for an analysis."""
    record = service.get_analysis(analysis_id)
    if record is None:
        return HTMLResponse(
            _layout("Not Found", '<div class="card"><p>Analysis not found.</p></div>'),
            status_code=404,
        )

    name = html.escape(f"{record.repository_owner}/{record.repository_name}")

    if record.findings_json:
        try:
            findings = json.loads(record.findings_json)
        except (json.JSONDecodeError, TypeError):
            findings = []
    else:
        findings = []

    if findings:
        rows = ""
        for f in findings:
            sev = f.get("severity", "info")
            sev_cls = f"severity-{sev}"
            rows += f"""\
<tr>
  <td><span class="badge {sev_cls}">{html.escape(sev.upper())}</span></td>
  <td>{html.escape(f.get('category', ''))}</td>
  <td><strong>{html.escape(f.get('title', ''))}</strong><br>
      <span style="font-size:0.8rem;color:#64748b">{html.escape(f.get('description', ''))}</span></td>
  <td style="font-size:0.8rem">{html.escape(f.get('recommendation', '') or '—')}</td>
</tr>"""

        table = f"""\
<div class="card">
  <h2>Findings for {name} ({len(findings)} total)</h2>
  <table>
    <thead><tr><th>Severity</th><th>Category</th><th>Finding</th><th>Recommendation</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""
    else:
        table = f"""\
<div class="card">
  <h2>Findings for {name}</h2>
  <div class="empty-state">No findings recorded.</div>
</div>"""

    nav = f"""\
<a class="btn btn-sm btn-outline" href="/dashboard/analyses/{html.escape(analysis_id)}">← Back to Analysis</a>"""

    return HTMLResponse(_layout(f"Findings — {name}", table + nav))


@dashboard_router.get(
    "/dashboard/analyses/{analysis_id}/report",
    response_class=HTMLResponse,
)
async def dashboard_report(
    analysis_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> HTMLResponse:
    """Report viewer page — embeds the HTML report in an iframe."""
    record = service.get_analysis(analysis_id)
    if record is None:
        return HTMLResponse(
            _layout("Not Found", '<div class="card"><p>Analysis not found.</p></div>'),
            status_code=404,
        )

    name = html.escape(f"{record.repository_owner}/{record.repository_name}")

    if record.report_html:
        # Serve the report via an API endpoint; embed in iframe
        content = f"""\
<div class="card">
  <h2>Report for {name}</h2>
  <p style="margin-bottom:0.75rem">
    <a class="btn btn-sm" href="/api/v1/analyses/{html.escape(analysis_id)}/report?format=html" target="_blank">Open Full Report</a>
    <a class="btn btn-sm btn-outline" href="/api/v1/analyses/{html.escape(analysis_id)}/report?format=json" target="_blank">JSON</a>
    <a class="btn btn-sm btn-outline" href="/api/v1/analyses/{html.escape(analysis_id)}/report?format=markdown" target="_blank">Markdown</a>
  </p>
</div>"""
    else:
        content = f"""\
<div class="card">
  <h2>Report for {name}</h2>
  <div class="empty-state">Report not available.</div>
</div>"""

    nav = f"""\
<a class="btn btn-sm btn-outline" href="/dashboard/analyses/{html.escape(analysis_id)}">← Back to Analysis</a>"""

    return HTMLResponse(_layout(f"Report — {name}", content + nav))
