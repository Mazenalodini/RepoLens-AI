"""RepoLens AI — API Route Handlers.

Thin HTTP handlers that validate input, delegate to AnalysisService,
and serialize responses. No analysis logic lives here.
"""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from repolens.api.dependencies import get_analysis_service
from repolens.api.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    ErrorResponse,
    FindingItem,
    FindingsResponse,
    HealthResponse,
    ReportResponse,
)
from repolens.application.analysis_service import AnalysisService
from repolens.domain.exceptions import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

_VALID_REPORT_FORMATS = frozenset({"html", "json", "markdown"})


def _record_to_response(record) -> AnalysisResponse:
    """Convert an AnalysisRecord to an AnalysisResponse."""
    return AnalysisResponse(
        analysis_id=record.id,
        repository_name=f"{record.repository_owner}/{record.repository_name}",
        repository_url=record.repository_url,
        status=record.status,
        created_at=record.created_at,
        completed_at=record.completed_at,
        total_files=record.total_files,
        total_directories=record.total_directories,
        total_size_bytes=record.total_size_bytes,
        total_evidence=record.total_evidence,
        total_findings=record.total_findings,
        ai_review_available=record.ai_review_json is not None,
        error_message=record.error_message,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse()


@router.post(
    "/analyses",
    response_model=AnalysisResponse,
    responses={422: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
async def create_analysis(
    request: AnalysisRequest,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    """Start a new repository analysis."""
    if request.report_format not in _VALID_REPORT_FORMATS:
        raise ValidationError(
            f"Invalid report format '{request.report_format}'. "
            f"Valid formats: {', '.join(sorted(_VALID_REPORT_FORMATS))}"
        )

    analysis_id = service.analyze(
        repository_url=request.repository_url,
        include_ai_review=request.include_ai_review,
        report_format=request.report_format,
    )

    record = service.get_analysis(analysis_id)
    if record is None:
        raise ValidationError("Analysis completed but record not found.")

    return _record_to_response(record)


@router.get(
    "/analyses",
    response_model=list[AnalysisResponse],
)
async def list_analyses(
    service: AnalysisService = Depends(get_analysis_service),
) -> list[AnalysisResponse]:
    """List recent analyses."""
    records = service.list_analyses()
    return [_record_to_response(r) for r in records]


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_analysis(
    analysis_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    """Get analysis details by ID."""
    record = service.get_analysis(analysis_id)
    if record is None:
        raise ValidationError(f"Analysis not found: {analysis_id}")

    return _record_to_response(record)


@router.get(
    "/analyses/{analysis_id}/findings",
    response_model=FindingsResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_findings(
    analysis_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> FindingsResponse:
    """Get findings for an analysis."""
    record = service.get_analysis(analysis_id)
    if record is None:
        raise ValidationError(f"Analysis not found: {analysis_id}")

    findings: list[FindingItem] = []
    if record.findings_json:
        try:
            raw = json.loads(record.findings_json)
            findings = [FindingItem(**f) for f in raw]
        except (json.JSONDecodeError, TypeError, KeyError):
            logger.warning("Failed to deserialize findings for %s", analysis_id)

    return FindingsResponse(
        analysis_id=analysis_id,
        total=len(findings),
        findings=findings,
    )


@router.get(
    "/analyses/{analysis_id}/report",
    response_model=None,
    responses={404: {"model": ErrorResponse}},
)
async def get_report(
    analysis_id: str,
    format: str = "html",
    service: AnalysisService = Depends(get_analysis_service),
) -> ReportResponse | HTMLResponse:
    """Get a report for an analysis."""
    record = service.get_analysis(analysis_id)
    if record is None:
        raise ValidationError(f"Analysis not found: {analysis_id}")

    content: str | None = None
    if format == "html":
        content = record.report_html
    elif format == "json":
        content = record.report_json_content
    elif format == "markdown":
        content = record.report_markdown
    else:
        raise ValidationError(
            f"Invalid report format '{format}'. "
            f"Valid formats: {', '.join(sorted(_VALID_REPORT_FORMATS))}"
        )

    if content is None:
        raise ValidationError(f"Report in '{format}' format not available.")

    if format == "html":
        return HTMLResponse(content=content)

    repo_name = f"{record.repository_owner}_{record.repository_name}"
    ext_map = {"json": "json", "markdown": "md"}

    return ReportResponse(
        analysis_id=analysis_id,
        format=format,
        content=content,
        filename=f"repolens_{repo_name}.{ext_map.get(format, 'txt')}",
    )
