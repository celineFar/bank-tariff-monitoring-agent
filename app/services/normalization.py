from __future__ import annotations

from typing import Protocol

from app.domain.acquisition import (
    ContentBlockType,
    DocumentArtifact,
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
    NormalizedTable,
    SourceReference,
)
from app.domain.pdf_extraction import PdfAdmissionRelevance
from app.services.block_normalizer import normalize_block
from app.services.normalization_baseline import NormalizationBaseline, score_page
from app.services.pdf_extraction import (
    PdfExtractionError,
    PdfExtractionOutcome,
    PdfModelUnavailable,
    PdfTranscriptionFailed,
    PdfUnreadable,
    empty_text_pages,
    ocr_filled_pages,
)
from app.services.table_normalizer import normalize_table_with_report

_PDF_FAILURE_CODES = {
    PdfUnreadable: NormalizationWarningCode.ARTIFACT_UNAVAILABLE,
    PdfModelUnavailable: NormalizationWarningCode.PDF_MODEL_REQUIRED,
    PdfTranscriptionFailed: NormalizationWarningCode.PDF_MODEL_FAILED,
}


def _outcome_warnings(
    outcome: PdfExtractionOutcome, document_id: str
) -> list[NormalizationWarning]:
    """What a successful (or deliberately skipped) PDF outcome should report."""
    warnings: list[NormalizationWarning] = []
    admission = outcome.plan.admission
    if outcome.normalized_document.extraction_method == "pdf_skipped":
        irrelevant = admission.relevance is PdfAdmissionRelevance.IRRELEVANT
        warnings.append(
            NormalizationWarning(
                code=(
                    NormalizationWarningCode.PDF_SKIPPED_IRRELEVANT
                    if irrelevant
                    else NormalizationWarningCode.PDF_SKIPPED_HISTORICAL
                ),
                source_id=document_id,
                message=(
                    f"Not transcribed ({admission.relevance.value}/"
                    f"{admission.temporal_status.value}): "
                    + ("; ".join(admission.decision_basis) or admission.reason)
                )[:2000],
            )
        )
        return warnings
    if pages := empty_text_pages(outcome):
        warnings.append(
            NormalizationWarning(
                code=NormalizationWarningCode.PDF_PAGE_EMPTY,
                source_id=document_id,
                message=(
                    "Pages with a text layer came back empty from transcription: "
                    + ", ".join(str(page) for page in pages)
                ),
            )
        )
    if pages := ocr_filled_pages(outcome):
        warnings.append(
            NormalizationWarning(
                code=NormalizationWarningCode.PDF_OCR_FILLED,
                source_id=document_id,
                message="Pages read by local OCR: " + ", ".join(str(p) for p in pages),
            )
        )
    return warnings


class ArtifactReader(Protocol):
    async def read(self, artifact: StoredArtifact) -> bytes: ...


class PdfExtractor(Protocol):
    async def extract(
        self, document: DocumentArtifact, content: bytes, *, document_id: str
    ) -> PdfExtractionOutcome: ...


class NoPdfExtractor:
    """For offline tools that normalize pages without Gemini: every linked PDF
    is reported as `PDF_MODEL_REQUIRED` instead of being transcribed."""

    async def extract(
        self, document: DocumentArtifact, content: bytes, *, document_id: str
    ) -> PdfExtractionOutcome:
        raise PdfModelUnavailable("No PDF extractor is configured")


class StructuralNormalizationService:
    """Turn acquisition artifacts into a uniform, evidence-linked source bundle."""

    def __init__(
        self,
        *,
        artifact_reader: ArtifactReader,
        pdf_extractor: PdfExtractor,
        baseline: NormalizationBaseline | None = None,
    ) -> None:
        self._artifact_reader = artifact_reader
        self._pdf_extractor = pdf_extractor
        self._baseline = baseline

    async def normalize(self, artifact: PageArtifact) -> NormalizedSourceBundle:
        warnings: list[NormalizationWarning] = []
        page_id = f"page:{artifact.page_content_hash[:16]}"
        normalized_tables: list[NormalizedTable] = []
        for table in artifact.tables:
            normalized_table, reasons = normalize_table_with_report(table)
            normalized_tables.append(normalized_table)
            if reasons:
                warnings.append(
                    NormalizationWarning(
                        code=NormalizationWarningCode.AMBIGUOUS_TABLE,
                        source_id=f"{page_id}:{table.id}",
                        message="; ".join(reasons)[:2000],
                    )
                )
        # Artifacts stored before blocks carried their table id fall back to
        # document order, which the parser kept for table blocks and tables.
        positional_ids = iter(table.id for table in normalized_tables)
        blocks = []
        for block in artifact.blocks:
            table_id = None
            if block.type is ContentBlockType.TABLE:
                positional_id = next(positional_ids, None)
                table_id = block.table_id or positional_id
            blocks.append(
                normalize_block(
                    block,
                    table_id=table_id,
                    extraction_method=artifact.acquisition_mode.value,
                )
            )

        documents: list[NormalizedDocument] = [
            NormalizedDocument(
                id=page_id,
                name=artifact.title or str(artifact.canonical_url),
                source_url=artifact.canonical_url,
                source_type=SourceType.PAGE,
                mime_type="text/html",
                content_sha256=artifact.page_content_hash,
                extraction_method=artifact.acquisition_mode.value,
                # Scored against the page's seed baseline below; a page with no
                # baseline is not measured rather than claimed perfect.
                quality_score=None,
                blocks=tuple(blocks),
                tables=tuple(normalized_tables),
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

        page_baseline = (
            self._baseline.for_urls(
                str(artifact.url), str(artifact.canonical_url), str(artifact.final_url)
            )
            if self._baseline is not None
            else None
        )
        if page_baseline is not None:
            result = score_page(documents[0], page_baseline)
            documents[0] = documents[0].model_copy(
                update={"quality_score": result.score}
            )
            if result.failures:
                warnings.append(
                    NormalizationWarning(
                        code=NormalizationWarningCode.BASELINE_MISMATCH,
                        source_id=page_id,
                        message=(
                            f"{len(result.failures)} of {result.checks} baseline "
                            "checks failed: " + "; ".join(result.failures)
                        )[:2000],
                    )
                )

        # Document ids are content-addressed, never positional: a new link
        # appearing earlier on the page must not rename the documents after it,
        # because every evidence id -- and so every extraction-cache key --
        # hashes the document id alongside the text it quotes.
        seen_document_ids: set[str] = set()
        for source_document in artifact.downloadable_documents:
            document_id = f"document:{source_document.sha256[:12]}"
            if document_id in seen_document_ids:
                continue
            seen_document_ids.add(document_id)
            try:
                content = await self._artifact_reader.read(source_document.artifact)
            except Exception as exc:
                documents.append(self._empty_pdf_document(source_document, document_id))
                warnings.append(
                    NormalizationWarning(
                        code=NormalizationWarningCode.ARTIFACT_UNAVAILABLE,
                        source_id=document_id,
                        message=f"Linked document artifact could not be read: {exc}",
                    )
                )
                continue
            try:
                outcome = await self._pdf_extractor.extract(
                    source_document, content, document_id=document_id
                )
            except PdfExtractionError as exc:
                # Only the extractor's own, expected failures become warnings;
                # anything else is a bug and fails the normalization stage.
                documents.append(self._empty_pdf_document(source_document, document_id))
                warnings.append(
                    NormalizationWarning(
                        code=_PDF_FAILURE_CODES.get(
                            type(exc), NormalizationWarningCode.PDF_MODEL_FAILED
                        ),
                        source_id=document_id,
                        message=f"PDF transcription failed: {exc}",
                    )
                )
                continue
            documents.append(outcome.normalized_document)
            warnings.extend(_outcome_warnings(outcome, document_id))

        return NormalizedSourceBundle(
            canonical_url=artifact.canonical_url,
            acquisition_content_hash=artifact.content_hash,
            documents=tuple(documents),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _empty_pdf_document(
        document: DocumentArtifact, document_id: str
    ) -> NormalizedDocument:
        return NormalizedDocument(
            id=document_id,
            name=document.document_name,
            source_url=document.final_url,
            source_type=SourceType.PDF,
            mime_type=document.mime_type,
            content_sha256=document.sha256,
            extraction_method="gemini_pdf_unavailable",
            quality_score=0,
        )
