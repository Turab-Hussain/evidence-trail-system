"""Shared helper: pull one JSON object out of an LLM text answer."""

from __future__ import annotations

import json
import re
from typing import Any

from evidence_trail.domain.exceptions import LLMError

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse the first JSON object in ``text`` (models sometimes add prose or fences).

    Raises:
        LLMError: no JSON object found, invalid JSON, or the JSON is not an object.
    """
    match = _JSON_BLOCK.search(text or "")
    if match is None:
        raise LLMError("LLM answer contained no JSON object.")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMError(f"LLM answer was not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMError("LLM answer JSON was not an object.")
    return parsed
