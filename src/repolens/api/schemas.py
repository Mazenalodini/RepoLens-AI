"""RepoLens AI — API Request/Response Schemas.

Pydantic models for HTTP request validation and response serialization.
"""

from pydantic import BaseModel, Field

# --- Requests ---


class AnalysisRequest(BaseModel):
    """Request body for POST /api/v1/analyses."""

    repository_url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="GitHub repository URL.",
    )
    include_ai_review: bool = Field(
        default=True,
        description="Whether to include AI-powered review.",
    )
    report_format: str = Field(
        default="html",
        description="Primary report format: html, json, or markdown.",
    )


# --- Responses ---


class AnalysisResponse(BaseModel):
    """Response for analysis metadata."""

    analysis_id: str
    repository_name: str
    repository_url: str
    status: str
    created_at: str
    completed_at: str | None = None
    total_files: int = 0
    total_directories: int = 0
    total_size_bytes: int = 0
    total_evidence: int = 0
    total_findings: int = 0
    ai_review_available: bool = False
    error_message: str | None = None


class FindingItem(BaseModel):
    """Single finding in the findings response."""

    rule_id: str
    finding_id: str
    category: str
    severity: str
    title: str
    description: str
    source_analyzer: str
    recommendation: str | None = None


class FindingsResponse(BaseModel):
    """Response for GET /api/v1/analyses/{id}/findings."""

    analysis_id: str
    total: int
    findings: list[FindingItem]


class ReportResponse(BaseModel):
    """Response for GET /api/v1/analyses/{id}/report."""

    analysis_id: str
    format: str
    content: str
    filename: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: str | None = None


class HealthResponse(BaseModel):
    """Response for GET /api/v1/health."""

    status: str = "ok"
    version: str = "0.1.0"
