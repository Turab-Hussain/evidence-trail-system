"""Consolidation Agent: merges duplicate / related requirements across channels."""

from __future__ import annotations

from dataclasses import dataclass

from evidence_trail.agents.base import Agent
from evidence_trail.agents.text_utils import text_similarity, tokenize
from evidence_trail.domain.enums import Priority, RequirementStatus
from evidence_trail.domain.models import Requirement

_PRIORITY_RANK = {Priority.LOW: 0, Priority.MEDIUM: 1, Priority.HIGH: 2}


@dataclass(frozen=True)
class ConsolidationInput:
    """A new candidate plus the requirements it may be merged into."""

    candidate: Requirement
    existing: list[Requirement]


class ConsolidationAgent(Agent[ConsolidationInput, Requirement | None]):
    """Finds the best existing match for a candidate (``None`` if it is new)."""

    name = "consolidation_agent"

    def __init__(self, similarity_threshold: float = 0.4) -> None:
        if not 0.0 < similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be in (0, 1].")
        self._threshold = similarity_threshold

    def run(self, payload: ConsolidationInput) -> Requirement | None:
        best: Requirement | None = None
        best_score = 0.0
        candidate_text = f"{payload.candidate.title} {payload.candidate.description}"
        for existing in payload.existing:
            if existing.status is RequirementStatus.REJECTED:
                continue  # a rejected requirement must not swallow new evidence
            score = text_similarity(candidate_text, f"{existing.title} {existing.description}")
            if score >= self._threshold and score > best_score:
                best, best_score = existing, score
        return best

    def merge(self, target: Requirement, candidate: Requirement) -> bool:
        """Fold ``candidate`` into ``target`` in place, keeping all provenance.

        Returns:
            ``True`` if anything changed (new evidence, text, priority or confidence).
        """
        changed = False

        known = {(ref.source_id, ref.snippet) for ref in target.sources}
        for ref in candidate.sources:
            if (ref.source_id, ref.snippet) not in known:
                target.sources.append(ref)
                changed = True

        # Append wording only when the candidate adds information we do not have yet.
        if tokenize(candidate.description) - tokenize(target.description):
            target.description = f"{target.description}\n{candidate.description}"
            changed = True

        if _PRIORITY_RANK[candidate.priority] > _PRIORITY_RANK[target.priority]:
            target.priority = candidate.priority
            changed = True

        if changed:
            # Agreement from another source slightly raises confidence (capped).
            target.confidence = min(max(target.confidence, candidate.confidence) + 0.05, 0.95)
            target.touch()
        return changed
