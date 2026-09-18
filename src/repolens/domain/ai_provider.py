"""RepoLens AI — AI Provider Protocol.

Defines the provider-agnostic contract for AI review generation.
Concrete implementations belong in Infrastructure.
"""

from typing import Protocol

from repolens.domain.ai_models import AIContext, AIReview


class AIProvider(Protocol):
    """Protocol for AI review providers.

    Implementations must translate an AIContext into a structured AIReview.
    Provider-specific logic (API keys, SDK calls) belongs in Infrastructure.
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        ...

    def review(self, context: AIContext) -> AIReview:
        """Generate a structured review from the given context.

        Args:
            context: Minimized, structured AI context.

        Returns:
            Validated AIReview with structured interpretation.

        Raises:
            AIProviderError: If the provider call fails.
        """
        ...
