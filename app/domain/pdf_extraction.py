from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PdfExtractionModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class PdfInputMode(StrEnum):
    MACHINE_READABLE = "machine_readable"
    IMAGE_ONLY = "image_only"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class PdfAdmissionRelevance(StrEnum):
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
    AMBIGUOUS = "ambiguous"


class PdfTemporalStatus(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    FUTURE = "future"
    TIME_BOUNDED = "time_bounded"
    UNKNOWN = "unknown"


class PdfAdmissionRole(StrEnum):
    PRODUCT_TERMS = "product_terms"
    FEES = "fees"
    LEGAL_DISCLOSURE = "legal_disclosure"
    OTHER = "other"


class PdfEffectivePeriod(PdfExtractionModel):
    raw: str
    start: date | None = None
    end: date | None = None


class PdfAdmission(PdfExtractionModel):
    relevance: PdfAdmissionRelevance
    role: PdfAdmissionRole
    temporal_status: PdfTemporalStatus
    decision_basis: tuple[str, ...] = ()
    reason: str
    effective_periods: tuple[PdfEffectivePeriod, ...] = ()


class PdfPageProbe(PdfExtractionModel):
    page_number: int = Field(ge=1)
    input_mode: PdfInputMode
    native_text_characters: int = Field(ge=0)
    images_detected: bool


class PdfInputProbe(PdfExtractionModel):
    page_count: int = Field(ge=0)
    document_mode: PdfInputMode
    pages: tuple[PdfPageProbe, ...] = ()


class PdfExtractedBlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    KEY_VALUE = "key_value"
    OTHER = "other"


class PdfModelItemKind(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    KEY_VALUE = "key_value"
    OTHER = "other"
    TABLE = "table"
    NOTE = "note"


class PdfModelItem(BaseModel):
    """Intentionally shallow schema sent to Gemini structured output."""

    page_number: int
    kind: PdfModelItemKind
    text: str
    heading_path: list[str]
    title: str
    headers: list[str]
    rows: list[list[str]]
    notes: list[str]


class PdfModelExtractionResponse(BaseModel):
    items: list[PdfModelItem]


class PdfExtractedBlock(PdfExtractionModel):
    type: PdfExtractedBlockType
    text: str = Field(min_length=1, max_length=50_000)
    heading_path: tuple[str, ...] = Field(default=(), max_length=20)


class PdfExtractedTableRow(PdfExtractionModel):
    cells: tuple[str, ...] = Field(min_length=1, max_length=50)


class PdfExtractedTable(PdfExtractionModel):
    title: str | None = Field(default=None, max_length=2000)
    headers: tuple[str, ...] = Field(default=(), max_length=50)
    rows: tuple[PdfExtractedTableRow, ...] = Field(default=(), max_length=1000)
    notes: tuple[str, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def require_rectangular_rows(self) -> PdfExtractedTable:
        width = len(self.headers) or (len(self.rows[0].cells) if self.rows else 0)
        if any(len(row.cells) != width for row in self.rows):
            raise ValueError("Gemini PDF table rows must have a consistent width")
        return self


class PdfExtractedPage(PdfExtractionModel):
    page_number: int = Field(ge=1)
    blocks: tuple[PdfExtractedBlock, ...] = Field(default=(), max_length=2000)
    tables: tuple[PdfExtractedTable, ...] = Field(default=(), max_length=200)
    notes: tuple[str, ...] = Field(default=(), max_length=200)


class PdfExtractionResponse(PdfExtractionModel):
    pages: tuple[PdfExtractedPage, ...] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_pages(self) -> PdfExtractionResponse:
        numbers = [page.page_number for page in self.pages]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Gemini PDF response contains duplicate page numbers")
        return self


class PdfModelUsage(PdfExtractionModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    thinking_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    request_attempts: int = Field(default=0, ge=0)
    application_retries: int = Field(default=0, ge=0)


class PdfExtractionPlan(PdfExtractionModel):
    document_id: str
    document_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    admission: PdfAdmission
    input_probe: PdfInputProbe
    schema_version: str
    prompt_version: str
    model_names: tuple[str, ...]
    content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
