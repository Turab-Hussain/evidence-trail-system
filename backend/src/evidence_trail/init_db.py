"""Create (or upgrade) the database file: ``python -m evidence_trail.init_db [path]``."""

from __future__ import annotations

import sqlite3
import sys

from evidence_trail.config import Settings
from evidence_trail.repositories.sqlite_repository import SQLiteRepository


def init_db(db_path: str) -> list[str]:
    """Create all tables/indexes in ``db_path`` and return the table names."""
    repo = SQLiteRepository(db_path)
    repo.close()
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    return [name for (name,) in rows]


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else Settings.from_env().db_path
    print(f"Database ready at {target}")
    for table in init_db(target):
        print(f"  - {table}")
