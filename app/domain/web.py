from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class HtmlLinkKind(StrEnum):
    HTML = "html"
    PDF = "pdf"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class HtmlCandidate:
    """An HTML URL emitted by the source-discovery boundary."""

    url: str


@dataclass(frozen=True, slots=True)
class HtmlHeading:
    level: int
    text: str


@dataclass(frozen=True, slots=True)
class HtmlTableRow:
    cells: tuple[str, ...]
    is_header: bool


@dataclass(frozen=True, slots=True)
class HtmlTable:
    caption: str | None
    rows: tuple[HtmlTableRow, ...]


@dataclass(frozen=True, slots=True)
class HtmlLink:
    url: str
    text: str | None
    context: str | None
    kind: HtmlLinkKind


@dataclass(frozen=True, slots=True)
class HtmlProvenanceHeaders:
    etag: str | None = None
    last_modified: str | None = None
    content_language: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievedHtmlPage:
    source_url: str
    final_url: str
    canonical_url: str
    title: str | None
    headings: tuple[HtmlHeading, ...]
    main_text: str
    tables: tuple[HtmlTable, ...]
    links: tuple[HtmlLink, ...]
    language_hint: str | None
    mime_type: str
    encoding: str | None
    size_bytes: int
    sha256: str
    retrieval_started_at: datetime
    retrieved_at: datetime
    provenance_headers: HtmlProvenanceHeaders
    raw_html: bytes = field(repr=False)
