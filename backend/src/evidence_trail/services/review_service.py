"""Human-in-the-loop review: PM approves, edits or rejects AI output."""

from __future__ import annotations

from evidence_trail.agents import ChangeLogAgent, ChangeLogInput
from evidence_trail.domain.enums import RequirementStatus, ReviewDecision
from evidence_trail.domain.exceptions import EvidenceTrailError
from evidence_trail.domain.models import EvidenceRecord, Requirement, ReviewEvent
from evidence_trail.repositories.base import Repository


class ReviewService:
    """Applies a PM decision and records who decided what, and when."""

    def __init__(self, repository: Repository, changelog: ChangeLogAgent) -> None:
        self._repo = repository
        self._changelog = changelog

    def review(
        self,
        requirement_id: str,
        *,
        actor: str,
        decision: ReviewDecision,
        edited_title: str | None = None,
        edited_description: str | None = None,
        note: str | None = None,
    ) -> Requirement:
        """Apply ``decision`` to a requirement and return the updated entity.

        Raises:
            NotFoundError: unknown requirement.
            InvalidStateTransitionError: the requirement is not reviewable now.
            EvidenceTrailError: an EDIT decision without any edited content.
        """
        requirement = self._repo.get_requirement(requirement_id)
        edited_content: str | None = None

        if decision is ReviewDecision.REJECT:
            requirement.transition_to(RequirementStatus.REJECTED)
            summary = "Rejected by PM"
        else:
            if decision is ReviewDecision.EDIT:
                if not (edited_title or edited_description):
                    raise EvidenceTrailError("An edit needs a new title and/or description.")
                requirement.title = edited_title or requirement.title
                requirement.description = edited_description or requirement.description
                edited_content = f"{requirement.title}: {requirement.description}"
                requirement.version += 1
            requirement.transition_to(RequirementStatus.APPROVED)
            summary = "Edited and approved by PM" if edited_content else "Approved by PM"

        self._repo.save_requirement(requirement)
        self._repo.save_review_event(
            ReviewEvent(
                requirement_id=requirement_id,
                actor=actor,
                decision=decision,
                edited_content=edited_content,
                note=note,
            )
        )
        if edited_content is not None:
            self._repo.save_version(
                self._changelog.run(ChangeLogInput(requirement, summary, actor))
            )
        self._repo.save_evidence(
            EvidenceRecord(
                requirement_id=requirement_id,
                transformation_step=f"pm_{decision.value}",
                output_ref=requirement_id,
                detail=summary,
                actor=actor,
            )
        )
        return requirement
