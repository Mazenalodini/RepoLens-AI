"""Unit tests for API dependencies."""

import pytest

from repolens.api.dependencies import _create_ai_provider
from repolens.infrastructure.google_ai_provider import GoogleAIProvider
from repolens.infrastructure.openrouter_ai_provider import OpenRouterAIProvider


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure environment variables don't bleed into tests."""
    monkeypatch.delenv("REPOLENS_AI_PROVIDER", raising=False)
    monkeypatch.delenv("REPOLENS_AI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


def test_explicit_google(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPOLENS_AI_PROVIDER", "google")
    monkeypatch.setenv("REPOLENS_AI_API_KEY", "google-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")  # Should be ignored

    provider = _create_ai_provider()

    assert isinstance(provider, GoogleAIProvider)
    assert provider._api_key == "google-key"


def test_explicit_google_missing_key(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPOLENS_AI_PROVIDER", "google")
    # Missing REPOLENS_AI_API_KEY
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    provider = _create_ai_provider()

    assert provider is None


def test_explicit_openrouter(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPOLENS_AI_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("REPOLENS_AI_API_KEY", "google-key")  # Should be ignored

    provider = _create_ai_provider()

    assert isinstance(provider, OpenRouterAIProvider)
    assert provider._api_key == "openrouter-key"


def test_explicit_openrouter_missing_key(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPOLENS_AI_PROVIDER", "openrouter")
    # Missing OPENROUTER_API_KEY
    monkeypatch.setenv("REPOLENS_AI_API_KEY", "google-key")

    provider = _create_ai_provider()

    assert provider is None


def test_explicit_invalid_provider(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPOLENS_AI_PROVIDER", "invalid-provider")
    monkeypatch.setenv("REPOLENS_AI_API_KEY", "google-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    provider = _create_ai_provider()

    assert provider is None


def test_auto_detect_google(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    # No explicit provider
    monkeypatch.setenv("REPOLENS_AI_API_KEY", "google-key")

    provider = _create_ai_provider()

    assert isinstance(provider, GoogleAIProvider)
    assert provider._api_key == "google-key"


def test_auto_detect_openrouter(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    # No explicit provider
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    provider = _create_ai_provider()

    assert isinstance(provider, OpenRouterAIProvider)
    assert provider._api_key == "openrouter-key"


def test_auto_detect_google_takes_precedence(clean_env, monkeypatch: pytest.MonkeyPatch) -> None:
    # No explicit provider, both keys present
    monkeypatch.setenv("REPOLENS_AI_API_KEY", "google-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    provider = _create_ai_provider()

    # Documented backward-compatible behavior: Google wins
    assert isinstance(provider, GoogleAIProvider)
    assert provider._api_key == "google-key"


def test_no_provider(clean_env) -> None:
    provider = _create_ai_provider()
    assert provider is None
