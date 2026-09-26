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


class PdfLinkLabel(StrEnum):
    """Whether a linked PDF belongs to the offering, judged from its link alone."""

    CURRENT_PRODUCT = "current_product"
    # Applies to this offering among others: the loan fee schedule, the
    # floating-rate procedure, a lending campaign that covers it.
    SHARED_TERMS = "shared_terms"
    RELATED_PRODUCT = "related_product"
    GENERIC_BANK_INFORMATION = "generic_bank_information"
    # The link does not say; the document is transcribed and read.
    UNCLEAR = "unclear"


TRANSCRIBED_LINK_LABELS = frozenset(
    {PdfLinkLabel.CURRENT_PRODUCT, PdfLinkLabel.SHARED_TERMS, PdfLinkLabel.UNCLEAR}
)


class PdfLinkChoice(PdfExtractionModel):
    """Source discovery's decision on one linked PDF, made before transcription."""

    label: PdfLinkLabel
    role: PdfAdmissionRole
    reason: str = Field(min_length=1, max_length=2000)
    # `llm` for a fresh model answer, `cache` for a stored one.
    decided_by: str = Field(pattern=r"^(llm|cache)$")
    model_name: str = Field(min_length=1, max_length=200)
    link_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def transcribe(self) -> bool:
        return self.label in TRANSCRIBED_LINK_LABELS


class PdfLinkSelection(PdfExtractionModel):
    """Link choices for one acquisition, keyed by PDF content hash (sha256)."""

    offering_id: str = Field(min_length=1, max_length=100)
    choices: dict[str, PdfLinkChoice] = Field(default_factory=dict)


class PdfPageProbe(PdfExtractionModel):
    page_number: int = Field(ge=1)
    input_mode: PdfInputMode
    native_text_characters: int = Field(ge=0)
    images_detected: bool


class PdfInputProbe(PdfExtractionModel):
    page_count: int = Field(ge=0)
    document_mode: PdfInputMode
    pages: tuple[PdfPageProbe, ...] = ()


class PdfTranscriptionSource(StrEnum):
    """Which engine produced the content of one PDF page."""

    GEMINI = "gemini"
    OCR = "ocr"
    NONE = "none"


class OcrPageOutcome(StrEnum):
    TRANSCRIBED = "transcribed"
    LOW_CONFIDENCE = "low_confidence"
    SKIPPED = "skipped"
    FAILED = "failed"


class OcrPageResult(PdfExtractionModel):
    page_number: int = Field(ge=1)
    outcome: OcrPageOutcome
    text: str = ""
    mean_confidence: float = Field(default=0.0, ge=0, le=100)
    word_count: int = Field(default=0, ge=0)
    detail: str = ""

    @model_validator(mode="after")
    def only_transcribed_carries_text(self) -> OcrPageResult:
        """A page that did not clear the floor must not smuggle text downstream."""
        if self.outcome is not OcrPageOutcome.TRANSCRIBED and self.text:
            raise ValueError("only a transcribed OCR page may carry text")
        return self


class OcrDocumentResult(PdfExtractionModel):
    engine_version: str
    languages: str
    pages: tuple[OcrPageResult, ...] = ()

    @property
    def transcribed_pages(self) -> tuple[int, ...]:
        return tuple(
            page.page_number
            for page in self.pages
            if page.outcome is OcrPageOutcome.TRANSCRIBED
        )


# One spelling of the OCR provenance marker, shared by the producer of OCR
# blocks and by every consumer that has to recognise one. Evidence keeps only a
# `source_item_id`, so the id itself carries the provenance downstream.
OCR_SOURCE_ITEM_MARKER = ":ocr:"


def ocr_block_id(document_id: str, page_number: int) -> str:
    return f"{document_id}:page:{page_number}{OCR_SOURCE_ITEM_MARKER}0"


def is_ocr_source_item(source_item_id: str | None) -> bool:
    return bool(source_item_id) and OCR_SOURCE_ITEM_MARKER in str(source_item_id)


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
    # Every header row, top to bottom, one entry per column (SE3): the table's
    # header hierarchy as fields, not as text the model has to repeat.
    header_rows: list[list[str]] = Field(default_factory=list)
    rows: list[list[str]]
    # Per row, the group it falls under (a merged label cell or a group row).
    row_groups: list[str] = Field(default_factory=list)
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
    header_rows: tuple[tuple[str, ...], ...] = Field(default=(), max_length=10)
    rows: tuple[PdfExtractedTableRow, ...] = Field(default=(), max_length=1000)
    # One per row when given; stored transcriptions from before SE3 have none.
    row_groups: tuple[str, ...] = Field(default=(), max_length=1000)
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
