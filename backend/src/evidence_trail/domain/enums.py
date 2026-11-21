"""Enumerations shared across the domain layer.

Using ``str`` mix-ins keeps the values JSON/DB friendly while still giving us
type-safe comparisons in code.
"""

from __future__ import annotations

from enum import StrEnum


class Channel(StrEnum):
    """Communication channel a source message arrived through."""

    EMAIL = "email"
    WHATSAPP = "whatsapp"
    MEETING_TRANSCRIPT = "meeting_transcript"
    DOCUMENT = "document"


class RequirementType(StrEnum):
    """Broad classification of a requirement."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"


class Priority(StrEnum):
    """Relative importance of a requirement."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RequirementStatus(StrEnum):
    """Lifecycle state of a requirement (see ``Requirement.transition_to``)."""

    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONFIRMED = "confirmed"
    CHANGES_REQUESTED = "changes_requested"


class AmbiguityType(StrEnum):
    """Kinds of ambiguity the Ambiguity Detection Agent can report."""

    VAGUE_TERM = "vague_term"
    MISSING_CONSTRAINT = "missing_constraint"
    CONFLICT = "conflict"


class ReviewDecision(StrEnum):
    """Decision a project manager can take on an AI-generated requirement."""

    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


class ClientResponse(StrEnum):
    """Outcome of a client confirmation request."""

    CONFIRMED = "confirmed"
    CHANGES_REQUESTED = "changes_requested"
