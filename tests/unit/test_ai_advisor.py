"""Unit tests for AIAdvisor."""

from repolens.application.ai_advisor import AIAdvisor
from repolens.domain.ai_models import AIContext, AIReview
from repolens.domain.exceptions import AIProviderError


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


class MockProvider:
    """Mock AI provider for testing."""

    def __init__(
        self,
        *,
        review: AIReview | None = None,
        error: Exception | None = None,
    ) -> None:
        self._review = review
        self._error = error

    @property
    def provider_name(self) -> str:
        return "mock-provider"

    def review(self, context: AIContext) -> AIReview:
        if self._error is not None:
            raise self._error
        if self._review is not None:
            return self._review
        return AIReview(
            executive_summary="Good project.",
            strengths=("Clean code",),
            concerns=("No CI",),
            recommendations=("Add CI",),
            overall_assessment="Healthy.",
            provider_model="mock-v1",
        )


# --- Success ---


def test_successful_review() -> None:
    provider = MockProvider()
    advisor = AIAdvisor(provider)
    result = advisor.review(_make_context())

    assert result.is_successful
    assert result.review is not None
    assert result.error is None
    assert result.review.executive_summary == "Good project."
    assert result.review.provider_model == "mock-v1"


# --- Provider errors ---


def test_provider_error_captured() -> None:
    provider = MockProvider(
        error=AIProviderError("API timeout"),
    )
    advisor = AIAdvisor(provider)
    result = advisor.review(_make_context())

    assert not result.is_successful
    assert result.review is None
    assert "API timeout" in result.error


def test_unexpected_error_captured() -> None:
    provider = MockProvider(
        error=RuntimeError("unexpected"),
    )
    advisor = AIAdvisor(provider)
    result = advisor.review(_make_context())

    assert not result.is_successful
    assert result.review is None
    assert "unexpected" in result.error


# --- Validation ---


def test_empty_executive_summary_fails_validation() -> None:
    review = AIReview(
        executive_summary="",
        strengths=(),
        concerns=(),
        recommendations=(),
        overall_assessment="OK.",
        provider_model="mock-v1",
    )
    provider = MockProvider(review=review)
    advisor = AIAdvisor(provider)
    result = advisor.review(_make_context())

    assert not result.is_successful
    assert "executive_summary" in result.error


def test_empty_overall_assessment_fails_validation() -> None:
    review = AIReview(
        executive_summary="Summary.",
        strengths=(),
        concerns=(),
        recommendations=(),
        overall_assessment="",
        provider_model="mock-v1",
    )
    provider = MockProvider(review=review)
    advisor = AIAdvisor(provider)
    result = advisor.review(_make_context())

    assert not result.is_successful
    assert "overall_assessment" in result.error


def test_empty_provider_model_fails_validation() -> None:
    review = AIReview(
        executive_summary="Summary.",
        strengths=(),
        concerns=(),
        recommendations=(),
        overall_assessment="OK.",
        provider_model="",
    )
    provider = MockProvider(review=review)
    advisor = AIAdvisor(provider)
    result = advisor.review(_make_context())

    assert not result.is_successful
    assert "provider_model" in result.error


def test_whitespace_only_fails_validation() -> None:
    review = AIReview(
        executive_summary="   ",
        strengths=(),
        concerns=(),
        recommendations=(),
        overall_assessment="OK.",
        provider_model="mock-v1",
    )
    provider = MockProvider(review=review)
    advisor = AIAdvisor(provider)
    result = advisor.review(_make_context())

    assert not result.is_successful
    assert "executive_summary" in result.error


# --- Never raises ---


def test_advisor_never_raises() -> None:
    """AIAdvisor must never raise to the caller."""
    provider = MockProvider(
        error=AIProviderError("fail"),
    )
    advisor = AIAdvisor(provider)
    # This must not raise
    result = advisor.review(_make_context())
    assert not result.is_successful
