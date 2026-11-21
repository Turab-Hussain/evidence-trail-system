"""Email connector: parses RFC 822 messages (e.g. ``.eml`` content)."""

from __future__ import annotations

from datetime import datetime
from email import message_from_string, policy
from email.utils import parsedate_to_datetime
from typing import Any

from evidence_trail.domain.enums import Channel
from evidence_trail.domain.exceptions import IngestionError
from evidence_trail.domain.models import SourceMessage
from evidence_trail.ingestion.base import Ingestor


class EmailIngestor(Ingestor):
    """Turns a raw email string into a single normalised message."""

    channel = Channel.EMAIL

    def ingest(
        self,
        raw: Any,
        project_id: str,
        *,
        sender: str | None = None,
        timestamp: datetime | None = None,
    ) -> list[SourceMessage]:
        if not isinstance(raw, str) or not raw.strip():
            raise IngestionError("Email content must be a non-empty string.")

        parsed = message_from_string(raw, policy=policy.default)
        body_part = parsed.get_body(preferencelist=("plain",))
        body = body_part.get_content() if body_part is not None else parsed.get_payload()
        if not isinstance(body, str) or not body.strip():
            raise IngestionError("Email has no readable plain-text body.")

        subject = str(parsed.get("Subject", "")).strip()
        content = f"{subject}\n{body}" if subject else body
        return [
            self._build(
                project_id,
                content,
                sender=sender or str(parsed.get("From", "")) or None,
                timestamp=timestamp or self._parse_date(parsed.get("Date")),
            )
        ]

    @staticmethod
    def _parse_date(value: object) -> datetime | None:
        """Parse an RFC 2822 date header; return ``None`` if absent/invalid."""
        if not value:
            return None
        try:
            return parsedate_to_datetime(str(value))
        except (TypeError, ValueError):
            return None
