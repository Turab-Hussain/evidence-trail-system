"""Domain-specific exception hierarchy.

A single base class (:class:`EvidenceTrailError`) lets callers, such as the API
layer, translate any expected failure into a clean response without catching
unrelated bugs.
"""

from __future__ import annotations


class EvidenceTrailError(Exception):
    """Base class for all expected, domain-level errors."""


class NotFoundError(EvidenceTrailError):
    """Raised when an entity does not exist."""


class InvalidStateTransitionError(EvidenceTrailError):
    """Raised when a requirement is moved to a status that is not allowed."""


class IngestionError(EvidenceTrailError):
    """Raised when raw input cannot be parsed into source messages."""


class LLMError(EvidenceTrailError):
    """Raised when an LLM call fails or returns unusable output."""


class AuthenticationError(EvidenceTrailError):
    """Raised for a missing, expired or invalid credential (HTTP 401)."""


class ConflictError(EvidenceTrailError):
    """Raised when a request clashes with existing data, e.g. a duplicate email (HTTP 409)."""


class RateLimitError(EvidenceTrailError):
    """Raised when too many attempts are made in a short time (HTTP 429)."""


class FileExtractionError(IngestionError):
    """Raised when an uploaded file is unsupported, too large, empty or unreadable."""


class InvalidInputError(EvidenceTrailError):
    """Raised when a request is well-formed but its values are not acceptable (HTTP 422)."""
