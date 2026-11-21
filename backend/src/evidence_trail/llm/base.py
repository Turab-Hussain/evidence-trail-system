"""LLM abstraction.

Agents depend on :class:`LLMClient` only, so the provider (Anthropic, a local
model, a test double) can be swapped without touching agent code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    """Minimal contract: send a prompt, receive a parsed JSON object."""

    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Return the model's answer parsed as a JSON object.

        Raises:
            LLMError: if the call fails or the answer is not valid JSON.
        """
