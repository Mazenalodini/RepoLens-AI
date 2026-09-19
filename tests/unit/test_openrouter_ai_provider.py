"""Unit tests for OpenRouterAIProvider."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from repolens.domain.ai_models import AIContext
from repolens.domain.exceptions import AIProviderError
from repolens.infrastructure.openrouter_ai_provider import OpenRouterAIProvider


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure environment variables don't bleed into tests."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("REPOLENS_AI_MODEL", raising=False)


def _make_context() -> AIContext:
    return AIContext(
        repository_name="owner/repo",
        repository_url="https://github.com/owner/repo",
        total_files=10,
        total_size_bytes=5000,
        language_summary=(("Python", 8),),
        classification_summary=(("source", 7),),
        evidence_summary=("Evidence 1",),
        findings_summary=("Finding 1",),
        project_metadata_name=None,
        project_metadata_version=None,
    )


# --- Configuration ---


def test_api_key_from_env(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")
    provider = OpenRouterAIProvider()
    assert provider._api_key == "env-key"


def test_api_key_from_init(clean_env) -> None:
    provider = OpenRouterAIProvider(api_key="init-key")
    assert provider._api_key == "init-key"


def test_missing_api_key_raises(clean_env) -> None:
    with pytest.raises(AIProviderError, match="API key not configured"):
        OpenRouterAIProvider()


def test_model_from_env(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    monkeypatch.setenv("REPOLENS_AI_MODEL", "custom-model")
    provider = OpenRouterAIProvider()
    assert provider._model == "custom-model"
    assert "custom-model" in provider.provider_name


def test_model_default(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    provider = OpenRouterAIProvider()
    assert provider._model == "openrouter/free"


def test_timeout_validation_rejects_zero() -> None:
    with pytest.raises(ValueError, match="Timeout must be a finite positive number"):
        OpenRouterAIProvider(api_key="test-key", timeout=0)


def test_timeout_validation_rejects_negative() -> None:
    with pytest.raises(ValueError, match="Timeout must be a finite positive number"):
        OpenRouterAIProvider(api_key="test-key", timeout=-1.5)


def test_timeout_validation_rejects_nan() -> None:
    with pytest.raises(ValueError, match="Timeout must be a finite positive number"):
        OpenRouterAIProvider(api_key="test-key", timeout=float("nan"))


def test_timeout_validation_rejects_inf() -> None:
    with pytest.raises(ValueError, match="Timeout must be a finite positive number"):
        OpenRouterAIProvider(api_key="test-key", timeout=float("inf"))


# --- Provider Execution ---


def _create_mock_response(status_code=200, content=None):
    if content is None:
        content = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "executive_summary": "Test summary",
                        "strengths": ["s1"],
                        "concerns": ["c1"],
                        "recommendations": ["r1"],
                        "overall_assessment": "Test assessment",
                    })
                }
            }]
        })

    response = MagicMock()
    response.status_code = status_code
    response.iter_bytes.return_value = [content.encode("utf-8")]

    if status_code >= 400:
        def raise_for_status():
            raise httpx.HTTPStatusError("Error", request=MagicMock(), response=response)
        response.raise_for_status.side_effect = raise_for_status
    else:
        response.raise_for_status.return_value = None

    return response


@patch("httpx.Client.stream")
def test_successful_review(mock_stream, clean_env) -> None:
    mock_context_manager = MagicMock()
    mock_response = _create_mock_response()
    mock_context_manager.__enter__.return_value = mock_response
    mock_stream.return_value = mock_context_manager

    provider = OpenRouterAIProvider(api_key="test-key")
    review = provider.review(_make_context())

    assert review.executive_summary == "Test summary"
    assert review.overall_assessment == "Test assessment"
    assert review.provider_model == "openrouter/free"
    assert review.strengths == ("s1",)
    assert review.concerns == ("c1",)
    assert review.recommendations == ("r1",)

    mock_stream.assert_called_once()
    kwargs = mock_stream.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert kwargs["json"]["model"] == "openrouter/free"


@patch("httpx.Client")
def test_timeout_is_applied(mock_client_cls, clean_env) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.__enter__.return_value = mock_client

    mock_context_manager = MagicMock()
    mock_response = _create_mock_response()
    mock_context_manager.__enter__.return_value = mock_response
    mock_client.stream.return_value = mock_context_manager

    provider = OpenRouterAIProvider(api_key="test-key", timeout=42.5)
    provider.review(_make_context())

    mock_client_cls.assert_called_once_with(timeout=42.5)


@patch("httpx.Client.stream")
def test_http_401(mock_stream, clean_env) -> None:
    mock_context_manager = MagicMock()
    mock_response = _create_mock_response(status_code=401)
    mock_context_manager.__enter__.return_value = mock_response
    mock_stream.return_value = mock_context_manager

    provider = OpenRouterAIProvider(api_key="test-key")
    with pytest.raises(AIProviderError, match="authentication failed"):
        provider.review(_make_context())


@patch("httpx.Client.stream")
def test_http_429(mock_stream, clean_env) -> None:
    mock_context_manager = MagicMock()
    mock_response = _create_mock_response(status_code=429)
    mock_context_manager.__enter__.return_value = mock_response
    mock_stream.return_value = mock_context_manager

    provider = OpenRouterAIProvider(api_key="test-key")
    with pytest.raises(AIProviderError, match="rate limit exceeded"):
        provider.review(_make_context())


@patch("httpx.Client.stream")
def test_http_500(mock_stream, clean_env) -> None:
    mock_context_manager = MagicMock()
    mock_response = _create_mock_response(status_code=500)
    mock_context_manager.__enter__.return_value = mock_response
    mock_stream.return_value = mock_context_manager

    provider = OpenRouterAIProvider(api_key="test-key")
    with pytest.raises(AIProviderError, match="service error \\(HTTP 500\\)"):
        provider.review(_make_context())


@patch("httpx.Client.stream")
def test_timeout_error(mock_stream, clean_env) -> None:
    mock_stream.side_effect = httpx.TimeoutException("timeout")

    provider = OpenRouterAIProvider(api_key="test-key", timeout=1.5)
    with pytest.raises(AIProviderError, match=r"timed out after 1.5s"):
        provider.review(_make_context())


@patch("httpx.Client.stream")
def test_connection_error(mock_stream, clean_env) -> None:
    mock_stream.side_effect = httpx.ConnectError("connection refused")

    provider = OpenRouterAIProvider(api_key="test-key")
    with pytest.raises(AIProviderError, match="Cannot connect"):
        provider.review(_make_context())


@patch("httpx.Client.stream")
def test_empty_response(mock_stream, clean_env) -> None:
    mock_context_manager = MagicMock()
    mock_response = _create_mock_response(content="{}")
    mock_context_manager.__enter__.return_value = mock_response
    mock_stream.return_value = mock_context_manager

    provider = OpenRouterAIProvider(api_key="test-key")
    with pytest.raises(AIProviderError, match="missing choices"):
        provider.review(_make_context())


@patch("httpx.Client.stream")
def test_invalid_json_payload(mock_stream, clean_env) -> None:
    mock_context_manager = MagicMock()
    mock_response = _create_mock_response(content="{invalid}")
    mock_context_manager.__enter__.return_value = mock_response
    mock_stream.return_value = mock_context_manager

    provider = OpenRouterAIProvider(api_key="test-key")
    with pytest.raises(AIProviderError, match="malformed JSON payload"):
        provider.review(_make_context())


@patch("httpx.Client.stream")
def test_wrong_schema(mock_stream, clean_env) -> None:
    # Outer JSON is valid, but the inner content is not the expected schema
    mock_context_manager = MagicMock()
    mock_response = _create_mock_response(
        content=json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps(["not", "an", "object"])
                }
            }]
        })
    )
    mock_context_manager.__enter__.return_value = mock_response
    mock_stream.return_value = mock_context_manager

    provider = OpenRouterAIProvider(api_key="test-key")
    with pytest.raises(AIProviderError, match="structure is invalid"):
        provider.review(_make_context())


@patch("httpx.Client.stream")
def test_api_key_not_in_error(mock_stream, clean_env) -> None:
    mock_context_manager = MagicMock()
    mock_response = _create_mock_response(status_code=401)
    mock_context_manager.__enter__.return_value = mock_response
    mock_stream.return_value = mock_context_manager

    secret_key = "secret_key_12345"
    provider = OpenRouterAIProvider(api_key=secret_key)
    try:
        provider.review(_make_context())
    except AIProviderError as exc:
        assert secret_key not in str(exc)


@patch("httpx.Client")
def test_response_size_limit(mock_client_cls, clean_env) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.__enter__.return_value = mock_client

    mock_context_manager = MagicMock()

    # Create chunks that exceed the 1MB limit (1024 * 1024)
    chunk1 = b"x" * (1024 * 512)
    chunk2 = b"x" * (1024 * 512 + 10)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.iter_bytes.return_value = [chunk1, chunk2]

    mock_context_manager.__enter__.return_value = mock_response
    mock_client.stream.return_value = mock_context_manager

    provider = OpenRouterAIProvider(api_key="test-key")
    with pytest.raises(AIProviderError, match="maximum size limit"):
        provider.review(_make_context())


def test_api_key_not_in_repr(clean_env) -> None:
    secret_key = "secret_key_12345"
    provider = OpenRouterAIProvider(api_key=secret_key)

    assert secret_key not in repr(provider)
    assert secret_key not in str(provider)
    assert secret_key not in provider.provider_name
