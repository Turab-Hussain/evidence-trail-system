"""Schema-level tests: constraints, foreign keys, persistence."""

import sqlite3
from pathlib import Path

import pytest

from evidence_trail.config import Settings
from evidence_trail.container import build_container
from evidence_trail.domain import enums
from evidence_trail.domain.enums import Channel, ClientResponse, ReviewDecision
from evidence_trail.domain.exceptions import NotFoundError
from evidence_trail.domain.models import EvidenceRecord, Requirement, SourceMessage
from evidence_trail.init_db import init_db
from evidence_trail.repositories.sqlite_repository import SCHEMA_PATH, SQLiteRepository


def test_schema_check_constraints_match_enums() -> None:
    """Fails if someone adds an enum value but forgets the CHECK list in schema.sql."""
    ddl = SCHEMA_PATH.read_text(encoding="utf-8")
    for enum_cls in (
        enums.Channel,
        enums.RequirementType,
        enums.Priority,
        enums.RequirementStatus,
        enums.AmbiguityType,
        enums.ReviewDecision,
        enums.ClientResponse,
    ):
        for member in enum_cls:
            assert f"'{member.value}'" in ddl, (
                f"{enum_cls.__name__}.{member.name} missing in schema"
            )


def test_foreign_keys_are_enforced() -> None:
    repo = SQLiteRepository(":memory:")
    orphan = SourceMessage(project_id="missing-project", channel=Channel.EMAIL, content="x")
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_source(orphan)
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_evidence(
            EvidenceRecord(requirement_id="nope", transformation_step="s", output_ref="r")
        )


def test_requirement_cannot_cite_unknown_source() -> None:
    from evidence_trail.domain.models import Project, SourceReference

    repo = SQLiteRepository(":memory:")
    project = repo.save_project(Project(name="p", client="c"))
    req = Requirement(
        project_id=project.project_id,
        title="t",
        description="d",
        sources=[SourceReference(source_id="ghost", snippet="s")],
    )
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_requirement(req)
    assert repo.list_requirements(project.project_id) == []  # transaction rolled back


def test_invalid_enum_value_rejected_by_database() -> None:
    repo = SQLiteRepository(":memory:")
    with pytest.raises(sqlite3.IntegrityError):
        repo._conn.execute("INSERT INTO projects (project_id, name, client) VALUES ('p','n','c')")
        repo._conn.execute(
            "INSERT INTO source_messages VALUES ('s','p','fax','2026-01-01','a',NULL,'x','u')"
        )


def test_data_survives_reopen(tmp_path: Path) -> None:
    db = str(tmp_path / "trail.db")
    first = build_container(Settings(db_path=db))
    pid = first.projects.create("Shop", "Acme").project_id
    req_id = first.pipeline.ingest(pid, Channel.DOCUMENT, "We need a login page.").created[0]
    first.review.review(req_id, actor="pm", decision=ReviewDecision.APPROVE)
    first.confirmation.record_response(req_id, ClientResponse.CONFIRMED)
    first.repository.close()  # type: ignore[attr-defined]

    second = build_container(Settings(db_path=db))
    req = second.repository.get_requirement(req_id)
    assert req.status.value == "confirmed" and req.source_ids
    trail = second.evidence.get_trail(req_id)
    assert trail.complete and len(second.repository.list_versions(req_id)) >= 2


def test_source_order_and_snippets_roundtrip() -> None:
    container = build_container(Settings(db_path=":memory:"))
    pid = container.projects.create("p", "c").project_id
    container.pipeline.ingest(pid, Channel.DOCUMENT, "We need JazzCash payment option.")
    container.pipeline.ingest(
        pid, Channel.EMAIL, "Subject: x\n\nWe want the JazzCash payment option urgently."
    )
    [req] = container.repository.list_requirements(pid)
    assert [r.snippet.split()[0] for r in req.sources] == ["We", "We"]
    assert len(req.sources) == 2


def test_get_missing_raises() -> None:
    with pytest.raises(NotFoundError):
        SQLiteRepository(":memory:").get_requirement("nope")


def test_init_db_creates_tables(tmp_path: Path) -> None:
    tables = init_db(str(tmp_path / "new.db"))
    assert {
        "projects",
        "source_messages",
        "requirements",
        "requirement_sources",
        "ambiguity_findings",
        "review_events",
        "confirmation_events",
        "requirement_versions",
        "evidence_records",
    } <= set(tables)
    init_db(str(tmp_path / "new.db"))  # idempotent


def test_replace_findings_is_atomic() -> None:
    """A failing insert must not leave the old findings deleted."""
    from evidence_trail.domain.enums import AmbiguityType
    from evidence_trail.domain.models import AmbiguityFinding

    container = build_container(Settings(db_path=":memory:"))
    pid = container.projects.create("p", "c").project_id
    req_id = container.pipeline.ingest(pid, Channel.DOCUMENT, "Make the homepage premium.").created[
        0
    ]
    repo = container.repository
    before = repo.list_findings(req_id)
    assert before

    good = AmbiguityFinding(
        requirement_id=req_id,
        issue_type=AmbiguityType.VAGUE_TERM,
        explanation="e",
        clarification_question="q",
    )
    bad = AmbiguityFinding(
        requirement_id="no-such-requirement",
        issue_type=AmbiguityType.VAGUE_TERM,
        explanation="e",
        clarification_question="q",
    )
    with pytest.raises(sqlite3.IntegrityError):
        repo.replace_findings(req_id, [good, bad])
    assert [f.finding_id for f in repo.list_findings(req_id)] == [f.finding_id for f in before]
