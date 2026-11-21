"""Project management (thin service so the API never touches the repository directly)."""

from __future__ import annotations

from collections import Counter

from evidence_trail.domain.enums import AmbiguityType
from evidence_trail.domain.models import Project
from evidence_trail.repositories.base import Repository


class ProjectService:
    """Create/list projects and compute dashboard figures."""

    def __init__(self, repository: Repository) -> None:
        self._repo = repository

    def create(self, name: str, client: str, owner_id: str | None = None) -> Project:
        return self._repo.save_project(Project(name=name, client=client, owner_id=owner_id))

    def list(self, owner_id: str | None = None) -> list[Project]:
        return self._repo.list_projects(owner_id)

    def dashboard(self, project_id: str) -> dict[str, object]:
        """Counts used by the dashboard view."""
        self._repo.get_project(project_id)
        requirements = self._repo.list_requirements(project_id)
        by_status = Counter(req.status.value for req in requirements)
        ambiguity = Counter[str]()
        for req in requirements:
            for finding in self._repo.list_findings(req.requirement_id):
                ambiguity[finding.issue_type.value] += 1
        return {
            "project_id": project_id,
            "total_requirements": len(requirements),
            "total_sources": len(self._repo.list_sources(project_id)),
            "by_status": dict(by_status),
            "open_ambiguities": {t.value: ambiguity.get(t.value, 0) for t in AmbiguityType},
        }
