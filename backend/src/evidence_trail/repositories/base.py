"""Abstract persistence interface.

Services depend on :class:`Repository`, never on a concrete database, so the
SQLite prototype can later be replaced by PostgreSQL without touching business
logic (Dependency Inversion Principle).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from evidence_trail.domain.enums import RequirementStatus
from evidence_trail.domain.models import (
    AmbiguityFinding,
    ConfirmationEvent,
    EvidenceRecord,
    Project,
    Requirement,
    RequirementVersion,
    ReviewEvent,
    SourceMessage,
    User,
)


class Repository(ABC):
    """Storage contract for every entity in the system."""

    # -- projects -----------------------------------------------------------
    @abstractmethod
    def save_project(self, project: Project) -> Project:
        """Insert or update a project."""

    @abstractmethod
    def get_project(self, project_id: str) -> Project:
        """Return a project or raise ``NotFoundError``."""

    @abstractmethod
    def list_projects(self, owner_id: str | None = None) -> list[Project]:
        """Return projects; with ``owner_id`` only that user's projects."""

    @abstractmethod
    def claim_orphan_projects(self, owner_id: str) -> int:
        """Give every project without an owner to ``owner_id``; return how many."""

    # -- users and secrets --------------------------------------------------
    @abstractmethod
    def save_user(self, user: User) -> User:
        """Insert or update a user."""

    @abstractmethod
    def get_user(self, user_id: str) -> User:
        """Return a user or raise ``NotFoundError``."""

    @abstractmethod
    def find_user_by_email(self, email: str) -> User | None:
        """Return the user with this email (case-insensitive) or ``None``."""

    @abstractmethod
    def count_users(self) -> int:
        """Return the number of registered users."""

    @abstractmethod
    def get_or_create_secret(self, name: str, factory: Callable[[], str]) -> str:
        """Return the stored secret, creating it with ``factory()`` on first use."""

    # -- source messages ----------------------------------------------------
    @abstractmethod
    def save_source(self, message: SourceMessage) -> SourceMessage:
        """Persist a source message (never deleted, to preserve evidence)."""

    @abstractmethod
    def get_source(self, source_id: str) -> SourceMessage:
        """Return a source message or raise ``NotFoundError``."""

    @abstractmethod
    def list_sources(self, project_id: str) -> list[SourceMessage]:
        """Return all source messages of a project."""

    # -- requirements -------------------------------------------------------
    @abstractmethod
    def save_requirement(self, requirement: Requirement) -> Requirement:
        """Insert or update a requirement."""

    @abstractmethod
    def get_requirement(self, requirement_id: str) -> Requirement:
        """Return a requirement or raise ``NotFoundError``."""

    @abstractmethod
    def list_requirements(
        self, project_id: str, status: RequirementStatus | None = None
    ) -> list[Requirement]:
        """Return a project's requirements, optionally filtered by status."""

    # -- append-only audit data --------------------------------------------
    @abstractmethod
    def save_finding(self, finding: AmbiguityFinding) -> None:
        """Persist an ambiguity finding."""

    @abstractmethod
    def replace_findings(self, requirement_id: str, findings: list[AmbiguityFinding]) -> None:
        """Replace all findings of a requirement (used when it is re-analysed)."""

    @abstractmethod
    def list_findings(self, requirement_id: str) -> list[AmbiguityFinding]:
        """Return ambiguity findings of a requirement."""

    @abstractmethod
    def save_review_event(self, event: ReviewEvent) -> None:
        """Persist a PM review event."""

    @abstractmethod
    def list_review_events(self, requirement_id: str) -> list[ReviewEvent]:
        """Return PM review events of a requirement."""

    @abstractmethod
    def save_confirmation(self, event: ConfirmationEvent) -> None:
        """Persist a client confirmation event."""

    @abstractmethod
    def list_confirmations(self, requirement_id: str) -> list[ConfirmationEvent]:
        """Return client confirmation events of a requirement."""

    @abstractmethod
    def save_version(self, version: RequirementVersion) -> None:
        """Persist a requirement version snapshot."""

    @abstractmethod
    def list_versions(self, requirement_id: str) -> list[RequirementVersion]:
        """Return version snapshots of a requirement, oldest first."""

    @abstractmethod
    def save_evidence(self, record: EvidenceRecord) -> None:
        """Persist an evidence record."""

    @abstractmethod
    def list_evidence(
        self, *, requirement_id: str | None = None, source_id: str | None = None
    ) -> list[EvidenceRecord]:
        """Return evidence records filtered by requirement and/or source."""

    @abstractmethod
    def list_recent_evidence(self, project_ids: list[str], limit: int) -> list[EvidenceRecord]:
        """Return the newest evidence records across the given projects."""
