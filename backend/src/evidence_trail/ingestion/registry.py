"""Registry mapping a :class:`Channel` to its :class:`Ingestor`."""

from __future__ import annotations

from collections.abc import Iterable

from evidence_trail.domain.enums import Channel
from evidence_trail.domain.exceptions import IngestionError
from evidence_trail.ingestion.base import Ingestor
from evidence_trail.ingestion.document_ingestor import DocumentIngestor
from evidence_trail.ingestion.email_ingestor import EmailIngestor
from evidence_trail.ingestion.transcript_ingestor import TranscriptIngestor
from evidence_trail.ingestion.whatsapp_ingestor import WhatsAppIngestor


class IngestorRegistry:
    """Looks up the right connector for a channel."""

    def __init__(self, ingestors: Iterable[Ingestor] | None = None) -> None:
        self._by_channel: dict[Channel, Ingestor] = {}
        for ingestor in ingestors if ingestors is not None else self.default_ingestors():
            self.register(ingestor)

    @staticmethod
    def default_ingestors() -> list[Ingestor]:
        """The four connectors in the MVP scope."""
        return [
            EmailIngestor(),
            WhatsAppIngestor(),
            TranscriptIngestor(),
            DocumentIngestor(),
        ]

    def register(self, ingestor: Ingestor) -> None:
        """Add (or replace) the connector for ``ingestor.channel``."""
        self._by_channel[ingestor.channel] = ingestor

    def get(self, channel: Channel) -> Ingestor:
        """Return the connector for ``channel`` or raise ``IngestionError``."""
        try:
            return self._by_channel[channel]
        except KeyError as exc:
            raise IngestionError(f"No ingestor registered for '{channel.value}'.") from exc
