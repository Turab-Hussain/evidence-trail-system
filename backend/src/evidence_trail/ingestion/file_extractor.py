"""Turns uploaded files (PDF, Word, text, email, subtitles) into plain text.

Each file type has its own :class:`FileTextExtractor`; to support another format,
add a subclass and list it in :class:`FileExtractorRegistry` (Open/Closed Principle).
The extracted text is then handed to the normal channel ingestors, so an uploaded
file goes through exactly the same pipeline as pasted text.
"""

from __future__ import annotations

import io
import re
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import PurePath
from xml.etree import ElementTree  # noqa: S405 - only used on DOCX XML after a size check

from evidence_trail.domain.enums import Channel
from evidence_trail.domain.exceptions import FileExtractionError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
_MAX_DOCX_XML_BYTES = 20 * 1024 * 1024  # guards against zip bombs
_CHUNK_LIMIT = 800  # characters; keeps one source message to a readable size

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass(frozen=True)
class ExtractedFile:
    """Result of reading one uploaded file."""

    filename: str
    text: str
    channel: Channel


def decode_text(data: bytes) -> str:
    """Decode bytes as UTF-8 (with or without BOM), UTF-16 (with BOM) or Windows-1252."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def chunk_paragraph(text: str, limit: int = _CHUNK_LIMIT) -> list[str]:
    """Split a long paragraph at sentence ends so no chunk is much longer than ``limit``."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return [text] if text else []
    chunks: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if current and len(current) + len(sentence) + 1 > limit:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


class FileTextExtractor(ABC):
    """Reads one family of file types."""

    #: Lower-case extensions including the dot, e.g. ``".pdf"``.
    extensions: tuple[str, ...]
    #: Channel used when the caller does not choose one.
    default_channel: Channel = Channel.DOCUMENT

    @abstractmethod
    def extract(self, data: bytes) -> str:
        """Return the file's text.

        Raises:
            FileExtractionError: if the file cannot be read.
        """


class PlainTextExtractor(FileTextExtractor):
    """Text, Markdown and CSV files."""

    extensions = (".txt", ".md", ".markdown", ".text", ".log", ".csv")

    def extract(self, data: bytes) -> str:
        return decode_text(data)


class EmailFileExtractor(FileTextExtractor):
    """``.eml`` files: the raw message is kept so the email ingestor can read its headers."""

    extensions = (".eml",)
    default_channel = Channel.EMAIL

    def extract(self, data: bytes) -> str:
        return decode_text(data)


class SubtitleExtractor(FileTextExtractor):
    """WebVTT / SRT meeting captions, turned into ``Speaker: text`` lines."""

    extensions = (".vtt", ".srt")
    default_channel = Channel.MEETING_TRANSCRIPT

    _TIMING = re.compile(r"^\s*\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}\s*-->")
    _VOICE = re.compile(r"<v\s+([^>]+)>")
    _TAG = re.compile(r"</?[^>]+>")

    def extract(self, data: bytes) -> str:
        lines: list[str] = []
        for raw in decode_text(data).splitlines():
            line = raw.strip()
            if (
                not line
                or line.upper().startswith(("WEBVTT", "NOTE", "STYLE"))
                or line.isdigit()
                or self._TIMING.match(line)
            ):
                continue
            line = self._VOICE.sub(lambda m: f"{m.group(1).strip()}: ", line)
            lines.append(self._TAG.sub("", line).strip())
        return "\n".join(lines)


class PdfExtractor(FileTextExtractor):
    """Text-based PDFs (scanned images have no text layer and are rejected)."""

    extensions = (".pdf",)

    def extract(self, data: bytes) -> str:
        from pypdf import PdfReader  # noqa: PLC0415 - optional until a PDF is uploaded
        from pypdf.errors import PyPdfError  # noqa: PLC0415

        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise FileExtractionError("This PDF is password-protected. Remove the password.")
            pages = [page.extract_text() or "" for page in reader.pages]
        except FileExtractionError:
            raise
        except (PyPdfError, ValueError, KeyError, OSError) as exc:
            raise FileExtractionError("This PDF could not be read. Is the file damaged?") from exc

        paragraphs: list[str] = []
        for page in pages:
            for block in re.split(r"\n\s*\n", page):
                paragraphs.extend(chunk_paragraph(block))
        if not paragraphs:
            raise FileExtractionError(
                "No text found in this PDF. It may be a scan; export a text version instead."
            )
        return "\n\n".join(paragraphs)


class DocxExtractor(FileTextExtractor):
    """Word ``.docx`` files, one paragraph per line block (tables included)."""

    extensions = (".docx",)

    def extract(self, data: bytes) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                info = archive.getinfo("word/document.xml")
                if info.file_size > _MAX_DOCX_XML_BYTES:
                    raise FileExtractionError("This Word file is too large to read.")
                xml = archive.read(info)
            root = ElementTree.fromstring(xml)  # noqa: S314 - size-checked, no external entities
        except FileExtractionError:
            raise
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
            raise FileExtractionError(
                "This is not a valid .docx file. Older .doc files are not supported."
            ) from exc

        paragraphs = []
        for para in root.iter(f"{_W_NS}p"):
            text = "".join(node.text or "" for node in para.iter(f"{_W_NS}t")).strip()
            if text:
                paragraphs.append(text)
        return "\n\n".join(paragraphs)


class FileExtractorRegistry:
    """Finds the right extractor for a file name and validates the upload."""

    def __init__(self, extractors: list[FileTextExtractor] | None = None) -> None:
        self._by_extension: dict[str, FileTextExtractor] = {}
        for extractor in extractors or [
            PlainTextExtractor(),
            EmailFileExtractor(),
            SubtitleExtractor(),
            PdfExtractor(),
            DocxExtractor(),
        ]:
            for extension in extractor.extensions:
                self._by_extension[extension] = extractor

    @property
    def supported_extensions(self) -> list[str]:
        return sorted(self._by_extension)

    def extract(self, filename: str, data: bytes, channel: Channel | None = None) -> ExtractedFile:
        """Read ``data`` and return its text plus the channel it should be filed under.

        Raises:
            FileExtractionError: unsupported type, empty, too large or unreadable.
        """
        name = PurePath(filename.replace("\\", "/")).name or "upload"
        extractor = self._by_extension.get(PurePath(name).suffix.lower())
        if extractor is None:
            raise FileExtractionError(
                f"'{name}' is not a supported file type. "
                f"Use one of: {', '.join(self.supported_extensions)}."
            )
        if not data:
            raise FileExtractionError(f"'{name}' is empty.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise FileExtractionError(
                f"'{name}' is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            )
        text = extractor.extract(data).strip()
        if not text:
            raise FileExtractionError(f"No readable text found in '{name}'.")
        return ExtractedFile(name, text, channel or extractor.default_channel)
