"""The signed-in user's dashboard: profile plus figures across all of their projects."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from pydantic import BaseModel

from evidence_trail.domain.enums import Channel, RequirementStatus
from evidence_trail.domain.models import Project, User
from evidence_trail.repositories.base import Repository

RECENT_ACTIVITY_LIMIT = 12
# Internal pipeline steps: shown in a requirement's own trail, but noise on a dashboard feed.
_INTERNAL_STEPS = frozenset({"extracted", "ambiguity_checked", "duplicate_linked"})


class ProjectSummary(BaseModel):
    """One row of the "your projects" table."""

    project: Project
    requirements: int
    sources: int
    by_status: dict[str, int]
    open_findings: int
    last_activity: datetime | None


class ActivityItem(BaseModel):
    """One recent step in the evidence trail, with names instead of ids."""

    timestamp: datetime
    step: str
    detail: str
    actor: str
    project_id: str
    project_name: str
    requirement_id: str | None
    requirement_title: str | None


class AccountDashboard(BaseModel):
    """Everything the dashboard screen shows."""

    projects: int
    sources: int
    requirements: int
    awaiting_review: int
    confirmed: int
    open_findings: int
    by_status: dict[str, int]
    by_channel: dict[str, int]
    project_summaries: list[ProjectSummary]
    recent_activity: list[ActivityItem]


class AccountService:
    """Aggregates a user's projects into dashboard figures."""

    def __init__(self, repository: Repository) -> None:
        self._repo = repository

    def dashboard(self, user: User) -> AccountDashboard:
        projects = self._repo.list_projects(user.user_id)
        by_status: Counter[str] = Counter({s.value: 0 for s in RequirementStatus})
        by_channel: Counter[str] = Counter({c.value: 0 for c in Channel})
        summaries: list[ProjectSummary] = []
        titles: dict[str, str] = {}
        total_sources = total_requirements = total_findings = 0

        for project in projects:
            requirements = self._repo.list_requirements(project.project_id)
            sources = self._repo.list_sources(project.project_id)
            findings = sum(len(self._repo.list_findings(r.requirement_id)) for r in requirements)
            project_status = Counter(r.status.value for r in requirements)
            by_status.update(project_status)
            by_channel.update(s.channel.value for s in sources)
            titles.update({r.requirement_id: r.title for r in requirements})
            stamps = [r.updated_at for r in requirements] + [s.timestamp for s in sources]
            summaries.append(
                ProjectSummary(
                    project=project,
                    requirements=len(requirements),
                    sources=len(sources),
                    by_status=dict(project_status),
                    open_findings=findings,
                    last_activity=max(stamps) if stamps else None,
                )
            )
            total_sources += len(sources)
            total_requirements += len(requirements)
            total_findings += findings

        return AccountDashboard(
            projects=len(projects),
            sources=total_sources,
            requirements=total_requirements,
            awaiting_review=by_status[RequirementStatus.PENDING_APPROVAL.value],
            confirmed=by_status[RequirementStatus.CONFIRMED.value],
            open_findings=total_findings,
            by_status=dict(by_status),
            by_channel=dict(by_channel),
            project_summaries=summaries,
            recent_activity=self._recent_activity(projects, titles),
        )

    def _recent_activity(
        self, projects: list[Project], titles: dict[str, str]
    ) -> list[ActivityItem]:
        names = {p.project_id: p.name for p in projects}
        items: list[ActivityItem] = []
        # Over-fetch, because internal steps are dropped below.
        newest = self._repo.list_recent_evidence(list(names), RECENT_ACTIVITY_LIMIT * 5)
        for record in newest:
            if len(items) == RECENT_ACTIVITY_LIMIT:
                break
            if record.transformation_step in _INTERNAL_STEPS:
                continue
            if record.requirement_id:
                project_id = self._repo.get_requirement(record.requirement_id).project_id
            elif record.source_id:
                project_id = self._repo.get_source(record.source_id).project_id
            else:
                continue
            items.append(
                ActivityItem(
                    timestamp=record.timestamp,
                    step=record.transformation_step,
                    detail=record.detail,
                    actor=record.actor,
                    project_id=project_id,
                    project_name=names.get(project_id, ""),
                    requirement_id=record.requirement_id,
                    requirement_title=titles.get(record.requirement_id or ""),
                )
            )
        return items
