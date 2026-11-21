"""Orchestrates ingestion -> extraction -> ambiguity -> consolidation -> versioning.

This is the only place that knows the *order* of the agents.  Each step writes
an :class:`EvidenceRecord`, so the full journey of every requirement can be
reconstructed later (see :class:`EvidenceTrailService`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from evidence_trail.agents import (
    AmbiguityDetectionAgent,
    ChangeLogAgent,
    ChangeLogInput,
    ConsolidationAgent,
    ConsolidationInput,
    RequirementExtractionAgent,
)
from evidence_trail.domain.enums import Channel, RequirementStatus
from evidence_trail.domain.models import EvidenceRecord, Requirement, SourceMessage
from evidence_trail.ingestion.registry import IngestorRegistry
from evidence_trail.repositories.base import Repository

logger = logging.getLogger(__name__)

SYSTEM_ACTOR = "system"


@dataclass
class PipelineResult:
    """Summary of one pipeline run (returned by the API)."""

    sources: list[SourceMessage] = field(default_factory=list)
    created: list[str] = field(default_factory=list)  # new requirement IDs
    updated: list[str] = field(default_factory=list)  # merged requirement IDs
    failed_sources: list[str] = field(default_factory=list)  # kept, but not processed


class RequirementPipeline:
    """Runs raw channel input through the agent chain and persists everything."""

    def __init__(
        self,
        repository: Repository,
        ingestors: IngestorRegistry,
        extraction: RequirementExtractionAgent,
        ambiguity: AmbiguityDetectionAgent,
        consolidation: ConsolidationAgent,
        changelog: ChangeLogAgent,
    ) -> None:
        self._repo = repository
        self._ingestors = ingestors
        self._extraction = extraction
        self._ambiguity = ambiguity
        self._consolidation = consolidation
        self._changelog = changelog

    # ------------------------------------------------------------------ API
    def ingest(
        self,
        project_id: str,
        channel: Channel,
        raw: Any,
        *,
        sender: str | None = None,
        timestamp: datetime | None = None,
    ) -> PipelineResult:
        """Parse ``raw`` for ``channel`` and process every resulting message."""
        self._repo.get_project(project_id)  # raises NotFoundError for unknown projects
        messages = self._ingestors.get(channel).ingest(
            raw, project_id, sender=sender, timestamp=timestamp
        )

        result = PipelineResult()
        for message in messages:
            # Persist evidence FIRST so a later failure can never lose it.
            self._repo.save_source(message)
            self._record(message.source_id, None, "ingested", message.evidence_uri)
            result.sources.append(message)
            try:
                self._process_message(message, result)
            except Exception:  # noqa: BLE001 - one bad message must not stop the batch
                logger.exception("Processing failed for source %s", message.source_id)
                result.failed_sources.append(message.source_id)
        return result

    # -------------------------------------------------------------- internals
    def _process_message(self, message: SourceMessage, result: PipelineResult) -> None:
        """Extract candidates from one message and consolidate each of them."""
        candidates = self._extraction.run(message)
        self._record(
            message.source_id,
            None,
            "extracted",
            f"{len(candidates)} candidate(s)",
            detail=self._extraction.name,
        )
        for candidate in candidates:
            existing = self._repo.list_requirements(message.project_id)
            match = self._consolidation.run(ConsolidationInput(candidate, existing))
            if match is None:
                self._create(candidate, message, result)
            else:
                self._merge(match, candidate, message, result)

    def _create(
        self, candidate: Requirement, message: SourceMessage, result: PipelineResult
    ) -> None:
        self._repo.save_requirement(candidate)
        self._record(
            message.source_id,
            candidate.requirement_id,
            "requirement_created",
            candidate.requirement_id,
            detail=f"version {candidate.version}",
        )
        self._analyse(candidate)
        self._snapshot(candidate, f"Created from {message.channel.value} message", SYSTEM_ACTOR)
        result.created.append(candidate.requirement_id)

    def _merge(
        self,
        target: Requirement,
        candidate: Requirement,
        message: SourceMessage,
        result: PipelineResult,
    ) -> None:
        if not self._consolidation.merge(target, candidate):
            # Duplicate of something we already know: still link the evidence.
            self._record(
                message.source_id,
                target.requirement_id,
                "duplicate_linked",
                target.requirement_id,
            )
            return

        target.version += 1
        if target.status is not RequirementStatus.PENDING_APPROVAL:
            target.transition_to(RequirementStatus.PENDING_APPROVAL)  # new info -> re-review
        self._repo.save_requirement(target)
        self._analyse(target)
        self._snapshot(
            target, f"Merged evidence from {message.channel.value} message", SYSTEM_ACTOR
        )
        self._record(
            message.source_id,
            target.requirement_id,
            "requirement_merged",
            target.requirement_id,
            detail=f"now version {target.version}",
        )
        if target.requirement_id not in result.updated:
            result.updated.append(target.requirement_id)

    def _analyse(self, requirement: Requirement) -> None:
        """(Re)run ambiguity detection and store the findings."""
        findings = self._ambiguity.run(requirement)
        self._repo.replace_findings(requirement.requirement_id, findings)
        self._record(
            None,
            requirement.requirement_id,
            "ambiguity_checked",
            requirement.requirement_id,
            detail=f"{len(findings)} finding(s)",
        )

    def _snapshot(self, requirement: Requirement, changes: str, author: str) -> None:
        version = self._changelog.run(ChangeLogInput(requirement, changes, author))
        self._repo.save_version(version)

    def _record(
        self,
        source_id: str | None,
        requirement_id: str | None,
        step: str,
        output_ref: str,
        *,
        detail: str = "",
    ) -> None:
        self._repo.save_evidence(
            EvidenceRecord(
                source_id=source_id,
                requirement_id=requirement_id,
                transformation_step=step,
                output_ref=output_ref,
                detail=detail,
            )
        )
