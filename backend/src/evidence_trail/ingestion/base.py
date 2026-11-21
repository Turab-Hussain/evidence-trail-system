"""Ingestion contract: turn raw channel input into normalised ``SourceMessage``s."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from evidence_trail.domain.enums import Channel
from evidence_trail.domain.models import SourceMessage


class Ingestor(ABC):
    """Base class for every channel connector (Open/Closed Principle).

    To support a new channel, subclass this, set :attr:`channel` and register
    the instance in :class:`~evidence_trail.ingestion.registry.IngestorRegistry`.
    """

    #: Channel handled by this ingestor.
    channel: Channel

    @abstractmethod
    def ingest(
        self,
        raw: Any,
        project_id: str,
        *,
        sender: str | None = None,
        timestamp: datetime | None = None,
    ) -> list[SourceMessage]:
        """Parse ``raw`` into one or more source messages.

        Raises:
            IngestionError: when the input is malformed or empty.
        """

    def _build(
        self,
        project_id: str,
        content: str,
        *,
        sender: str | None,
        timestamp: datetime | None,
        sender_role: str | None = None,
    ) -> SourceMessage:
        """Create a ``SourceMessage`` stamped with this ingestor's channel."""
        fields: dict[str, Any] = {
            "project_id": project_id,
            "channel": self.channel,
            "content": content.strip(),
            "sender": sender,
            "sender_role": sender_role,
        }
        if timestamp is not None:
            fields["timestamp"] = timestamp
        return SourceMessage(**fields)
