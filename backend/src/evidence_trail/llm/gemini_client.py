"""Google Gemini implementation of :class:`LLMClient` (optional dependency).

Install with ``pip install -e ".[gemini]"`` and set ``GEMINI_API_KEY``.
"""

from __future__ import annotations

import logging
from typing import Any

from evidence_trail.domain.exceptions import LLMError
from evidence_trail.llm.base import LLMClient
from evidence_trail.llm.json_utils import parse_json_object

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-flash-latest"


class GeminiLLMClient(LLMClient):
    """Calls the Gemini API through the ``google-genai`` SDK in JSON mode."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_GEMINI_MODEL,
        *,
        temperature: float = 0.0,
        client: Any | None = None,
    ) -> None:
        """
        Args:
            api_key: Gemini API key.
            model: Model name; override if your key has access to a newer one.
            temperature: 0 keeps extraction as repeatable as the model allows.
            client: Pre-built SDK client (used by tests to avoid network calls).
        """
        self._model = model
        self._temperature = temperature
        if client is not None:
            self._client = client
            return
        try:
            from google import genai  # noqa: PLC0415 - optional dependency
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise LLMError(
                "The 'google-genai' package is not installed. "
                'Install it with: pip install -e ".[gemini]"'
            ) from exc
        self._client = genai.Client(api_key=api_key)

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        try:
            from google.genai import types  # noqa: PLC0415 - optional dependency

            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=self._temperature,
                ),
            )
            text = response.text
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001 - SDK raises many error types
            logger.warning("Gemini call failed: %s", exc)
            raise LLMError(f"Gemini call failed: {exc}") from exc
        return parse_json_object(text or "")
