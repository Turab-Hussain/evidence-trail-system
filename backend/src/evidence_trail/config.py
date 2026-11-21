"""Application settings, loaded once from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
    """Load ``KEY=value`` lines from a ``.env`` file into ``os.environ``.

    Variables already set in the real environment win, so a shell value always
    overrides the file. A missing file is silently ignored.
    """
    env_file = Path(path)
    if not env_file.is_file():
        return
    for raw in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("\"'")
        os.environ.setdefault(key.strip(), value)


@dataclass(frozen=True)
class Settings:
    """Immutable runtime configuration.

    Attributes:
        db_path: SQLite file path (``:memory:`` is allowed for tests).
        secret_key: Signs login tokens. ``None`` generates one on first start and keeps it
            in the database, so logins survive restarts.
        token_ttl_hours: How long a login stays valid.
        llm_provider: ``"none"`` (offline heuristics), ``"gemini"`` or ``"anthropic"``.
        llm_model: Model name for the chosen provider; ``None`` uses the provider default.
        gemini_api_key: Credential for the Gemini API.
        anthropic_api_key: Credential for the Anthropic API.
        cors_origins: Browser origins allowed to call the API (the frontend dev server by
            default). Comma-separated in ``EVIDENCE_CORS_ORIGINS``.
        similarity_threshold: Minimum text similarity (0-1) to consolidate two
            requirements into one.
    """

    db_path: str = "evidence_trail.db"
    secret_key: str | None = None
    token_ttl_hours: int = 168
    llm_provider: str = "none"
    llm_model: str | None = None
    gemini_api_key: str | None = None
    anthropic_api_key: str | None = None
    similarity_threshold: float = 0.4
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from ``EVIDENCE_*`` variables (and a local ``.env`` file)."""
        load_dotenv()
        return cls(
            db_path=os.getenv("EVIDENCE_DB_PATH", cls.db_path),
            secret_key=os.getenv("EVIDENCE_SECRET_KEY") or None,
            token_ttl_hours=int(os.getenv("EVIDENCE_TOKEN_TTL_HOURS", cls.token_ttl_hours)),
            llm_provider=os.getenv("EVIDENCE_LLM_PROVIDER", cls.llm_provider).lower(),
            llm_model=os.getenv("EVIDENCE_LLM_MODEL") or None,
            gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or None,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
            cors_origins=tuple(
                origin.strip()
                for origin in os.getenv("EVIDENCE_CORS_ORIGINS", ",".join(cls.cors_origins)).split(
                    ","
                )
                if origin.strip()
            ),
            similarity_threshold=float(
                os.getenv("EVIDENCE_SIMILARITY_THRESHOLD", cls.similarity_threshold)
            ),
        )
