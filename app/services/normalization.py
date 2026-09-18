from __future__ import annotations

from typing import Protocol

from app.config import OcrSettings
from app.domain.acquisition import (
    ContentBlockType,
    PageArtifact,
    SourceType,
    StoredArtifact,
)
from app.domain.normalization import (
    NormalizationWarning,
    NormalizationWarningCode,
    NormalizedDocument,
    NormalizedLink,
    NormalizedSourceBundle,
    SourceReference,
)
from app.services.api_payload_normalizer import normalize_network_payload
from app.services.block_normalizer import normalize_block
from app.services.pdf_text_extractor import OcrExtractor, PdfTextExtractor
from app.services.table_normalizer import normalize_table


class ArtifactReader(Protocol):
    async def read(self, artifact: StoredArtifact) -> bytes: ...


class StructuralNormalizationService:
    """Turn acquisition artifacts into a uniform, evidence-linked source bundle."""

    def __init__(
        self,
        ocr_settings: OcrSettings,
        *,
        artifact_reader: ArtifactReader | None = None,
        ocr_extractor: OcrExtractor | None = None,
    ) -> None:
        self._artifact_reader = artifact_reader
        self._pdf_extractor = PdfTextExtractor(
            ocr_settings, ocr_extractor=ocr_extractor
        )

    async def normalize(self, artifact: PageArtifact) -> NormalizedSourceBundle:
        warnings: list[NormalizationWarning] = []
        normalized_tables = tuple(normalize_table(table) for table in artifact.tables)
        table_ids = iter(table.id for table in normalized_tables)
        blocks = []
        for block in artifact.blocks:
            table_id = (
                next(table_ids, None)
                if block.type is ContentBlockType.TABLE
                else None
            )
            blocks.append(
                normalize_block(
                    block,
                    table_id=table_id,
                    extraction_method=artifact.acquisition_mode.value,
                )
            )

        documents: list[NormalizedDocument] = [
            NormalizedDocument(
                id=f"page:{artifact.content_hash[:16]}",
                name=artifact.title or str(artifact.canonical_url),
                source_url=artifact.canonical_url,
                source_type=SourceType.PAGE,
                mime_type="text/html",
                content_sha256=artifact.content_hash,
                extraction_method=artifact.acquisition_mode.value,
                quality_score=1.0,
                blocks=tuple(blocks),
                tables=normalized_tables,
                links=tuple(
                    NormalizedLink(
                        id=link.id,
                        url=link.url,
                        raw_href=link.raw_href,
                        fragment=link.fragment,
                        text=link.text,
                        title=link.title,
                        rel=link.rel,
                        declared_mime_type=link.declared_mime_type,
                        same_allowlisted_source=link.same_allowlisted_source,
                        downloadable=link.downloadable,
                        source_refs=(
                            SourceReference(
                                source_item_id=link.id, locator=link.locator
                            ),
                        ),
                    )
                    for link in artifact.links
                ),
            )
        ]

        for index, source_document in enumerate(artifact.downloadable_documents):
            document_id = f"document:{index}:{source_document.sha256[:12]}"
            if self._artifact_reader is None:
                documents.append(
                    PdfTextExtractor._empty_document(source_document, document_id)
                )
                warnings.append(
                    NormalizationWarning(
                        code=NormalizationWarningCode.ARTIFACT_UNAVAILABLE,
                        source_id=document_id,
                        message="No artifact reader was configured for the linked document",
                    )
                )
                continue
            try:
                content = await self._artifact_reader.read(source_document.artifact)
            except Exception as exc:
                documents.append(
                    PdfTextExtractor._empty_document(source_document, document_id)
                )
                warnings.append(
                    NormalizationWarning(
                        code=NormalizationWarningCode.ARTIFACT_UNAVAILABLE,
                        source_id=document_id,
                        message=f"Linked document artifact could not be read: {exc}",
                    )
                )
                continue
            normalized_document, document_warnings = self._pdf_extractor.extract(
                source_document, content, document_id=document_id
            )
            documents.append(normalized_document)
            warnings.extend(document_warnings)

        for index, payload in enumerate(artifact.network_payloads):
            document, payload_warnings = normalize_network_payload(payload, index=index)
            documents.append(document)
            warnings.extend(payload_warnings)

        return NormalizedSourceBundle(
            canonical_url=artifact.canonical_url,
            acquisition_content_hash=artifact.content_hash,
            documents=tuple(documents),
            warnings=tuple(warnings),
        )
