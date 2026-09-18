"""Unit tests for GoogleAIProvider."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from repolens.domain.ai_models import AIContext
from repolens.domain.exceptions import AIProviderError
from repolens.infrastructure.google_ai_provider import GoogleAIProvider


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure environment variables don't bleed into tests."""
    monkeypatch.delenv("REPOLENS_AI_API_KEY", raising=False)
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
    monkeypatch.setenv("REPOLENS_AI_API_KEY", "env-key")
    provider = GoogleAIProvider()
    assert provider._api_key == "env-key"


def test_api_key_from_init(clean_env) -> None:
    provider = GoogleAIProvider(api_key="init-key")
    assert provider._api_key == "init-key"


def test_missing_api_key_raises(clean_env) -> None:
    with pytest.raises(AIProviderError, match="API key not configured"):
        GoogleAIProvider()


def test_model_from_env(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPOLENS_AI_API_KEY", "key")
    monkeypatch.setenv("REPOLENS_AI_MODEL", "custom-model")
    provider = GoogleAIProvider()
    assert provider._model == "custom-model"
    assert "custom-model" in provider.provider_name


def test_model_default(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPOLENS_AI_API_KEY", "key")
    provider = GoogleAIProvider()
    assert provider._model == "gemini-2.5-flash"





@pytest.fixture
def mock_genai_client():
    mock_module = MagicMock()
    mock_client_cls = MagicMock()
    mock_module.Client = mock_client_cls

    mock_google = MagicMock()
    mock_google.genai = mock_module

    with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_module}):
        yield mock_client_cls

# --- Provider Execution ---


def test_successful_review(mock_genai_client, clean_env) -> None:
    # Setup mock response
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "executive_summary": "Test summary",
        "strengths": ["s1"],
        "concerns": ["c1"],
        "recommendations": ["r1"],
        "overall_assessment": "Test assessment",
    })

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai_client.return_value = mock_client

    provider = GoogleAIProvider(api_key="test-key")
    review = provider.review(_make_context())

    # Verify response
    assert review.executive_summary == "Test summary"
    assert review.overall_assessment == "Test assessment"
    assert review.provider_model == "gemini-2.5-flash"
    assert review.strengths == ("s1",)
    assert review.concerns == ("c1",)
    assert review.recommendations == ("r1",)

    # Verify client initialization
    mock_genai_client.assert_called_once_with(api_key="test-key")

    # Verify API call
    mock_client.models.generate_content.assert_called_once()
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash"
    assert "owner/repo" in call_kwargs["contents"]
    assert "Evidence 1" in call_kwargs["contents"]


def test_removes_markdown_fences(mock_genai_client, clean_env) -> None:
    mock_response = MagicMock()
    mock_response.text = "```json\n" + json.dumps({
        "executive_summary": "Test summary",
        "strengths": [],
        "concerns": [],
        "recommendations": [],
        "overall_assessment": "Test assessment",
    }) + "\n```"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai_client.return_value = mock_client

    provider = GoogleAIProvider(api_key="test-key")
    review = provider.review(_make_context())

    assert review.executive_summary == "Test summary"


def test_handles_api_failure(mock_genai_client, clean_env) -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API down")
    mock_genai_client.return_value = mock_client

    provider = GoogleAIProvider(api_key="test-key")

    with pytest.raises(AIProviderError, match="API call failed: API down"):
        provider.review(_make_context())


def test_handles_invalid_json(mock_genai_client, clean_env) -> None:
    mock_response = MagicMock()
    mock_response.text = "{ invalid json }"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai_client.return_value = mock_client

    provider = GoogleAIProvider(api_key="test-key")

    with pytest.raises(AIProviderError, match="not valid JSON"):
        provider.review(_make_context())


def test_handles_missing_text(mock_genai_client, clean_env) -> None:
    mock_response = MagicMock()
    del mock_response.text

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai_client.return_value = mock_client

    provider = GoogleAIProvider(api_key="test-key")

    with pytest.raises(AIProviderError, match="no text content"):
        provider.review(_make_context())


def test_handles_empty_text(mock_genai_client, clean_env) -> None:
    mock_response = MagicMock()
    mock_response.text = "   \n"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai_client.return_value = mock_client

    provider = GoogleAIProvider(api_key="test-key")

    with pytest.raises(AIProviderError, match="empty"):
        provider.review(_make_context())


def test_handles_wrong_schema(mock_genai_client, clean_env) -> None:
    mock_response = MagicMock()
    mock_response.text = json.dumps(["not", "an", "object"])

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai_client.return_value = mock_client

    provider = GoogleAIProvider(api_key="test-key")

    with pytest.raises(AIProviderError, match="structure is invalid"):
        provider.review(_make_context())
