"""Requirement Extraction Agent.

Converts one :class:`SourceMessage` into candidate :class:`Requirement`
objects.  If an :class:`LLMClient` is configured it is tried first; on *any*
LLM failure the agent falls back to deterministic heuristics, so a model
outage never silently drops evidence (non-functional "Reliability" requirement).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from evidence_trail.agents.base import Agent
from evidence_trail.domain.enums import Priority, RequirementType
from evidence_trail.domain.exceptions import LLMError
from evidence_trail.domain.models import Requirement, SourceMessage, SourceReference
from evidence_trail.llm.base import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a requirements engineer. Extract software requirements from the "
    "client message. Reply ONLY with JSON: "
    '{"requirements": [{"title": str, "description": str, '
    '"type": "functional"|"non_functional", "priority": "high"|"medium"|"low", '
    '"confidence": number between 0 and 1, "snippet": exact supporting text}]}. '
    "Never invent details that are not in the message."
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_CUE = re.compile(
    r"\b(need|needs|must|should|want|wants|require|requires|required|have to|has to|"
    r"add|support|include|allow|make|provide|enable|let users|will)\b",
    re.IGNORECASE,
)
_NFR = re.compile(
    r"\b(secure|security|fast|speed|performance|load|uptime|available|availability|"
    r"responsive|accessible|scalable|encrypt\w*|backup|latency)\b",
    re.IGNORECASE,
)
_HIGH = re.compile(r"\b(urgent|asap|critical|must|immediately|high priority)\b", re.IGNORECASE)
_LOW = re.compile(r"\b(nice to have|optional|later|eventually|if possible|maybe)\b", re.IGNORECASE)
_LEAD_IN = re.compile(
    r"^(hi|hello|hey|thanks?|please|also|and|so|ok|okay)[,!. ]+|"
    r"^(we|i|you|they)\s+(really\s+)?(need|want|must|should|require|have to)\s+(to\s+)?|"
    r"^(can|could)\s+you\s+(please\s+)?|^it\s+(should|must|will)\s+|^(the\s+)?system\s+(should|must|will)\s+",
    re.IGNORECASE,
)


# Words a truncated title must not end on.
_DANGLING = frozenset("a an the to of for with and or but on in at by as that which".split())


class _LLMRequirement(BaseModel):
    """Schema the LLM output must satisfy (schema-constrained generation)."""

    title: str = Field(min_length=3)
    description: str = Field(min_length=3)
    type: RequirementType = RequirementType.FUNCTIONAL
    priority: Priority = Priority.MEDIUM
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    snippet: str = ""


class RequirementExtractionAgent(Agent[SourceMessage, list[Requirement]]):
    """Extracts candidate requirements from a single source message."""

    name = "requirement_extraction_agent"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm

    # ------------------------------------------------------------------ API
    def run(self, payload: SourceMessage) -> list[Requirement]:
        if self._llm is not None:
            try:
                return self._extract_with_llm(payload)
            except LLMError as exc:
                logger.warning(
                    "LLM extraction failed for %s (%s); using heuristic fallback.",
                    payload.source_id,
                    exc,
                )
        return self._extract_with_heuristics(payload)

    # ------------------------------------------------------------ LLM path
    def _extract_with_llm(self, message: SourceMessage) -> list[Requirement]:
        assert self._llm is not None
        answer = self._llm.generate_json(SYSTEM_PROMPT, message.content)
        raw_items: Any = answer.get("requirements")
        if not isinstance(raw_items, list):
            raise LLMError("LLM answer has no 'requirements' list.")

        results: list[Requirement] = []
        for item in raw_items:
            try:
                parsed = _LLMRequirement.model_validate(item)
            except ValidationError as exc:
                logger.warning("Skipping invalid LLM requirement: %s", exc)
                continue
            results.append(
                self._build(
                    message,
                    title=parsed.title,
                    description=parsed.description,
                    req_type=parsed.type,
                    priority=parsed.priority,
                    confidence=parsed.confidence,
                    snippet=parsed.snippet or parsed.description,
                )
            )
        return results

    # ------------------------------------------------------- heuristic path
    def _extract_with_heuristics(self, message: SourceMessage) -> list[Requirement]:
        results: list[Requirement] = []
        for sentence in _SENTENCE_SPLIT.split(message.content):
            sentence = sentence.strip()
            if not self._looks_like_requirement(sentence):
                continue
            cue_count = len(_CUE.findall(sentence))
            results.append(
                self._build(
                    message,
                    title=self._make_title(sentence),
                    description=sentence,
                    req_type=(
                        RequirementType.NON_FUNCTIONAL
                        if _NFR.search(sentence)
                        else RequirementType.FUNCTIONAL
                    ),
                    priority=self._priority_of(sentence),
                    confidence=min(0.4 + 0.1 * cue_count, 0.7),  # heuristics never claim >0.7
                    snippet=sentence,
                )
            )
        return results

    @staticmethod
    def _looks_like_requirement(sentence: str) -> bool:
        """A sentence qualifies if it is a statement, not tiny, and has a cue word."""
        return (
            len(sentence.split()) >= 3
            and not sentence.endswith("?")
            and _CUE.search(sentence) is not None
        )

    @staticmethod
    def _priority_of(sentence: str) -> Priority:
        if _LOW.search(sentence):
            return Priority.LOW
        if _HIGH.search(sentence):
            return Priority.HIGH
        return Priority.MEDIUM

    @staticmethod
    def _make_title(sentence: str, max_words: int = 12) -> str:
        """Short title: drop short labels and filler lead-ins, never end on a dangling word."""
        text = sentence.strip().rstrip(".!")
        # "Small change for the website: please add X" -> "please add X"
        head, separator, tail = text.partition(":")
        if separator and tail.strip() and len(head.split()) <= 6:
            text = tail.strip()
        previous = None
        while previous != text:  # remove stacked lead-ins like "Hi, we need to"
            previous = text
            text = _LEAD_IN.sub("", text).strip()
        words = text.split()
        truncated = len(words) > max_words
        words = words[:max_words]
        while truncated and words and words[-1].lower().strip(",;") in _DANGLING:
            words.pop()  # "...with a" -> "..."
        title = " ".join(words) or sentence[:60]
        title = title[:1].upper() + title[1:]
        return f"{title}\u2026" if truncated else title

    # --------------------------------------------------------------- shared
    @staticmethod
    def _build(
        message: SourceMessage,
        *,
        title: str,
        description: str,
        req_type: RequirementType,
        priority: Priority,
        confidence: float,
        snippet: str,
    ) -> Requirement:
        """Create a candidate requirement that points back to its source."""
        return Requirement(
            project_id=message.project_id,
            title=title,
            description=description,
            type=req_type,
            priority=priority,
            confidence=confidence,
            sources=[SourceReference(source_id=message.source_id, snippet=snippet)],
        )
