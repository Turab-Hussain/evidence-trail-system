"""Client confirmation workflow: draft the message, record the response."""

from __future__ import annotations

from evidence_trail.agents import (
    ChangeLogAgent,
    ChangeLogInput,
    ConfirmationDraftAgent,
    ConfirmationInput,
)
from evidence_trail.domain.enums import ClientResponse, RequirementStatus
from evidence_trail.domain.exceptions import InvalidStateTransitionError
from evidence_trail.domain.models import ConfirmationEvent, EvidenceRecord, Requirement
from evidence_trail.repositories.base import Repository


class ConfirmationService:
    """Only PM-approved requirements may be sent to (or answered by) the client."""

    def __init__(
        self,
        repository: Repository,
        drafter: ConfirmationDraftAgent,
        changelog: ChangeLogAgent,
    ) -> None:
        self._repo = repository
        self._drafter = drafter
        self._changelog = changelog

    def draft(self, requirement_id: str) -> str:
        """Return a client-ready confirmation message for an approved requirement."""
        requirement = self._repo.get_requirement(requirement_id)
        if requirement.status not in (
            RequirementStatus.APPROVED,
            RequirementStatus.CHANGES_REQUESTED,
        ):
            raise InvalidStateTransitionError(
                "Only PM-approved requirements can be sent for client confirmation."
            )
        findings = self._repo.list_findings(requirement_id)
        return self._drafter.run(ConfirmationInput(requirement, findings))

    def record_response(
        self,
        requirement_id: str,
        response: ClientResponse,
        *,
        note: str | None = None,
        actor: str = "client",
    ) -> Requirement:
        """Store the client's answer and move the requirement accordingly."""
        requirement = self._repo.get_requirement(requirement_id)
        target = (
            RequirementStatus.CONFIRMED
            if response is ClientResponse.CONFIRMED
            else RequirementStatus.CHANGES_REQUESTED
        )
        requirement.transition_to(target)  # raises if the requirement is not APPROVED
        self._repo.save_requirement(requirement)
        self._repo.save_confirmation(
            ConfirmationEvent(
                requirement_id=requirement_id,
                client_response=response,
                note=note,
                actor=actor,
            )
        )
        self._repo.save_version(
            self._changelog.run(
                ChangeLogInput(requirement, f"Client response: {response.value}", actor)
            )
        )
        self._repo.save_evidence(
            EvidenceRecord(
                requirement_id=requirement_id,
                transformation_step=f"client_{response.value}",
                output_ref=requirement_id,
                detail=note or "",
                actor=actor,
            )
        )
        return requirement
