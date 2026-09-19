"""RepoLens AI — OpenRouter AI Provider.

Concrete AIProvider implementation using OpenRouter via HTTP.
Isolated in Infrastructure — Domain and Application never import this.
"""

import json
import logging
import math
import os

import httpx

from repolens.domain.ai_models import AIContext, AIReview
from repolens.domain.exceptions import AIProviderError
from repolens.infrastructure.ai_prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    parse_review_json,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "openrouter/free"
_ENV_API_KEY = "OPENROUTER_API_KEY"
_ENV_MODEL = "REPOLENS_AI_MODEL"

# Bounded response size safeguard (1 MB) to prevent memory exhaustion
_MAX_RESPONSE_BYTES = 1024 * 1024


class OpenRouterAIProvider:
    """AI provider using OpenRouter HTTP API.

    Configuration:
    - API key: OPENROUTER_API_KEY environment variable (required)
    - Model: REPOLENS_AI_MODEL environment variable (default: openrouter/free)

    The API key is never logged, persisted, or included in AIContext.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Initialize the OpenRouter AI provider.

        Args:
            api_key: API key. Falls back to OPENROUTER_API_KEY env var.
            model: Model name. Falls back to REPOLENS_AI_MODEL env var,
                   then to openrouter/free.
            timeout: API call timeout in seconds.
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
        return f"openrouter ({self._model})"

    def review(self, context: AIContext) -> AIReview:
        """Generate a structured review using OpenRouter.

        Raises:
            AIProviderError: On network, auth, or parsing failures.
        """
        user_prompt = build_user_prompt(context)

        try:
            with (
                httpx.Client(timeout=self._timeout) as client,
                client.stream(
                    "POST",
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.3,
                    },
                ) as response,
            ):
                    # Handle specific HTTP error status codes explicitly
                    if response.status_code == 401:
                        raise AIProviderError("OpenRouter authentication failed. Check OPENROUTER_API_KEY.")
                    if response.status_code == 429:
                        raise AIProviderError("OpenRouter rate limit exceeded. Try again later.")
                    if response.status_code >= 500:
                        raise AIProviderError(f"OpenRouter service error (HTTP {response.status_code}).")

                    # Handle any other HTTP errors
                    response.raise_for_status()

                    # Bounded read to avoid memory exhaustion
                    content_chunks = []
                    total_bytes = 0
                    for chunk in response.iter_bytes():
                        total_bytes += len(chunk)
                        if total_bytes > _MAX_RESPONSE_BYTES:
                            raise AIProviderError(
                                f"OpenRouter response exceeded maximum size limit of {_MAX_RESPONSE_BYTES} bytes."
                            )
                        content_chunks.append(chunk)

                    raw_content = b"".join(content_chunks).decode("utf-8")

        except httpx.TimeoutException as exc:
            raise AIProviderError(f"OpenRouter request timed out after {self._timeout}s.") from exc
        except httpx.ConnectError as exc:
            raise AIProviderError("Cannot connect to OpenRouter API.") from exc
        except httpx.HTTPStatusError as exc:
            # Fallback for 4xx errors other than 401 and 429
            raise AIProviderError(f"OpenRouter HTTP error {exc.response.status_code}.") from exc
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(f"OpenRouter API call failed: {exc}") from exc

        return self._extract_and_parse(raw_content)

    def _extract_and_parse(self, raw_content: str) -> AIReview:
        """Extract choices[0].message.content from the OpenRouter payload and parse it."""
        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise AIProviderError(f"OpenRouter returned malformed JSON payload: {exc}") from exc

        choices = payload.get("choices")
        if not choices or not isinstance(choices, list):
            raise AIProviderError("OpenRouter returned empty or invalid response (missing choices).")

        first_choice = choices[0]
        message = first_choice.get("message")
        if not message or not isinstance(message, dict):
            raise AIProviderError("OpenRouter returned empty or invalid response (missing message).")

        content = message.get("content")
        if not content:
            raise AIProviderError("OpenRouter returned empty or invalid response (missing content).")

        return parse_review_json(str(content), self._model)
