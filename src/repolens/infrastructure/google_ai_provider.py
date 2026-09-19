"""RepoLens AI — Google AI Provider.

Concrete AIProvider implementation using the Google GenAI SDK.
Isolated in Infrastructure — Domain and Application never import this.
"""

import logging
import math
import os

from repolens.domain.ai_models import AIContext, AIReview
from repolens.domain.exceptions import AIProviderError
from repolens.infrastructure.ai_prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    parse_review_json,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_ENV_API_KEY = "REPOLENS_AI_API_KEY"
_ENV_MODEL = "REPOLENS_AI_MODEL"


class GoogleAIProvider:
    """AI provider using Google GenAI SDK.

    Configuration:
    - API key: REPOLENS_AI_API_KEY environment variable (required)
    - Model: REPOLENS_AI_MODEL environment variable (default: gemini-2.5-flash)

    The API key is never logged, persisted, or included in AIContext.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Initialize the Google AI provider.

        Args:
            api_key: API key. Falls back to REPOLENS_AI_API_KEY env var.
            model: Model name. Falls back to REPOLENS_AI_MODEL env var,
                   then to gemini-2.5-flash.
            timeout: API call timeout in seconds. Will be converted to milliseconds for the SDK.
        """
        self._api_key = api_key or os.environ.get(_ENV_API_KEY, "")
        self._model = (
            model
            or os.environ.get(_ENV_MODEL, "")
            or _DEFAULT_MODEL
        )

        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError(f"Timeout must be a finite positive number, got {timeout}")

        self._timeout = timeout

        if not self._api_key:
            raise AIProviderError(
                f"API key not configured. Set {_ENV_API_KEY} "
                f"environment variable."
            )

    @property
    def provider_name(self) -> str:
        return f"google-genai ({self._model})"

    def review(self, context: AIContext) -> AIReview:
        """Generate a structured review using Google GenAI.

        Raises:
            AIProviderError: On network, auth, or parsing failures.
        """
        try:
            from google import genai
        except ImportError as exc:
            raise AIProviderError(
                "google-genai package is not installed. "
                "Install with: pip install google-genai"
            ) from exc

        user_prompt = build_user_prompt(context)

        try:
            client = genai.Client(api_key=self._api_key)
            timeout_ms = int(self._timeout * 1000)
            response = client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.3,
                    http_options=genai.types.HttpOptions(timeout=timeout_ms),
                ),
            )
        except Exception as exc:
            raise AIProviderError(
                f"Google GenAI API call failed: {exc}"
            ) from exc

        try:
            text = response.text  # type: ignore[attr-defined]
        except AttributeError as exc:
            raise AIProviderError("AI response has no text content.") from exc

        return parse_review_json(text, self._model)
