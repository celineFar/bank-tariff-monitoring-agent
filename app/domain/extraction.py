from __future__ import annotations

import math
import re
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.discovery import StoredArtifact

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EXTRACTION_NAMESPACE = UUID("c9e8990a-c3ce-48b3-a481-00a4f65ea52f")


class ExtractionModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class ExtractedBlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE = "table"
    LINK = "link"
    FACT = "fact"


class ExtractionStatus(StrEnum):
    SUCCESS = "success"
    NEEDS_OCR = "needs_ocr"


class SourceLocator(ExtractionModel):
    css_path: str | None = Field(default=None, max_length=4000)
    page: int | None = Field(default=None, ge=1)
    bounding_box: tuple[float, float, float, float] | None = None

    @field_validator("bounding_box")
    @classmethod
    def validate_bounding_box(
        cls, value: tuple[float, float, float, float] | None
    ) -> tuple[float, float, float, float] | None:
        if value is None:
            return None
        x0, top, x1, bottom = value
        if not all(math.isfinite(coordinate) for coordinate in value):
            raise ValueError("bounding-box coordinates must be finite")
        if x1 < x0 or bottom < top:
            raise ValueError("bounding-box coordinates are inverted")
        return value

    @model_validator(mode="after")
    def require_a_location(self) -> SourceLocator:
        if self.css_path is None and self.page is None:
            raise ValueError("a source locator requires a CSS path or page")
        return self


class ExtractionWarning(ExtractionModel):
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1000)
    source_locator: SourceLocator | None = None


class ExtractedLink(ExtractionModel):
    text: str = Field(min_length=1)
    target: str = Field(min_length=1, max_length=4000)


class ExtractedTableRow(ExtractionModel):
    cells: tuple[str, ...] = Field(min_length=1)
    is_header: bool = False


class ExtractedTable(ExtractionModel):
    caption: str | None = None
    rows: tuple[ExtractedTableRow, ...] = Field(min_length=1)


class ExtractedPageTable(ExtractionModel):
    ordinal: int = Field(ge=0)
    table: ExtractedTable
    source_locator: SourceLocator


class ExtractedPage(ExtractionModel):
    page_number: int = Field(ge=1)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    blocks: tuple[ExtractedBlock, ...] = ()
    tables: tuple[ExtractedPageTable, ...] = ()
    warnings: tuple[ExtractionWarning, ...] = ()
    text_character_count: int = Field(ge=0)
    image_count: int = Field(ge=0)
    invalid_unicode_ratio: float = Field(ge=0, le=1)
    unreadable_character_ratio: float = Field(ge=0, le=1)
    is_empty: bool
    is_image_only: bool
    is_scanned: bool
    needs_ocr: bool

    @model_validator(mode="after")
    def validate_ordinals(self) -> ExtractedPage:
        if tuple(block.ordinal for block in self.blocks) != tuple(
            range(len(self.blocks))
        ):
            raise ValueError("page block ordinals must be contiguous and ordered")
        if tuple(table.ordinal for table in self.tables) != tuple(
            range(len(self.tables))
        ):
            raise ValueError("page table ordinals must be contiguous and ordered")
        return self


class PdfDocumentMetadata(ExtractionModel):
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    modification_date: str | None = None
    is_encrypted: bool = False
    pypdf_version: str
    pdfplumber_version: str


class OcrAssessment(ExtractionModel):
    status: ExtractionStatus
    pages_requiring_ocr: tuple[int, ...] = ()
    reason: str | None = Field(default=None, max_length=100)
    page_reasons: dict[int, tuple[str, ...]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_status(self) -> OcrAssessment:
        pages = tuple(sorted(set(self.pages_requiring_ocr)))
        if pages != self.pages_requiring_ocr:
            raise ValueError("OCR page numbers must be sorted and unique")
        if self.status is ExtractionStatus.NEEDS_OCR:
            if not pages or self.reason is None:
                raise ValueError("needs_ocr requires pages and a reason")
        elif pages or self.reason is not None or self.page_reasons:
            raise ValueError("successful extraction cannot require OCR pages")
        if set(self.page_reasons) != set(pages):
            raise ValueError("OCR page reasons must match pages requiring OCR")
        return self


class ExtractedBlock(ExtractionModel):
    block_id: str
    ordinal: int = Field(ge=0)
    block_type: ExtractedBlockType
    section: tuple[str, ...] = ()
    text: str = Field(min_length=1)
    label: str | None = None
    heading_level: int | None = Field(default=None, ge=1, le=6)
    links: tuple[ExtractedLink, ...] = ()
    table: ExtractedTable | None = None
    source_locator: SourceLocator

    @field_validator("block_id")
    @classmethod
    def validate_block_id(cls, value: str) -> str:
        normalized = value.casefold()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("block_id must be a lowercase SHA-256 hex digest")
        return normalized

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> ExtractedBlock:
        if (self.block_type is ExtractedBlockType.HEADING) != (
            self.heading_level is not None
        ):
            raise ValueError("only heading blocks require heading_level")
        if (self.block_type is ExtractedBlockType.TABLE) != (self.table is not None):
            raise ValueError("only table blocks require table data")
        if self.block_type is ExtractedBlockType.FACT and not self.label:
            raise ValueError("fact blocks require a label")
        return self


class ExtractionStatistics(ExtractionModel):
    block_count: int = Field(ge=0)
    heading_count: int = Field(ge=0)
    paragraph_count: int = Field(ge=0)
    list_item_count: int = Field(ge=0)
    table_count: int = Field(ge=0)
    table_row_count: int = Field(ge=0)
    link_count: int = Field(ge=0)
    text_character_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    page_count: int = Field(default=0, ge=0)
    empty_page_count: int = Field(default=0, ge=0)
    image_only_page_count: int = Field(default=0, ge=0)
    pages_requiring_ocr_count: int = Field(default=0, ge=0)


class ExtractedDocumentContent(ExtractionModel):
    schema_version: str = "1.1"
    extraction_id: UUID
    product_id: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=1, max_length=4000)
    final_url: str = Field(min_length=1, max_length=4000)
    source_storage_key: str = Field(min_length=1, max_length=1000)
    source_sha256: str
    source_mime_type: str = Field(min_length=1, max_length=255)
    language: str | None = Field(default=None, max_length=35)
    extractor: str = Field(min_length=1, max_length=100)
    extractor_version: str = Field(min_length=1, max_length=50)
    status: ExtractionStatus = ExtractionStatus.SUCCESS
    blocks: tuple[ExtractedBlock, ...] = ()
    pages: tuple[ExtractedPage, ...] = ()
    pdf_metadata: PdfDocumentMetadata | None = None
    ocr: OcrAssessment = OcrAssessment(status=ExtractionStatus.SUCCESS)
    statistics: ExtractionStatistics
    warnings: tuple[ExtractionWarning, ...] = ()

    @field_validator("source_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.casefold()
        if not _SHA256.fullmatch(normalized):
            raise ValueError("source_sha256 must be a lowercase SHA-256 hex digest")
        return normalized

    @model_validator(mode="after")
    def validate_block_order_and_counts(self) -> ExtractedDocumentContent:
        if tuple(block.ordinal for block in self.blocks) != tuple(
            range(len(self.blocks))
        ):
            raise ValueError("block ordinals must be contiguous and document ordered")
        if len({block.block_id for block in self.blocks}) != len(self.blocks):
            raise ValueError("block IDs must be unique")
        page_blocks = tuple(block for page in self.pages for block in page.blocks)
        all_blocks = self.blocks + page_blocks
        if len({block.block_id for block in all_blocks}) != len(all_blocks):
            raise ValueError("block IDs must be unique across the document")
        if tuple(page.page_number for page in self.pages) != tuple(
            range(1, len(self.pages) + 1)
        ):
            raise ValueError("page numbers must be contiguous and one-based")
        if self.statistics.block_count != len(all_blocks):
            raise ValueError("statistics block count did not match blocks")
        if self.statistics.page_count != len(self.pages):
            raise ValueError("statistics page count did not match pages")
        if self.statistics.warning_count != len(self.warnings):
            raise ValueError("statistics warning count did not match warnings")
        if self.status is not self.ocr.status:
            raise ValueError("document and OCR statuses must match")
        if self.statistics.pages_requiring_ocr_count != len(
            self.ocr.pages_requiring_ocr
        ):
            raise ValueError("statistics OCR page count did not match assessment")
        return self


class ExtractedDocument(ExtractedDocumentContent):
    representation_artifact: StoredArtifact
    extracted_at: datetime


class PersistedExtraction(ExtractionModel):
    extraction_id: UUID
    source_artifact_id: UUID
    product_id: str
    source_url: str
    representation_artifact: StoredArtifact
    extractor: str
    extractor_version: str
    status: ExtractionStatus
    ocr: OcrAssessment
    statistics: ExtractionStatistics
    warnings: tuple[ExtractionWarning, ...]
    extracted_at: datetime


def extraction_id_for(
    *,
    source_sha256: str,
    source_storage_key: str,
    source_mime_type: str,
    product_id: str,
    source_url: str,
    final_url: str,
    language: str | None,
    extractor: str,
    extractor_version: str,
) -> UUID:
    identity = "\x1f".join(
        (
            source_sha256.casefold(),
            source_storage_key,
            source_mime_type.casefold(),
            product_id,
            source_url,
            final_url,
            language or "",
            extractor,
            extractor_version,
        )
    )
    return uuid5(_EXTRACTION_NAMESPACE, identity)
