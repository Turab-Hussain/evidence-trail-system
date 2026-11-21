"""File upload: extraction per file type and the HTTP endpoint."""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

import pytest
from fastapi.testclient import TestClient

from evidence_trail.domain.enums import Channel
from evidence_trail.domain.exceptions import FileExtractionError
from evidence_trail.ingestion.file_extractor import MAX_UPLOAD_BYTES, FileExtractorRegistry


def make_docx(paragraphs: list[str]) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{escape(p)}</w:t></w:r></w:p>" for p in paragraphs)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return buffer.getvalue()


def make_pdf(text: str) -> bytes:
    """A minimal one-page PDF whose page contains ``text``."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objects) + 1, xref)
    return bytes(out)


registry = FileExtractorRegistry()


def test_text_and_markdown_and_encodings() -> None:
    assert (
        registry.extract("brief.md", b"# Brief\nWe need a login page.").channel is Channel.DOCUMENT
    )
    assert "caf\u00e9" in registry.extract("a.txt", "caf\u00e9 login".encode("utf-8-sig")).text
    assert "caf\u00e9" in registry.extract("a.txt", "caf\u00e9 login".encode("cp1252")).text
    assert "login" in registry.extract("a.txt", "login".encode("utf-16")).text


def test_docx_paragraphs_are_extracted() -> None:
    result = registry.extract("spec.docx", make_docx(["We need login.", "Make it fast & safe."]))
    assert result.text == "We need login.\n\nMake it fast & safe."


def test_pdf_text_is_extracted() -> None:
    result = registry.extract("spec.pdf", make_pdf("We need a login page for customers."))
    assert "login page" in result.text and result.channel is Channel.DOCUMENT


def test_pdf_without_text_and_corrupt_files_are_rejected() -> None:
    with pytest.raises(FileExtractionError, match="No text"):
        registry.extract("scan.pdf", make_pdf(""))
    with pytest.raises(FileExtractionError, match="could not be read|No text"):
        registry.extract("bad.pdf", b"this is not a pdf")
    with pytest.raises(FileExtractionError, match="not a valid .docx"):
        registry.extract("bad.docx", b"this is not a zip")


def test_eml_and_vtt_default_channels() -> None:
    eml = registry.extract("m.eml", b"Subject: Hi\nFrom: a@b.co\n\nWe need a login page.")
    assert eml.channel is Channel.EMAIL and "Subject: Hi" in eml.text
    vtt = registry.extract(
        "call.vtt",
        b"WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\n<v Sara>We need search.</v>\n\n"
        b"2\n00:00:05.000 --> 00:00:06.000\nAli: Okay.\n",
    )
    assert vtt.channel is Channel.MEETING_TRANSCRIPT
    assert vtt.text.splitlines() == ["Sara: We need search.", "Ali: Okay."]


def test_validation_errors() -> None:
    with pytest.raises(FileExtractionError, match="not a supported"):
        registry.extract("photo.png", b"x")
    with pytest.raises(FileExtractionError, match="empty"):
        registry.extract("a.txt", b"")
    with pytest.raises(FileExtractionError, match="larger than"):
        registry.extract("a.txt", b"x" * (MAX_UPLOAD_BYTES + 1))
    with pytest.raises(FileExtractionError, match="No readable text"):
        registry.extract("a.txt", b"   \n  ")


def test_filename_path_is_stripped_and_channel_override() -> None:
    result = registry.extract("C:\\Users\\me\\brief.txt", b"We need x.", Channel.EMAIL)
    assert result.filename == "brief.txt" and result.channel is Channel.EMAIL


# --------------------------------------------------------------------- HTTP
def _project(client: TestClient, auth: dict[str, str]) -> str:
    return client.post("/projects", json={"name": "Shop", "client": "Acme"}, headers=auth).json()[
        "project_id"
    ]


def test_upload_creates_requirements_from_many_file_types(
    client: TestClient, auth: dict[str, str]
) -> None:
    pid = _project(client, auth)
    files = [
        ("files", ("brief.txt", b"We need a login page.\n\nMake it premium.", "text/plain")),
        (
            "files",
            ("spec.docx", make_docx(["Customers must reset their password."]), "application/x"),
        ),
        ("files", ("scope.pdf", make_pdf("We need an admin dashboard."), "application/pdf")),
        ("files", ("mail.eml", b"Subject: Hi\n\nPlease add product search.", "message/rfc822")),
    ]
    resp = client.post(f"/projects/{pid}/upload", files=files, headers=auth)
    assert resp.status_code == 200, resp.text
    results = resp.json()["results"]
    assert all(r["ok"] for r in results), results
    assert [r["channel"] for r in results] == ["document", "document", "document", "email"]
    assert all(r["created_requirements"] for r in results)

    listing = client.get(f"/projects/{pid}/requirements", headers=auth).json()
    assert len(listing) >= 5
    detail = client.get(f"/requirements/{listing[0]['requirement_id']}", headers=auth).json()
    assert detail["sources"][0]["sender"] == "brief.txt"  # the file name is kept as provenance


def test_one_bad_file_does_not_block_the_others(client: TestClient, auth: dict[str, str]) -> None:
    pid = _project(client, auth)
    files = [
        ("files", ("photo.png", b"\x89PNG", "image/png")),
        ("files", ("ok.txt", b"We need a login page.", "text/plain")),
        ("files", ("empty.txt", b"", "text/plain")),
    ]
    results = client.post(f"/projects/{pid}/upload", files=files, headers=auth).json()["results"]
    assert [r["ok"] for r in results] == [False, True, False]
    assert "not a supported" in results[0]["error"] and "empty" in results[2]["error"]
    assert (
        ".pdf"
        in client.post(f"/projects/{pid}/upload", files=files[:1], headers=auth).json()[
            "supported_types"
        ]
    )


def test_upload_channel_override_validation_and_limits(
    client: TestClient, auth: dict[str, str]
) -> None:
    pid = _project(client, auth)
    one = [("files", ("a.txt", b"Sara: We need search.", "text/plain"))]
    ok = client.post(
        f"/projects/{pid}/upload", files=one, data={"channel": "transcript"}, headers=auth
    )
    assert ok.json()["results"][0]["channel"] == "meeting_transcript"
    bad = client.post(f"/projects/{pid}/upload", files=one, data={"channel": "fax"}, headers=auth)
    assert bad.status_code == 422
    many = [("files", (f"{i}.txt", b"We need x.", "text/plain")) for i in range(11)]
    assert client.post(f"/projects/{pid}/upload", files=many, headers=auth).status_code == 422
    assert client.post(f"/projects/{pid}/upload", files=one).status_code == 401


def test_upload_to_someone_elses_project_is_not_found(client: TestClient) -> None:
    from tests.conftest import sign_up

    alice = sign_up(client, "alice@example.com")
    bob = sign_up(client, "bob@example.com")
    pid = _project(client, alice)
    files = [("files", ("a.txt", b"We need x.", "text/plain"))]
    assert client.post(f"/projects/{pid}/upload", files=files, headers=bob).status_code == 404
