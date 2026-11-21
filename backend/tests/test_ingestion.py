import pytest

from evidence_trail.domain.exceptions import IngestionError
from evidence_trail.ingestion.document_ingestor import DocumentIngestor
from evidence_trail.ingestion.email_ingestor import EmailIngestor
from evidence_trail.ingestion.transcript_ingestor import TranscriptIngestor
from evidence_trail.ingestion.whatsapp_ingestor import WhatsAppIngestor

EMAIL = (
    "From: client@example.com\nSubject: Payments\n"
    "Date: Mon, 01 Sep 2026 10:00:00 +0000\n\nPlease add Bank Transfer."
)


def test_email_parsed() -> None:
    [msg] = EmailIngestor().ingest(EMAIL, "p")
    assert msg.sender == "client@example.com"
    assert "Bank Transfer" in msg.content and "Payments" in msg.content
    assert msg.timestamp.year == 2026


def test_email_empty_rejected() -> None:
    with pytest.raises(IngestionError):
        EmailIngestor().ingest("  ", "p")


def test_whatsapp_webhook() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "9230012345",
                                    "timestamp": "1788000000",
                                    "type": "text",
                                    "text": {"body": "Need JazzCash"},
                                },
                                {"from": "9230012345", "type": "image"},
                            ]
                        }
                    }
                ]
            }
        ]
    }
    msgs = WhatsAppIngestor().ingest(payload, "p")
    assert [m.content for m in msgs] == ["Need JazzCash"]


def test_whatsapp_without_text_rejected() -> None:
    with pytest.raises(IngestionError):
        WhatsAppIngestor().ingest({"entry": []}, "p")


def test_transcript_speaker_turns_and_continuation() -> None:
    raw = "[10:00] Ali: We need dark mode\nand it should remember the choice\nSara: Agreed"
    msgs = TranscriptIngestor().ingest(raw, "p")
    assert [m.sender for m in msgs] == ["Ali", "Sara"]
    assert "remember the choice" in msgs[0].content


def test_document_paragraphs() -> None:
    msgs = DocumentIngestor().ingest("One.\n\nTwo.", "p")
    assert len(msgs) == 2
