"""RepoLens AI — AI Advisor.

Orchestrates AI review: calls the provider, validates the response,
and wraps the result in AIReviewResult. Never raises to the caller.
"""

import logging

from repolens.domain.ai_models import AIContext, AIReview, AIReviewResult
from repolens.domain.ai_provider import AIProvider
from repolens.domain.exceptions import AIProviderError

logger = logging.getLogger(__name__)


class AIAdvisor:
    """Coordinates the AI review lifecycle.

    - Calls the provider with the minimized context
    - Catches provider errors and wraps them
    - Validates the returned review
    - Never raises exceptions to the caller
    """

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    def review(self, context: AIContext) -> AIReviewResult:
        """Request an AI review and return a wrapped result.

        Returns AIReviewResult with is_successful=True on success,
        or is_successful=False with an error message on failure.
        """
        try:
            ai_review = self._provider.review(context)
        except AIProviderError as exc:
            logger.warning(
                "AI provider '%s' failed: %s",
                self._provider.provider_name,
                exc,
            )
            return AIReviewResult(
                review=None,
                error=f"Provider error: {exc}",
                is_successful=False,
            )
        except Exception as exc:
            logger.exception(
                "Unexpected error from AI provider '%s'.",
                self._provider.provider_name,
            )
            return AIReviewResult(
                review=None,
                error=f"Unexpected error: {exc}",
                is_successful=False,
            )

        validation_error = self._validate_review(ai_review)
        if validation_error:
            logger.warning(
                "AI review from '%s' failed validation: %s",
                self._provider.provider_name,
                validation_error,
            )
            return AIReviewResult(
                review=None,
                error=f"Validation error: {validation_error}",
                is_successful=False,
            )

        return AIReviewResult(
            review=ai_review,
            error=None,
            is_successful=True,
        )

    @staticmethod
    def _validate_review(review: AIReview) -> str | None:
        """Validate that the AI review has required non-empty fields.

        Returns an error message string if invalid, None if valid.
        """
        if not review.executive_summary.strip():
            return "executive_summary is empty"
        if not review.overall_assessment.strip():
            return "overall_assessment is empty"
        if not review.provider_model.strip():
            return "provider_model is empty"
        return None
