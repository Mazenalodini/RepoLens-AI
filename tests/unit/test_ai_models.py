"""Unit tests for AI domain models."""

from repolens.domain.ai_models import AIContext, AIReview, AIReviewResult


def _make_context(**overrides) -> AIContext:
    defaults = {
        "repository_name": "owner/repo",
        "repository_url": "https://github.com/owner/repo",
        "total_files": 10,
        "total_size_bytes": 5000,
        "language_summary": (("Python", 8), ("TOML", 2)),
        "classification_summary": (("source", 7), ("test", 3)),
        "evidence_summary": ("Evidence 1", "Evidence 2"),
        "findings_summary": ("Finding 1",),
        "project_metadata_name": "myproject",
        "project_metadata_version": "1.0.0",
    }
    defaults.update(overrides)
    return AIContext(**defaults)


def _make_review(**overrides) -> AIReview:
    defaults = {
        "executive_summary": "Good project overall.",
        "strengths": ("Clean code", "Good tests"),
        "concerns": ("No CI",),
        "recommendations": ("Add CI", "Add docs"),
        "overall_assessment": "Healthy repository.",
        "provider_model": "gemini-2.5-flash",
    }
    defaults.update(overrides)
    return AIReview(**defaults)


# --- AIContext ---


def test_ai_context_creation() -> None:
    ctx = _make_context()
    assert ctx.repository_name == "owner/repo"
    assert ctx.total_files == 10
    assert ctx.language_summary == (("Python", 8), ("TOML", 2))


def test_ai_context_is_frozen() -> None:
    ctx = _make_context()
    try:
        ctx.repository_name = "changed"  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except AttributeError:
        pass


def test_ai_context_no_metadata() -> None:
    ctx = _make_context(
        project_metadata_name=None,
        project_metadata_version=None,
    )
    assert ctx.project_metadata_name is None
    assert ctx.project_metadata_version is None


def test_ai_context_deterministic() -> None:
    c1 = _make_context()
    c2 = _make_context()
    assert c1 == c2


# --- AIReview ---


def test_ai_review_creation() -> None:
    review = _make_review()
    assert review.executive_summary == "Good project overall."
    assert review.provider_model == "gemini-2.5-flash"
    assert len(review.strengths) == 2
    assert len(review.concerns) == 1
    assert len(review.recommendations) == 2


def test_ai_review_is_frozen() -> None:
    review = _make_review()
    try:
        review.executive_summary = "x"  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except AttributeError:
        pass


def test_ai_review_empty_tuples() -> None:
    review = _make_review(
        strengths=(), concerns=(), recommendations=(),
    )
    assert review.strengths == ()
    assert review.concerns == ()
    assert review.recommendations == ()


# --- AIReviewResult ---


def test_ai_review_result_success() -> None:
    review = _make_review()
    result = AIReviewResult(
        review=review, error=None, is_successful=True,
    )
    assert result.is_successful
    assert result.review is not None
    assert result.error is None


def test_ai_review_result_failure() -> None:
    result = AIReviewResult(
        review=None,
        error="Provider timeout",
        is_successful=False,
    )
    assert not result.is_successful
    assert result.review is None
    assert result.error == "Provider timeout"


def test_ai_review_result_is_frozen() -> None:
    result = AIReviewResult(
        review=None, error="err", is_successful=False,
    )
    try:
        result.is_successful = True  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except AttributeError:
        pass
