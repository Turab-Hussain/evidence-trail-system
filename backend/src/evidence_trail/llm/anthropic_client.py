"""Anthropic implementation of :class:`LLMClient` (optional dependency)."""

from __future__ import annotations

import logging
from typing import Any

from evidence_trail.domain.exceptions import LLMError
from evidence_trail.llm.base import LLMClient
from evidence_trail.llm.json_utils import parse_json_object

logger = logging.getLogger(__name__)


class AnthropicLLMClient(LLMClient):
    """Calls the Anthropic Messages API and parses a JSON reply.

    The ``anthropic`` package is imported lazily so the rest of the system
    works without it installed (``pip install .[anthropic]`` to enable).
    """

    def __init__(self, api_key: str, model: str, max_tokens: int = 2000) -> None:
        try:
            import anthropic  # noqa: PLC0415 - optional dependency
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise LLMError(
                "The 'anthropic' package is not installed. "
                "Install it with: pip install .[anthropic]"
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = "".join(
                block.text for block in response.content if getattr(block, "type", "") == "text"
            )
        except Exception as exc:  # noqa: BLE001 - SDK raises many error types
            logger.warning("LLM call failed: %s", exc)
            raise LLMError(f"LLM call failed: {exc}") from exc
        return parse_json_object(text)
