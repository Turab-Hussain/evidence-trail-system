"""Plain-text / Markdown document connector.

PDF, DOCX and XLSX parsers are listed as future work in the proposal; they can
be added as further :class:`Ingestor` subclasses without changing other code.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from evidence_trail.domain.enums import Channel
from evidence_trail.domain.exceptions import IngestionError
from evidence_trail.domain.models import SourceMessage
from evidence_trail.ingestion.base import Ingestor


class DocumentIngestor(Ingestor):
    """Splits a text document into one message per paragraph."""

    channel = Channel.DOCUMENT

    def ingest(
        self,
        raw: Any,
        project_id: str,
        *,
        sender: str | None = None,
        timestamp: datetime | None = None,
    ) -> list[SourceMessage]:
        if not isinstance(raw, str) or not raw.strip():
            raise IngestionError("Document content must be a non-empty string.")
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
        return [
            self._build(project_id, paragraph, sender=sender, timestamp=timestamp)
            for paragraph in paragraphs
        ]
