"""Change Log Agent: builds immutable version snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from evidence_trail.agents.base import Agent
from evidence_trail.domain.models import Requirement, RequirementVersion


@dataclass(frozen=True)
class ChangeLogInput:
    """A requirement as it is *now*, why it changed, and who changed it."""

    requirement: Requirement
    changes: str
    author: str


class ChangeLogAgent(Agent[ChangeLogInput, RequirementVersion]):
    """Creates a :class:`RequirementVersion` from the current requirement state."""

    name = "change_log_agent"

    def run(self, payload: ChangeLogInput) -> RequirementVersion:
        req = payload.requirement
        return RequirementVersion(
            requirement_id=req.requirement_id,
            version_number=req.version,
            changes=payload.changes,
            author=payload.author,
            snapshot={
                "title": req.title,
                "description": req.description,
                "type": req.type.value,
                "priority": req.priority.value,
                "status": req.status.value,
                "confidence": req.confidence,
                "source_ids": req.source_ids,
            },
        )
