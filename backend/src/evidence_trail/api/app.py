"""FastAPI application factory and routes."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from evidence_trail.api import schemas
from evidence_trail.config import Settings
from evidence_trail.container import Container, build_container
from evidence_trail.domain.enums import Channel, RequirementStatus
from evidence_trail.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    EvidenceTrailError,
    IngestionError,
    InvalidInputError,
    InvalidStateTransitionError,
    NotFoundError,
    RateLimitError,
)
from evidence_trail.domain.models import Project, Requirement, User
from evidence_trail.ingestion.file_extractor import MAX_UPLOAD_BYTES
from evidence_trail.llm.base import LLMClient
from evidence_trail.services.evidence_service import EvidenceTrail

logger = logging.getLogger(__name__)

# Channels whose raw input is plain text (WhatsApp uses its own JSON webhook route).
_TEXT_CHANNELS = {
    "email": Channel.EMAIL,
    "transcript": Channel.MEETING_TRANSCRIPT,
    "document": Channel.DOCUMENT,
}


def get_container(request: Request) -> Container:
    """FastAPI dependency: the container is stored on ``app.state`` by the factory."""
    container: Container = request.app.state.container
    return container


Services = Annotated[Container, Depends(get_container)]

MAX_FILES_PER_UPLOAD = 10


def get_current_user(
    request: Request, svc: Services, authorization: Annotated[str | None, Header()] = None
) -> User:
    """FastAPI dependency: the user behind the ``Authorization: Bearer <token>`` header."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthenticationError("Please sign in to continue.")
    return svc.auth.authenticate(token.strip())


CurrentUser = Annotated[User, Depends(get_current_user)]


def owned_project(svc: Container, user: User, project_id: str) -> Project:
    """Return the project if ``user`` owns it; otherwise behave as if it does not exist."""
    project = svc.repository.get_project(project_id)
    if project.owner_id != user.user_id:
        raise NotFoundError(f"Project '{project_id}' not found.")
    return project


def owned_requirement(svc: Container, user: User, requirement_id: str) -> Requirement:
    """Return the requirement if it belongs to one of ``user``'s projects."""
    requirement = svc.repository.get_requirement(requirement_id)
    owned_project(svc, user, requirement.project_id)
    return requirement


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    """Build the application.

    Args:
        settings: Defaults to :meth:`Settings.from_env`.
        llm: Optional LLM override (used by tests).
    """
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="AI Requirements Evidence Trail System",
        version="0.1.0",
        description="Turns scattered client communication into verified, traceable requirements.",
    )
    app.state.container = build_container(settings, llm)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # -- error mapping: domain exceptions -> HTTP status codes -----------------
    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidStateTransitionError)
    async def _conflict(_: Request, exc: InvalidStateTransitionError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(AuthenticationError)
    async def _unauthenticated(_: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(
            status_code=401, content={"detail": str(exc)}, headers={"WWW-Authenticate": "Bearer"}
        )

    @app.exception_handler(ConflictError)
    async def _duplicate(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(RateLimitError)
    async def _too_many(_: Request, exc: RateLimitError) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc)})

    @app.exception_handler(InvalidInputError)
    async def _invalid(_: Request, exc: InvalidInputError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(IngestionError)
    async def _bad_input(_: Request, exc: IngestionError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(EvidenceTrailError)
    async def _domain_error(_: Request, exc: EvidenceTrailError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # -- routes ----------------------------------------------------------------
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # -- accounts --------------------------------------------------------------
    @app.post("/auth/signup", response_model=schemas.AuthResponse, status_code=201)
    def signup(body: schemas.SignupRequest, svc: Services) -> schemas.AuthResponse:
        user, token = svc.auth.signup(body.name, body.email, body.password)
        return schemas.AuthResponse(token=token, user=schemas.UserPublic.from_user(user))

    @app.post("/auth/login", response_model=schemas.AuthResponse)
    def login(body: schemas.LoginRequest, svc: Services) -> schemas.AuthResponse:
        user, token = svc.auth.login(body.email, body.password)
        return schemas.AuthResponse(token=token, user=schemas.UserPublic.from_user(user))

    @app.get("/auth/me", response_model=schemas.UserPublic)
    def me(user: CurrentUser) -> schemas.UserPublic:
        return schemas.UserPublic.from_user(user)

    @app.get("/me/dashboard", response_model=schemas.MeResponse)
    def account_dashboard(user: CurrentUser, svc: Services) -> schemas.MeResponse:
        return schemas.MeResponse(
            user=schemas.UserPublic.from_user(user), dashboard=svc.accounts.dashboard(user)
        )

    # -- projects --------------------------------------------------------------
    @app.post("/projects", response_model=Project, status_code=201)
    def create_project(body: schemas.ProjectCreate, user: CurrentUser, svc: Services) -> Project:
        return svc.projects.create(body.name, body.client, user.user_id)

    @app.get("/projects", response_model=list[Project])
    def list_projects(user: CurrentUser, svc: Services) -> list[Project]:
        return svc.projects.list(user.user_id)

    @app.get("/projects/{project_id}/dashboard")
    def dashboard(project_id: str, user: CurrentUser, svc: Services) -> dict[str, object]:
        owned_project(svc, user, project_id)
        return svc.projects.dashboard(project_id)

    @app.post(
        "/projects/{project_id}/ingest/{channel}",
        response_model=schemas.IngestResponse,
    )
    def ingest_text(
        project_id: str,
        channel: str,
        body: schemas.IngestRequest,
        user: CurrentUser,
        svc: Services,
    ) -> schemas.IngestResponse:
        owned_project(svc, user, project_id)
        if channel not in _TEXT_CHANNELS:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown channel '{channel}'. Use one of {sorted(_TEXT_CHANNELS)}.",
            )
        result = svc.pipeline.ingest(
            project_id,
            _TEXT_CHANNELS[channel],
            body.content,
            sender=body.sender,
            timestamp=body.timestamp,
        )
        return _to_ingest_response(result)

    @app.post("/projects/{project_id}/webhooks/whatsapp", response_model=schemas.IngestResponse)
    def ingest_whatsapp(
        project_id: str, payload: dict[str, Any], user: CurrentUser, svc: Services
    ) -> schemas.IngestResponse:
        """Accepts an official WhatsApp Business Cloud API webhook payload."""
        owned_project(svc, user, project_id)
        return _to_ingest_response(svc.pipeline.ingest(project_id, Channel.WHATSAPP, payload))

    @app.post("/projects/{project_id}/upload", response_model=schemas.UploadResponse)
    def upload_files(
        project_id: str,
        user: CurrentUser,
        svc: Services,
        files: Annotated[list[UploadFile], File()],
        channel: Annotated[str | None, Form()] = None,
    ) -> schemas.UploadResponse:
        """Upload PDF, Word, text, email or caption files; each is read and processed."""
        owned_project(svc, user, project_id)
        if not files:
            raise InvalidInputError("Choose at least one file.")
        if len(files) > MAX_FILES_PER_UPLOAD:
            raise InvalidInputError(f"Upload at most {MAX_FILES_PER_UPLOAD} files at a time.")
        chosen: Channel | None = None
        if channel:
            if channel not in _TEXT_CHANNELS:
                raise InvalidInputError(f"Unknown channel '{channel}'.")
            chosen = _TEXT_CHANNELS[channel]

        results: list[schemas.UploadResult] = []
        for upload in files:
            name = upload.filename or "upload"
            try:
                data = upload.file.read(MAX_UPLOAD_BYTES + 1)
                extracted = svc.files.extract(name, data, chosen)
                outcome = svc.pipeline.ingest(
                    project_id,
                    extracted.channel,
                    extracted.text,
                    sender=None if extracted.channel is Channel.EMAIL else extracted.filename,
                )
            except IngestionError as exc:  # includes FileExtractionError
                results.append(schemas.UploadResult(filename=name, ok=False, error=str(exc)))
                continue
            results.append(
                schemas.UploadResult(
                    filename=extracted.filename,
                    ok=True,
                    channel=extracted.channel.value,
                    characters=len(extracted.text),
                    created_requirements=outcome.created,
                    updated_requirements=outcome.updated,
                    failed_sources=outcome.failed_sources,
                )
            )
        return schemas.UploadResponse(
            results=results, supported_types=svc.files.supported_extensions
        )

    @app.get(
        "/projects/{project_id}/requirements",
        response_model=list[schemas.RequirementListItem],
    )
    def list_requirements(
        project_id: str,
        user: CurrentUser,
        svc: Services,
        status: RequirementStatus | None = None,
        q: str | None = None,
    ) -> list[schemas.RequirementListItem]:
        """List requirements, optionally filtered by status and a text search ``q``."""
        owned_project(svc, user, project_id)
        items = svc.repository.list_requirements(project_id, status)
        if q:
            needle = q.lower()
            items = [r for r in items if needle in f"{r.title} {r.description}".lower()]
        return [
            schemas.RequirementListItem(
                **item.model_dump(),
                open_findings=len(svc.repository.list_findings(item.requirement_id)),
            )
            for item in items
        ]

    @app.get("/requirements/{requirement_id}", response_model=schemas.RequirementDetail)
    def get_requirement(
        requirement_id: str, user: CurrentUser, svc: Services
    ) -> schemas.RequirementDetail:
        requirement = owned_requirement(svc, user, requirement_id)
        return schemas.RequirementDetail(
            requirement=requirement,
            findings=svc.repository.list_findings(requirement_id),
            sources=[svc.repository.get_source(sid) for sid in requirement.source_ids],
        )

    @app.get("/requirements/{requirement_id}/trail", response_model=EvidenceTrail)
    def get_trail(requirement_id: str, user: CurrentUser, svc: Services) -> EvidenceTrail:
        owned_requirement(svc, user, requirement_id)
        return svc.evidence.get_trail(requirement_id)

    @app.post("/requirements/{requirement_id}/review", response_model=Requirement)
    def review(
        requirement_id: str, body: schemas.ReviewRequest, user: CurrentUser, svc: Services
    ) -> Requirement:
        owned_requirement(svc, user, requirement_id)
        return svc.review.review(
            requirement_id,
            actor=user.name,
            decision=body.decision,
            edited_title=body.edited_title,
            edited_description=body.edited_description,
            note=body.note,
        )

    @app.get(
        "/requirements/{requirement_id}/confirmation-draft",
        response_model=schemas.ConfirmationDraftResponse,
    )
    def confirmation_draft(
        requirement_id: str, user: CurrentUser, svc: Services
    ) -> schemas.ConfirmationDraftResponse:
        owned_requirement(svc, user, requirement_id)
        return schemas.ConfirmationDraftResponse(
            requirement_id=requirement_id, draft=svc.confirmation.draft(requirement_id)
        )

    @app.post("/requirements/{requirement_id}/confirmation", response_model=Requirement)
    def confirmation(
        requirement_id: str, body: schemas.ConfirmationRequest, user: CurrentUser, svc: Services
    ) -> Requirement:
        owned_requirement(svc, user, requirement_id)
        return svc.confirmation.record_response(
            requirement_id, body.response, note=body.note, actor=body.actor
        )

    return app


def _to_ingest_response(result: Any) -> schemas.IngestResponse:
    """Map a ``PipelineResult`` to its HTTP representation."""
    return schemas.IngestResponse(
        source_ids=[s.source_id for s in result.sources],
        created_requirements=result.created,
        updated_requirements=result.updated,
        failed_sources=result.failed_sources,
    )
