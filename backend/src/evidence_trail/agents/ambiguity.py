"""Ambiguity Detection Agent (rule based).

Finds three kinds of problems and attaches a clarification question to each:

* **vague terms**   - "premium", "fast", "user-friendly", ...
* **missing constraints** - non-functional requirements without a number
* **conflicts**     - the same unit quoted with different values by different sources
"""

from __future__ import annotations

import re

from evidence_trail.agents.base import Agent
from evidence_trail.domain.enums import AmbiguityType, RequirementType
from evidence_trail.domain.models import AmbiguityFinding, Requirement

# Words that sound specific but are not measurable.
VAGUE_TERMS = frozenset(
    {
        "premium", "modern", "nice", "clean", "simple", "easy", "intuitive",
        "user-friendly", "fast", "quick", "quickly", "better", "good", "great",
        "robust", "flexible", "scalable", "appropriate", "professional",
        "attractive", "smooth", "seamless", "etc", "asap",
    }
)  # fmt: skip

_PHRASES = ("and so on", "as needed", "high quality", "state of the art")
_QUANTITY = re.compile(
    r"(\d+(?:\.\d+)?)\s*(seconds?|secs?|ms|minutes?|hours?|days?|users?|%|mb|gb|s)\b",
    re.IGNORECASE,
)
_UNIT_ALIASES = {"sec": "second", "secs": "second", "s": "second", "seconds": "second"}


class AmbiguityDetectionAgent(Agent[Requirement, list[AmbiguityFinding]]):
    """Returns every ambiguity finding for a requirement."""

    name = "ambiguity_detection_agent"

    def run(self, payload: Requirement) -> list[AmbiguityFinding]:
        findings: list[AmbiguityFinding] = []
        findings.extend(self._vague_terms(payload))
        findings.extend(self._missing_constraints(payload))
        findings.extend(self._conflicts(payload))
        return findings

    # ----------------------------------------------------------------- rules
    def _vague_terms(self, req: Requirement) -> list[AmbiguityFinding]:
        text = f"{req.title} {req.description}".lower()
        words = set(re.findall(r"[a-z][a-z-]*", text))
        found = sorted(term for term in VAGUE_TERMS if term in words)
        found += [phrase for phrase in _PHRASES if phrase in text]
        return [
            AmbiguityFinding(
                requirement_id=req.requirement_id,
                issue_type=AmbiguityType.VAGUE_TERM,
                explanation=f"'{term}' is subjective and can be interpreted differently.",
                clarification_question=(
                    f"What concrete, measurable outcome do you expect when you say '{term}'?"
                ),
            )
            for term in found
        ]

    def _missing_constraints(self, req: Requirement) -> list[AmbiguityFinding]:
        if req.type is not RequirementType.NON_FUNCTIONAL:
            return []
        if re.search(r"\d", req.description):
            return []
        return [
            AmbiguityFinding(
                requirement_id=req.requirement_id,
                issue_type=AmbiguityType.MISSING_CONSTRAINT,
                explanation="A quality requirement was stated without a measurable target.",
                clarification_question=(
                    "What target value (for example time, number of users or percentage) "
                    "should this meet?"
                ),
            )
        ]

    def _conflicts(self, req: Requirement) -> list[AmbiguityFinding]:
        """Same unit, different numbers, across the requirement's evidence."""
        values_by_unit: dict[str, set[str]] = {}
        for ref in req.sources:
            for number, unit in _QUANTITY.findall(ref.snippet):
                key = self._normalise_unit(unit)
                values_by_unit.setdefault(key, set()).add(self._normalise_number(number))
        return [
            AmbiguityFinding(
                requirement_id=req.requirement_id,
                issue_type=AmbiguityType.CONFLICT,
                explanation=(
                    f"Sources give different values for '{unit}': {', '.join(sorted(values))}."
                ),
                clarification_question=f"Which value for '{unit}' is correct: "
                f"{' or '.join(sorted(values))}?",
            )
            for unit, values in sorted(values_by_unit.items())
            if len(values) > 1
        ]

    @staticmethod
    def _normalise_unit(unit: str) -> str:
        unit = unit.lower()
        if unit in _UNIT_ALIASES:
            return _UNIT_ALIASES[unit]
        return unit[:-1] if unit.endswith("s") and len(unit) > 2 else unit

    @staticmethod
    def _normalise_number(number: str) -> str:
        """``5`` and ``5.0`` are the same value."""
        value = float(number)
        return str(int(value)) if value.is_integer() else str(value)
