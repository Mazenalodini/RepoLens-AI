"""Unit tests for API error handlers."""

from unittest.mock import MagicMock

import pytest

from repolens.api.errors import repolens_error_handler, unexpected_error_handler
from repolens.domain.exceptions import (
    AcquisitionError,
    AcquisitionTimeoutError,
    ConcurrencyLimitError,
    PipelineError,
    RepoLensError,
    ReportError,
    RepositoryNotFoundError,
    RepositorySizeError,
    ValidationError,
)


def _make_request() -> MagicMock:
    request = MagicMock()
    request.method = "POST"
    request.url.path = "/api/v1/analyses"
    return request


@pytest.mark.asyncio
async def test_validation_error_returns_422() -> None:
    resp = await repolens_error_handler(
        _make_request(),
        ValidationError("bad url"),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_not_found_returns_404() -> None:
    resp = await repolens_error_handler(
        _make_request(),
        RepositoryNotFoundError("not found"),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_acquisition_timeout_returns_504() -> None:
    resp = await repolens_error_handler(
        _make_request(),
        AcquisitionTimeoutError("timed out"),
    )
    assert resp.status_code == 504


@pytest.mark.asyncio
async def test_acquisition_error_returns_502() -> None:
    resp = await repolens_error_handler(
        _make_request(),
        AcquisitionError("failed"),
    )
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_repo_size_error_returns_422() -> None:
    resp = await repolens_error_handler(
        _make_request(),
        RepositorySizeError("too large"),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_concurrency_limit_returns_429() -> None:
    resp = await repolens_error_handler(
        _make_request(),
        ConcurrencyLimitError("busy"),
    )
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_pipeline_error_returns_500() -> None:
    resp = await repolens_error_handler(
        _make_request(),
        PipelineError("pipeline broke"),
    )
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_report_error_returns_500() -> None:
    resp = await repolens_error_handler(
        _make_request(),
        ReportError("report failed"),
    )
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_base_repolens_error_returns_500() -> None:
    resp = await repolens_error_handler(
        _make_request(),
        RepoLensError("generic"),
    )
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_unexpected_error_returns_500() -> None:
    resp = await unexpected_error_handler(
        _make_request(),
        RuntimeError("oops"),
    )
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_error_response_has_detail() -> None:
    resp = await repolens_error_handler(
        _make_request(),
        ValidationError("bad input"),
    )
    import json
    body = json.loads(resp.body.decode())
    assert body["error"] == "Invalid input"
    assert body["detail"] == "bad input"


@pytest.mark.asyncio
async def test_unexpected_error_hides_detail() -> None:
    resp = await unexpected_error_handler(
        _make_request(),
        RuntimeError("secret info"),
    )
    import json
    body = json.loads(resp.body.decode())
    assert body["detail"] is None
