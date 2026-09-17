from __future__ import annotations

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


class SourceLocator(ExtractionModel):
    css_path: str | None = Field(default=None, max_length=4000)
    page: int | None = Field(default=None, ge=1)

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


class ExtractedDocumentContent(ExtractionModel):
    schema_version: str = "1.0"
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
    blocks: tuple[ExtractedBlock, ...]
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
        if self.statistics.block_count != len(self.blocks):
            raise ValueError("statistics block count did not match blocks")
        if self.statistics.warning_count != len(self.warnings):
            raise ValueError("statistics warning count did not match warnings")
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
