"""HTTP request/response models (kept separate from domain entities)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from evidence_trail.domain.enums import ClientResponse, ReviewDecision
from evidence_trail.domain.models import AmbiguityFinding, Requirement, SourceMessage, User
from evidence_trail.services.account_service import AccountDashboard


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class UserPublic(BaseModel):
    """The account fields that are safe to send to the browser."""

    user_id: str
    name: str
    email: str
    created_at: datetime
    last_login_at: datetime | None

    @classmethod
    def from_user(cls, user: User) -> UserPublic:
        return cls(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


class MeResponse(BaseModel):
    """Profile plus dashboard figures, so one request fills the dashboard screen."""

    user: UserPublic
    dashboard: AccountDashboard


class UploadResult(BaseModel):
    """Outcome for one uploaded file; a failed file never blocks the others."""

    filename: str
    ok: bool
    channel: str | None = None
    characters: int = 0
    error: str | None = None
    created_requirements: list[str] = []
    updated_requirements: list[str] = []
    failed_sources: list[str] = []


class UploadResponse(BaseModel):
    results: list[UploadResult]
    supported_types: list[str]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    client: str = Field(min_length=1, max_length=200)


class IngestRequest(BaseModel):
    """Payload for email / transcript / document ingestion."""

    content: str = Field(min_length=1)
    sender: str | None = None
    timestamp: datetime | None = None


class IngestResponse(BaseModel):
    source_ids: list[str]
    created_requirements: list[str]
    updated_requirements: list[str]
    failed_sources: list[str]


class ReviewRequest(BaseModel):
    """The reviewer is always the signed-in user, so no ``actor`` is accepted."""

    decision: ReviewDecision
    edited_title: str | None = None
    edited_description: str | None = None
    note: str | None = None


class ConfirmationRequest(BaseModel):
    response: ClientResponse
    note: str | None = None
    actor: str = "client"


class ConfirmationDraftResponse(BaseModel):
    requirement_id: str
    draft: str


class RequirementListItem(Requirement):
    """A requirement plus the number of open ambiguity findings (for list views)."""

    open_findings: int = 0


class RequirementDetail(BaseModel):
    """Everything the review screen needs for one requirement."""

    requirement: Requirement
    findings: list[AmbiguityFinding]
    sources: list[SourceMessage]  # full original messages, in citation order
