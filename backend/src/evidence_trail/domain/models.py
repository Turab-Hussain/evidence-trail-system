"""Core domain entities (the "Core Data Objects" from the proposal).

All entities are Pydantic models, which gives us validation and cheap JSON
(de)serialisation for persistence and the HTTP API.  Behaviour that belongs to
an entity (for example the requirement state machine) lives on the entity.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import ClassVar

from pydantic import BaseModel, Field

from evidence_trail.domain.enums import (
    AmbiguityType,
    Channel,
    ClientResponse,
    Priority,
    RequirementStatus,
    RequirementType,
    ReviewDecision,
)
from evidence_trail.domain.exceptions import InvalidStateTransitionError


def new_id(prefix: str) -> str:
    """Return a short, prefixed, unique identifier such as ``req-1a2b3c4d5e6f``."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time (single place to mock in tests)."""
    return datetime.now(UTC)


class User(BaseModel):
    """A registered account. ``password_hash`` never leaves the backend."""

    user_id: str = Field(default_factory=lambda: new_id("usr"))
    name: str
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=utc_now)
    last_login_at: datetime | None = None


class Project(BaseModel):
    """A client project that groups all communication and requirements."""

    project_id: str = Field(default_factory=lambda: new_id("proj"))
    name: str
    client: str
    status: str = "active"
    owner_id: str | None = None  # the user who created it; only the owner can see it


class SourceMessage(BaseModel):
    """One normalised unit of client communication, regardless of channel."""

    source_id: str = Field(default_factory=lambda: new_id("src"))
    project_id: str
    channel: Channel
    timestamp: datetime = Field(default_factory=utc_now)
    sender: str | None = None
    sender_role: str | None = None
    content: str
    evidence_uri: str = ""

    def model_post_init(self, __context: object) -> None:
        """Derive a stable evidence URI when the caller did not supply one."""
        if not self.evidence_uri:
            self.evidence_uri = f"evidence://{self.project_id}/{self.source_id}"


class SourceReference(BaseModel):
    """Link from a requirement back to the exact text that supports it."""

    source_id: str
    snippet: str


class Requirement(BaseModel):
    """A (possibly consolidated) living requirement.

    The status field is guarded by :meth:`transition_to` so invalid lifecycle
    jumps (for example REJECTED -> CONFIRMED) cannot happen by accident.
    """

    # Allowed lifecycle moves.  Anything not listed here is rejected.
    _TRANSITIONS: ClassVar[dict[RequirementStatus, frozenset[RequirementStatus]]] = {
        RequirementStatus.PENDING_APPROVAL: frozenset(
            {RequirementStatus.APPROVED, RequirementStatus.REJECTED}
        ),
        RequirementStatus.APPROVED: frozenset(
            {
                RequirementStatus.CONFIRMED,
                RequirementStatus.CHANGES_REQUESTED,
                RequirementStatus.PENDING_APPROVAL,
            }
        ),
        RequirementStatus.CHANGES_REQUESTED: frozenset(
            {
                RequirementStatus.APPROVED,
                RequirementStatus.REJECTED,
                RequirementStatus.PENDING_APPROVAL,
            }
        ),
        RequirementStatus.CONFIRMED: frozenset({RequirementStatus.PENDING_APPROVAL}),
        RequirementStatus.REJECTED: frozenset(),
    }

    requirement_id: str = Field(default_factory=lambda: new_id("req"))
    project_id: str
    title: str
    description: str
    type: RequirementType = RequirementType.FUNCTIONAL
    priority: Priority = Priority.MEDIUM
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: RequirementStatus = RequirementStatus.PENDING_APPROVAL
    version: int = 1
    sources: list[SourceReference] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def source_ids(self) -> list[str]:
        """Distinct source IDs supporting this requirement, in first-seen order."""
        return list(dict.fromkeys(ref.source_id for ref in self.sources))

    def transition_to(self, new_status: RequirementStatus) -> None:
        """Move to ``new_status`` or raise if the transition is not allowed."""
        if new_status == self.status:
            return
        if new_status not in self._TRANSITIONS[self.status]:
            raise InvalidStateTransitionError(
                f"Cannot move requirement {self.requirement_id} "
                f"from '{self.status.value}' to '{new_status.value}'."
            )
        self.status = new_status
        self.touch()

    def touch(self) -> None:
        """Refresh ``updated_at``."""
        self.updated_at = utc_now()


class AmbiguityFinding(BaseModel):
    """A single ambiguity problem found in a requirement."""

    finding_id: str = Field(default_factory=lambda: new_id("amb"))
    requirement_id: str
    issue_type: AmbiguityType
    explanation: str
    clarification_question: str


class ReviewEvent(BaseModel):
    """A project manager's decision on a requirement (audit record)."""

    event_id: str = Field(default_factory=lambda: new_id("rev"))
    requirement_id: str
    actor: str
    decision: ReviewDecision
    edited_content: str | None = None
    note: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class ConfirmationEvent(BaseModel):
    """The client's response to a confirmation draft (audit record)."""

    confirmation_id: str = Field(default_factory=lambda: new_id("conf"))
    requirement_id: str
    client_response: ClientResponse
    note: str | None = None
    actor: str = "client"
    timestamp: datetime = Field(default_factory=utc_now)


class RequirementVersion(BaseModel):
    """Immutable snapshot of a requirement at a point in its history."""

    version_id: str = Field(default_factory=lambda: new_id("ver"))
    requirement_id: str
    version_number: int
    changes: str
    author: str
    snapshot: dict[str, object]
    timestamp: datetime = Field(default_factory=utc_now)


class EvidenceRecord(BaseModel):
    """One step in the chain from raw message to verified requirement."""

    evidence_id: str = Field(default_factory=lambda: new_id("evd"))
    source_id: str | None = None
    requirement_id: str | None = None
    transformation_step: str
    output_ref: str
    detail: str = ""
    actor: str = "system"
    timestamp: datetime = Field(default_factory=utc_now)
