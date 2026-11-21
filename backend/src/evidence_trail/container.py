"""Composition root: the one place where concrete classes are wired together."""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass

from evidence_trail.agents import (
    AmbiguityDetectionAgent,
    ChangeLogAgent,
    ConfirmationDraftAgent,
    ConsolidationAgent,
    RequirementExtractionAgent,
)
from evidence_trail.config import Settings
from evidence_trail.ingestion.file_extractor import FileExtractorRegistry
from evidence_trail.ingestion.registry import IngestorRegistry
from evidence_trail.llm.base import LLMClient
from evidence_trail.repositories.base import Repository
from evidence_trail.repositories.sqlite_repository import SQLiteRepository
from evidence_trail.services.account_service import AccountService
from evidence_trail.services.auth_service import AuthService
from evidence_trail.services.confirmation_service import ConfirmationService
from evidence_trail.services.evidence_service import EvidenceTrailService
from evidence_trail.services.pipeline import RequirementPipeline
from evidence_trail.services.project_service import ProjectService
from evidence_trail.services.review_service import ReviewService
from evidence_trail.services.security import PasswordHasher, TokenService

logger = logging.getLogger(__name__)


@dataclass
class Container:
    """Holds every long-lived service instance."""

    repository: Repository
    pipeline: RequirementPipeline
    review: ReviewService
    confirmation: ConfirmationService
    evidence: EvidenceTrailService
    projects: ProjectService
    auth: AuthService
    accounts: AccountService
    files: FileExtractorRegistry


def build_llm(settings: Settings) -> LLMClient | None:
    """Create the configured LLM client, or ``None`` for offline heuristics."""
    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("EVIDENCE_LLM_PROVIDER=gemini requires GEMINI_API_KEY.")
        from evidence_trail.llm.gemini_client import (  # noqa: PLC0415
            DEFAULT_GEMINI_MODEL,
            GeminiLLMClient,
        )

        return GeminiLLMClient(settings.gemini_api_key, settings.llm_model or DEFAULT_GEMINI_MODEL)
    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("EVIDENCE_LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY.")
        from evidence_trail.llm.anthropic_client import AnthropicLLMClient  # noqa: PLC0415

        return AnthropicLLMClient(
            settings.anthropic_api_key, settings.llm_model or "claude-sonnet-5-5"
        )
    if settings.llm_provider != "none":
        raise ValueError(f"Unknown LLM provider '{settings.llm_provider}'.")
    logger.info("No LLM configured: extraction uses offline heuristics.")
    return None


def build_container(settings: Settings, llm: LLMClient | None = None) -> Container:
    """Wire repositories, agents and services together.

    Args:
        settings: Runtime configuration.
        llm: Optional pre-built LLM client (handy for tests); overrides settings.
    """
    repository = SQLiteRepository(settings.db_path)
    changelog = ChangeLogAgent()
    pipeline = RequirementPipeline(
        repository=repository,
        ingestors=IngestorRegistry(),
        extraction=RequirementExtractionAgent(llm if llm is not None else build_llm(settings)),
        ambiguity=AmbiguityDetectionAgent(),
        consolidation=ConsolidationAgent(settings.similarity_threshold),
        changelog=changelog,
    )
    signing_key = settings.secret_key or repository.get_or_create_secret(
        "token_signing_key", lambda: secrets.token_hex(32)
    )
    return Container(
        repository=repository,
        pipeline=pipeline,
        review=ReviewService(repository, changelog),
        confirmation=ConfirmationService(repository, ConfirmationDraftAgent(), changelog),
        evidence=EvidenceTrailService(repository),
        projects=ProjectService(repository),
        auth=AuthService(
            repository, PasswordHasher(), TokenService(signing_key, settings.token_ttl_hours * 3600)
        ),
        accounts=AccountService(repository),
        files=FileExtractorRegistry(),
    )
