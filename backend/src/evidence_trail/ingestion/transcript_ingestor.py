"""Meeting transcript connector.

Understands lines such as ``[10:32] Ali: We need a dark mode`` or
``Sara: Payments via JazzCash``.  Lines without a speaker are attached to the
previous speaker so multi-line utterances stay together.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from evidence_trail.domain.enums import Channel
from evidence_trail.domain.exceptions import IngestionError
from evidence_trail.domain.models import SourceMessage
from evidence_trail.ingestion.base import Ingestor

_LINE = re.compile(
    r"^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?(?P<speaker>[A-Za-z][\w .'-]{0,39}):\s*(?P<text>.+)$"
)


class TranscriptIngestor(Ingestor):
    """Splits a transcript into one message per speaker turn."""

    channel = Channel.MEETING_TRANSCRIPT

    def ingest(
        self,
        raw: Any,
        project_id: str,
        *,
        sender: str | None = None,
        timestamp: datetime | None = None,
    ) -> list[SourceMessage]:
        if not isinstance(raw, str) or not raw.strip():
            raise IngestionError("Transcript must be a non-empty string.")

        turns: list[tuple[str | None, list[str]]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            match = _LINE.match(line)
            if match:
                turns.append((match["speaker"].strip(), [match["text"].strip()]))
            elif turns:
                turns[-1][1].append(line)  # continuation of previous turn
            else:
                turns.append((sender, [line]))

        return [
            self._build(project_id, " ".join(parts), sender=speaker, timestamp=timestamp)
            for speaker, parts in turns
        ]
