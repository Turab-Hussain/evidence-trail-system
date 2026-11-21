"""Builds the AI Requirement Evidence Trail: the connected journey of a requirement."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel

from evidence_trail.domain.enums import RequirementStatus
from evidence_trail.repositories.base import Repository


class TrailEntry(BaseModel):
    """One line of the timeline."""

    timestamp: datetime
    kind: str  # source | ai_step | ambiguity | pm_decision | client_confirmation | version
    actor: str
    summary: str
    reference: str | None = None


class EvidenceTrail(BaseModel):
    """Chronological trail plus a completeness verdict."""

    requirement_id: str
    entries: list[TrailEntry]
    complete: bool
    missing: list[str]


class EvidenceTrailService:
    """Read-only view that joins sources, findings, decisions and versions."""

    def __init__(self, repository: Repository) -> None:
        self._repo = repository

    @staticmethod
    def _kind_of(step: str, actor: str) -> str:
        """Classify an evidence record for display."""
        if step.startswith("pm_"):
            return "pm_decision"
        if step.startswith("client_"):
            return "client_confirmation"
        return "ai_step" if actor == "system" else "other"

    def get_trail(self, requirement_id: str) -> EvidenceTrail:
        """Assemble the chronological trail for one requirement."""
        requirement = self._repo.get_requirement(requirement_id)
        entries: list[TrailEntry] = []
        missing: list[str] = []

        evidence = self._repo.list_evidence(requirement_id=requirement_id)
        snippet_by_source: dict[str, str] = {}
        for ref in requirement.sources:
            snippet_by_source.setdefault(ref.source_id, ref.snippet)

        # Original client messages (the evidence itself).
        for source_id in requirement.source_ids:
            try:
                source = self._repo.get_source(source_id)
            except Exception:  # noqa: BLE001 - any failure means evidence is not retrievable
                missing.append(f"source {source_id} not retrievable")
                continue
            entries.append(
                TrailEntry(
                    timestamp=source.timestamp,
                    kind="source",
                    actor=source.sender or source.channel.value,
                    # The exact supporting text, not an arbitrary prefix of the message.
                    summary=(
                        f"[{source.channel.value}] "
                        f"{snippet_by_source.get(source_id, source.content)[:300]}"
                    ),
                    reference=source.evidence_uri,
                )
            )

        for record in evidence:
            entries.append(
                TrailEntry(
                    timestamp=record.timestamp,
                    kind=self._kind_of(record.transformation_step, record.actor),
                    actor=record.actor,
                    summary=f"{record.transformation_step}: {record.detail}".rstrip(": "),
                    reference=record.output_ref,
                )
            )

        # Findings carry no time of their own: place them right after the check that
        # produced them (not at the requirement's last-updated time, which moves).
        checked = [r.timestamp for r in evidence if r.transformation_step == "ambiguity_checked"]
        finding_time = (
            max(checked) + timedelta(microseconds=1) if checked else requirement.created_at
        )
        for finding in self._repo.list_findings(requirement_id):
            entries.append(
                TrailEntry(
                    timestamp=finding_time,
                    kind="ambiguity",
                    actor="system",
                    summary=f"{finding.issue_type.value}: {finding.explanation}",
                    reference=finding.finding_id,
                )
            )

        for version in self._repo.list_versions(requirement_id):
            entries.append(
                TrailEntry(
                    timestamp=version.timestamp,
                    kind="version",
                    actor=version.author,
                    summary=f"v{version.version_number}: {version.changes}",
                    reference=version.version_id,
                )
            )

        # Completeness rule from the proposal: a finalised requirement must link to
        # valid sources AND to the decision events that finalised it.
        if not requirement.sources:
            missing.append("no source evidence")
        if requirement.status in (RequirementStatus.APPROVED, RequirementStatus.CONFIRMED):
            if not self._repo.list_review_events(requirement_id):
                missing.append("no PM review event")
        if requirement.status is RequirementStatus.CONFIRMED:
            if not self._repo.list_confirmations(requirement_id):
                missing.append("no client confirmation event")

        entries.sort(key=lambda entry: entry.timestamp)
        return EvidenceTrail(
            requirement_id=requirement_id,
            entries=entries,
            complete=not missing,
            missing=missing,
        )
