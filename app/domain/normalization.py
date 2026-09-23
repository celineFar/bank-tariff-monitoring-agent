from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.pdf_extraction import PdfAdmission, PdfInputMode

_SPACE_RE = re.compile(r"[\t\r\f\v \u00a0]+")
_ALL_SPACE_RE = re.compile(r"[\s\u00a0]+")
_NUMBER_SEPARATORS_RE = re.compile(r"(?<=\d)[ ,](?=\d{3}(?:\D|$))")
_SUPERSCRIPTS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_SUPERSCRIPT_PLACEHOLDERS = tuple(chr(0xE000 + index) for index in range(10))


def normalize_text(value: str) -> str:
    return _ALL_SPACE_RE.sub(" ", _normalize_unicode(value)).strip()


def normalize_multiline_text(value: str) -> str:
    normalized = _normalize_unicode(value).replace("\r\n", "\n")
    normalized = normalized.replace("\r", "\n")
    lines = [_SPACE_RE.sub(" ", line).strip() for line in normalized.split("\n")]
    return "\n".join(line for line in lines if line)


def _normalize_unicode(value: str) -> str:
    protected = value.translate(
        str.maketrans(dict(zip(_SUPERSCRIPTS, _SUPERSCRIPT_PLACEHOLDERS, strict=True)))
    )
    normalized = unicodedata.normalize("NFKC", protected)
    return normalized.translate(
        str.maketrans(dict(zip(_SUPERSCRIPT_PLACEHOLDERS, _SUPERSCRIPTS, strict=True)))
    )


def normalize_money_text(value: str) -> str:
    return _NUMBER_SEPARATORS_RE.sub("", normalize_text(value).upper())


def normalize_percentage(value: str) -> str:
    normalized = normalize_text(value).replace(",", ".").replace("%", "").strip()
    try:
        number = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid percentage: {value!r}") from exc
    return f"{number.normalize()}%"


class NormalizationModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class NormalizedBlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    KEY_VALUE = "key_value"
    TABLE = "table"
    ACCORDION = "accordion"
    CARD = "card"
    LINK = "link"
    OTHER = "other"


class ScalarKind(StrEnum):
    NUMBER = "number"
    RANGE = "range"
    DATE = "date"


class NormalizationWarningCode(StrEnum):
    ARTIFACT_UNAVAILABLE = "ARTIFACT_UNAVAILABLE"
    INVALID_JSON = "INVALID_JSON"
    AMBIGUOUS_TABLE = "AMBIGUOUS_TABLE"
    PDF_MODEL_REQUIRED = "PDF_MODEL_REQUIRED"
    PDF_MODEL_FAILED = "PDF_MODEL_FAILED"


class SourceReference(NormalizationModel):
    source_item_id: str = Field(min_length=1, max_length=200)
    locator: SourceLocator


class NormalizedScalar(NormalizationModel):
    raw: str = Field(min_length=1)
    kind: ScalarKind
    operator: str | None = None
    value: Decimal | None = None
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    unit: str | None = None
    normalized_date: date | None = None

    @model_validator(mode="after")
    def require_kind_values(self) -> NormalizedScalar:
        if self.kind is ScalarKind.NUMBER and self.value is None:
            raise ValueError("number scalar requires value")
        if self.kind is ScalarKind.RANGE and (
            self.min_value is None or self.max_value is None
        ):
            raise ValueError("range scalar requires min_value and max_value")
        if self.kind is ScalarKind.DATE and self.normalized_date is None:
            raise ValueError("date scalar requires normalized_date")
        return self


class NormalizedTableCell(NormalizationModel):
    raw_text: str
    text: str
    markdown: str = ""
    list_items: tuple[str, ...] = ()
    scalar_candidates: tuple[NormalizedScalar, ...] = ()
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)


class NormalizedTableRow(NormalizationModel):
    id: str = Field(min_length=1, max_length=200)
    cells: tuple[NormalizedTableCell, ...] = Field(min_length=1)


class NormalizedNote(NormalizationModel):
    marker: str | None = None
    raw_text: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)


class NormalizedTable(NormalizationModel):
    id: str = Field(min_length=1, max_length=200)
    title: str | None = None
    headers: tuple[str, ...] = ()
    headers_inferred: bool = False
    rows: tuple[NormalizedTableRow, ...] = ()
    notes: tuple[NormalizedNote, ...] = ()
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_rectangular_rows(self) -> NormalizedTable:
        width = len(self.headers)
        if not width and self.rows:
            width = len(self.rows[0].cells)
        if any(len(row.cells) != width for row in self.rows):
            raise ValueError("normalized table rows must have a consistent width")
        return self


class NormalizedBlock(NormalizationModel):
    id: str = Field(min_length=1, max_length=200)
    type: NormalizedBlockType
    raw_text: str = Field(min_length=1)
    text: str = Field(min_length=1)
    markdown: str | None = None
    heading_path: tuple[str, ...] = ()
    parent_id: str | None = None
    link_ids: tuple[str, ...] = ()
    visible: bool = True
    table_id: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)
    scalar_candidates: tuple[NormalizedScalar, ...] = ()
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)
    extraction_method: str = Field(default="html", min_length=1, max_length=100)


class NormalizedLink(NormalizationModel):
    id: str = Field(min_length=1, max_length=200)
    url: HttpUrl
    raw_href: str = Field(default="", max_length=8192)
    fragment: str | None = None
    text: str = ""
    title: str | None = None
    rel: tuple[str, ...] = ()
    declared_mime_type: str | None = None
    same_allowlisted_source: bool = True
    downloadable: bool = False
    source_refs: tuple[SourceReference, ...] = Field(min_length=1)


class NormalizedDocument(NormalizationModel):
    id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=1000)
    source_url: HttpUrl
    source_type: SourceType
    mime_type: str = Field(min_length=1, max_length=255)
    content_sha256: str = Field(min_length=64, max_length=64)
    extraction_method: str = Field(min_length=1, max_length=100)
    quality_score: float | None = Field(default=None, ge=0, le=1)
    pdf_input_mode: PdfInputMode | None = None
    pdf_admission: PdfAdmission | None = None
    blocks: tuple[NormalizedBlock, ...] = ()
    tables: tuple[NormalizedTable, ...] = ()
    links: tuple[NormalizedLink, ...] = ()


class NormalizationWarning(NormalizationModel):
    code: NormalizationWarningCode
    source_id: str
    message: str = Field(min_length=1)


class NormalizedSourceBundle(NormalizationModel):
    canonical_url: HttpUrl
    acquisition_content_hash: str = Field(min_length=64, max_length=64)
    documents: tuple[NormalizedDocument, ...] = Field(min_length=1)
    warnings: tuple[NormalizationWarning, ...] = ()
