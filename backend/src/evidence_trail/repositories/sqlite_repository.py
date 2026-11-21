"""SQLite implementation of :class:`Repository` on a normalised relational schema.

The DDL lives in ``schema.sql`` (tables, foreign keys, CHECK constraints,
indexes).  Table and column names used in SQL come only from the constant
``_TABLES`` specification below; every value is bound as a SQL parameter.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from evidence_trail.domain.enums import RequirementStatus
from evidence_trail.domain.exceptions import NotFoundError
from evidence_trail.domain.models import (
    AmbiguityFinding,
    ConfirmationEvent,
    EvidenceRecord,
    Project,
    Requirement,
    RequirementVersion,
    ReviewEvent,
    SourceMessage,
    SourceReference,
    User,
)
from evidence_trail.repositories.base import Repository

ModelT = TypeVar("ModelT", bound=BaseModel)

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


@dataclass(frozen=True)
class _Table:
    """Static description of one table (never built from user input)."""

    name: str
    pk: str
    columns: tuple[str, ...]  # all columns, primary key first
    model: type[BaseModel]


_TABLES: dict[str, _Table] = {
    t.name: t
    for t in (
        _Table(
            "users",
            "user_id",
            ("user_id", "name", "email", "password_hash", "created_at", "last_login_at"),
            User,
        ),
        _Table(
            "projects",
            "project_id",
            ("project_id", "name", "client", "status", "owner_id"),
            Project,
        ),
        _Table(
            "source_messages",
            "source_id",
            (
                "source_id",
                "project_id",
                "channel",
                "timestamp",
                "sender",
                "sender_role",
                "content",
                "evidence_uri",
            ),
            SourceMessage,
        ),
        _Table(
            "requirements",
            "requirement_id",
            (
                "requirement_id",
                "project_id",
                "title",
                "description",
                "type",
                "priority",
                "confidence",
                "status",
                "version",
                "created_at",
                "updated_at",
            ),
            Requirement,
        ),
        _Table(
            "ambiguity_findings",
            "finding_id",
            ("finding_id", "requirement_id", "issue_type", "explanation", "clarification_question"),
            AmbiguityFinding,
        ),
        _Table(
            "review_events",
            "event_id",
            (
                "event_id",
                "requirement_id",
                "actor",
                "decision",
                "edited_content",
                "note",
                "timestamp",
            ),
            ReviewEvent,
        ),
        _Table(
            "confirmation_events",
            "confirmation_id",
            (
                "confirmation_id",
                "requirement_id",
                "client_response",
                "note",
                "actor",
                "timestamp",
            ),
            ConfirmationEvent,
        ),
        _Table(
            "requirement_versions",
            "version_id",
            (
                "version_id",
                "requirement_id",
                "version_number",
                "changes",
                "author",
                "snapshot",
                "timestamp",
            ),
            RequirementVersion,
        ),
        _Table(
            "evidence_records",
            "evidence_id",
            (
                "evidence_id",
                "source_id",
                "requirement_id",
                "transformation_step",
                "output_ref",
                "detail",
                "actor",
                "timestamp",
            ),
            EvidenceRecord,
        ),
    )
}


class SQLiteRepository(Repository):
    """Thread-safe SQLite repository with enforced foreign keys."""

    def __init__(self, db_path: str = ":memory:") -> None:
        # One shared connection guarded by a lock; FastAPI runs sync routes in threads.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._migrate_legacy_projects_table()
            self._conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    def _migrate_legacy_projects_table(self) -> None:
        """Add ``projects.owner_id`` to databases created before user accounts existed."""
        columns = [row["name"] for row in self._conn.execute("PRAGMA table_info(projects)")]
        if columns and "owner_id" not in columns:
            self._conn.execute("ALTER TABLE projects ADD COLUMN owner_id TEXT")
            self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            self._conn.close()

    # ------------------------------------------------------------ generic CRUD
    @contextmanager
    def _transaction(self) -> Iterator[None]:
        """One atomic unit of work: commit on success, roll back on any exception.

        Never nest ``with self._conn`` blocks: sqlite3 commits at the end of *each*
        one, which would silently break atomicity.  Code inside a transaction
        must call ``_upsert_raw`` (not ``_upsert``).
        """
        with self._lock, self._conn:
            yield

    def _upsert_raw(self, table: _Table, values: dict[str, Any]) -> None:
        """INSERT, or UPDATE every non-key column on conflict. Caller owns the transaction."""
        cols = table.columns
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols[1:])
        sql = (
            f"INSERT INTO {table.name} ({', '.join(cols)}) "  # noqa: S608 - constant spec
            f"VALUES ({', '.join('?' for _ in cols)}) "
            f"ON CONFLICT({table.pk}) DO UPDATE SET {updates}"
        )
        self._conn.execute(sql, tuple(values[c] for c in cols))

    def _upsert(self, table: _Table, values: dict[str, Any]) -> None:
        """Single-statement upsert in its own transaction."""
        with self._transaction():
            self._upsert_raw(table, values)

    def _fetch(
        self, table: _Table, where: str = "", params: tuple[Any, ...] = ()
    ) -> list[sqlite3.Row]:
        """SELECT rows oldest-first. ``where`` is always a constant fragment."""
        sql = f"SELECT {', '.join(table.columns)} FROM {table.name} {where} ORDER BY rowid"  # noqa: S608
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    @staticmethod
    def _dump(model: BaseModel, **exclude: Any) -> dict[str, Any]:
        """Entity -> flat column dict (enums and datetimes become text)."""
        return model.model_dump(mode="json", exclude=set(exclude) or None)

    def _get(self, table: _Table, entity_id: str) -> sqlite3.Row:
        rows = self._fetch(table, f"WHERE {table.pk} = ?", (entity_id,))
        if not rows:
            raise NotFoundError(f"{table.model.__name__} '{entity_id}' not found.")
        return rows[0]

    def _list_by(self, table: _Table, column: str, value: str, model: type[ModelT]) -> list[ModelT]:
        assert column in table.columns  # defensive: column names are code constants
        rows = self._fetch(table, f"WHERE {column} = ?", (value,))
        return [model.model_validate(dict(row)) for row in rows]

    # --------------------------------------------------------------- projects
    def save_project(self, project: Project) -> Project:
        self._upsert(_TABLES["projects"], self._dump(project))
        return project

    def get_project(self, project_id: str) -> Project:
        return Project.model_validate(dict(self._get(_TABLES["projects"], project_id)))

    def list_projects(self, owner_id: str | None = None) -> list[Project]:
        table = _TABLES["projects"]
        if owner_id is None:
            rows = self._fetch(table)
        else:
            rows = self._fetch(table, "WHERE owner_id = ?", (owner_id,))
        return [Project.model_validate(dict(r)) for r in rows]

    def claim_orphan_projects(self, owner_id: str) -> int:
        with self._transaction():
            cursor = self._conn.execute(
                "UPDATE projects SET owner_id = ? WHERE owner_id IS NULL", (owner_id,)
            )
            return cursor.rowcount

    # ------------------------------------------------------------------ users
    def save_user(self, user: User) -> User:
        self._upsert(_TABLES["users"], self._dump(user))
        return user

    def get_user(self, user_id: str) -> User:
        return User.model_validate(dict(self._get(_TABLES["users"], user_id)))

    def find_user_by_email(self, email: str) -> User | None:
        rows = self._fetch(_TABLES["users"], "WHERE email = ?", (email,))  # column is NOCASE
        return User.model_validate(dict(rows[0])) if rows else None

    def count_users(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        return int(row["n"])

    def get_or_create_secret(self, name: str, factory: Callable[[], str]) -> str:
        with self._transaction():
            row = self._conn.execute(
                "SELECT value FROM app_secrets WHERE name = ?", (name,)
            ).fetchone()
            if row is not None:
                return str(row["value"])
            value = factory()
            self._conn.execute("INSERT INTO app_secrets (name, value) VALUES (?, ?)", (name, value))
            return value

    # ---------------------------------------------------------------- sources
    def save_source(self, message: SourceMessage) -> SourceMessage:
        self._upsert(_TABLES["source_messages"], self._dump(message))
        return message

    def get_source(self, source_id: str) -> SourceMessage:
        return SourceMessage.model_validate(dict(self._get(_TABLES["source_messages"], source_id)))

    def list_sources(self, project_id: str) -> list[SourceMessage]:
        return self._list_by(_TABLES["source_messages"], "project_id", project_id, SourceMessage)

    # ----------------------------------------------------------- requirements
    def save_requirement(self, requirement: Requirement) -> Requirement:
        """Upsert the requirement and rewrite its provenance rows atomically."""
        with self._transaction():
            self._upsert_raw(_TABLES["requirements"], self._dump(requirement, sources=True))
            self._conn.execute(
                "DELETE FROM requirement_sources WHERE requirement_id = ?",
                (requirement.requirement_id,),
            )
            self._conn.executemany(
                "INSERT INTO requirement_sources (requirement_id, position, source_id, snippet) "
                "VALUES (?, ?, ?, ?)",
                [
                    (requirement.requirement_id, pos, ref.source_id, ref.snippet)
                    for pos, ref in enumerate(requirement.sources)
                ],
            )
        return requirement

    def _to_requirement(self, row: sqlite3.Row) -> Requirement:
        data = dict(row)
        with self._lock:
            refs = self._conn.execute(
                "SELECT source_id, snippet FROM requirement_sources "
                "WHERE requirement_id = ? ORDER BY position",
                (data["requirement_id"],),
            ).fetchall()
        data["sources"] = [
            SourceReference(source_id=r["source_id"], snippet=r["snippet"]) for r in refs
        ]
        return Requirement.model_validate(data)

    def get_requirement(self, requirement_id: str) -> Requirement:
        return self._to_requirement(self._get(_TABLES["requirements"], requirement_id))

    def list_requirements(
        self, project_id: str, status: RequirementStatus | None = None
    ) -> list[Requirement]:
        table = _TABLES["requirements"]
        if status is None:
            rows = self._fetch(table, "WHERE project_id = ?", (project_id,))
        else:
            rows = self._fetch(
                table, "WHERE project_id = ? AND status = ?", (project_id, status.value)
            )
        return [self._to_requirement(row) for row in rows]

    # ----------------------------------------------------------- audit tables
    def save_finding(self, finding: AmbiguityFinding) -> None:
        self._upsert(_TABLES["ambiguity_findings"], self._dump(finding))

    def replace_findings(self, requirement_id: str, findings: list[AmbiguityFinding]) -> None:
        with self._transaction():
            self._conn.execute(
                "DELETE FROM ambiguity_findings WHERE requirement_id = ?", (requirement_id,)
            )
            for finding in findings:
                self._upsert_raw(_TABLES["ambiguity_findings"], self._dump(finding))

    def list_findings(self, requirement_id: str) -> list[AmbiguityFinding]:
        return self._list_by(
            _TABLES["ambiguity_findings"], "requirement_id", requirement_id, AmbiguityFinding
        )

    def save_review_event(self, event: ReviewEvent) -> None:
        self._upsert(_TABLES["review_events"], self._dump(event))

    def list_review_events(self, requirement_id: str) -> list[ReviewEvent]:
        return self._list_by(
            _TABLES["review_events"], "requirement_id", requirement_id, ReviewEvent
        )

    def save_confirmation(self, event: ConfirmationEvent) -> None:
        self._upsert(_TABLES["confirmation_events"], self._dump(event))

    def list_confirmations(self, requirement_id: str) -> list[ConfirmationEvent]:
        return self._list_by(
            _TABLES["confirmation_events"], "requirement_id", requirement_id, ConfirmationEvent
        )

    def save_version(self, version: RequirementVersion) -> None:
        values = self._dump(version)
        values["snapshot"] = json.dumps(values["snapshot"])
        self._upsert(_TABLES["requirement_versions"], values)

    def list_versions(self, requirement_id: str) -> list[RequirementVersion]:
        rows = self._fetch(
            _TABLES["requirement_versions"], "WHERE requirement_id = ?", (requirement_id,)
        )
        result = []
        for row in rows:
            data = dict(row)
            data["snapshot"] = json.loads(data["snapshot"])
            result.append(RequirementVersion.model_validate(data))
        return result

    def save_evidence(self, record: EvidenceRecord) -> None:
        self._upsert(_TABLES["evidence_records"], self._dump(record))

    def list_evidence(
        self, *, requirement_id: str | None = None, source_id: str | None = None
    ) -> list[EvidenceRecord]:
        table = _TABLES["evidence_records"]
        clauses, params = [], []
        if requirement_id is not None:
            clauses.append("requirement_id = ?")
            params.append(requirement_id)
        if source_id is not None:
            clauses.append("source_id = ?")
            params.append(source_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return [
            EvidenceRecord.model_validate(dict(r)) for r in self._fetch(table, where, tuple(params))
        ]

    def list_recent_evidence(self, project_ids: list[str], limit: int) -> list[EvidenceRecord]:
        if not project_ids:
            return []
        table = _TABLES["evidence_records"]
        columns = ", ".join(f"e.{c}" for c in table.columns)
        marks = ", ".join("?" for _ in project_ids)  # only placeholders are interpolated
        sql = (
            f"SELECT {columns} FROM evidence_records e "  # noqa: S608 - constants + placeholders
            "LEFT JOIN requirements r ON r.requirement_id = e.requirement_id "
            "LEFT JOIN source_messages s ON s.source_id = e.source_id "
            f"WHERE COALESCE(r.project_id, s.project_id) IN ({marks}) "
            "ORDER BY e.timestamp DESC, e.rowid DESC LIMIT ?"
        )
        with self._lock:
            rows = self._conn.execute(sql, (*project_ids, limit)).fetchall()
        return [EvidenceRecord.model_validate(dict(r)) for r in rows]
