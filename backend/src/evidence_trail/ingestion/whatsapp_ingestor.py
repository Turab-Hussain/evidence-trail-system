"""WhatsApp Business Platform (Cloud API) connector.

Only the *official* webhook payload format is supported - the proposal
explicitly excludes scraping personal chats.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from evidence_trail.domain.enums import Channel
from evidence_trail.domain.exceptions import IngestionError
from evidence_trail.domain.models import SourceMessage
from evidence_trail.ingestion.base import Ingestor


class WhatsAppIngestor(Ingestor):
    """Extracts text messages from a Cloud API webhook payload (``dict``)."""

    channel = Channel.WHATSAPP

    def ingest(
        self,
        raw: Any,
        project_id: str,
        *,
        sender: str | None = None,
        timestamp: datetime | None = None,
    ) -> list[SourceMessage]:
        if not isinstance(raw, dict):
            raise IngestionError("WhatsApp payload must be a JSON object.")

        messages: list[SourceMessage] = []
        for entry in raw.get("entry", []):
            for change in entry.get("changes", []):
                for item in change.get("value", {}).get("messages", []):
                    message = self._parse_message(item, project_id, sender)
                    if message is not None:
                        messages.append(message)
        if not messages:
            raise IngestionError("WhatsApp payload contained no text messages.")
        return messages

    def _parse_message(
        self, item: dict[str, Any], project_id: str, default_sender: str | None
    ) -> SourceMessage | None:
        """Convert one webhook message; non-text messages are skipped."""
        if item.get("type") != "text":
            return None
        body = item.get("text", {}).get("body", "")
        if not body.strip():
            return None
        sent_at = None
        if item.get("timestamp"):
            try:
                sent_at = datetime.fromtimestamp(int(item["timestamp"]), tz=UTC)
            except (TypeError, ValueError):
                sent_at = None
        return self._build(
            project_id,
            body,
            sender=item.get("from") or default_sender,
            timestamp=sent_at,
        )
