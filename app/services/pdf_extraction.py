from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence

from google.genai.errors import APIError
from pydantic import BaseModel, ConfigDict

from app.config import OcrSettings, PdfExtractionSettings
from app.domain.acquisition import DocumentArtifact, SourceLocator, SourceType
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedNote,
    NormalizedTable,
    NormalizedTableCell,
    NormalizedTableRow,
    SourceReference,
    normalize_multiline_text,
)
from app.domain.pdf_extraction import (
    OcrDocumentResult,
    OcrPageOutcome,
    OcrPageResult,
    PdfAdmissionRelevance,
    PdfExtractedBlockType,
    PdfExtractionPlan,
    PdfExtractionResponse,
    PdfInputMode,
    PdfModelUsage,
    PdfTemporalStatus,
    PdfTranscriptionSource,
    ocr_block_id,
)
from app.repositories.contracts import PdfExtractionRepository
from app.services.gemini_pdf_extractor import AdkGeminiPdfExtractor
from app.services.model_call_usage import (
    PostgresModelCallUsageRepository,
    record_model_cache_hit,
)
from app.services.model_pricing import enforce_model_price_cap
from app.services.ocr_transcriber import OcrTranscriber
from app.services.pdf_admission import assess_pdf_metadata
from app.services.pdf_input_probe import probe_pdf_input
from app.services.pdf_rasterizer import PageRasterizer
from app.services.scalar_normalizer import extract_scalar_candidates
from app.services.telemetry import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer()


class PdfExtractionOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan: PdfExtractionPlan
    normalized_document: NormalizedDocument
    model_name: str | None = None
    usage: PdfModelUsage = PdfModelUsage()
    reused: bool = False
    ocr: OcrDocumentResult | None = None
    page_sources: tuple[tuple[int, PdfTranscriptionSource], ...] = ()


class InMemoryPdfExtractionRepository:
    def __init__(self) -> None:
        self._values: dict[tuple[str, ...], PdfExtractionResponse] = {}

    async def get_exact(
        self,
        *,
        document_sha256: str,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprint: str,
    ) -> PdfExtractionResponse | None:
        return self._values.get(
            _cache_key(
                document_sha256,
                schema_version,
                prompt_version,
                model_name,
                content_fingerprint,
            )
        )

    async def save(
        self,
        *,
        document_sha256: str,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprint: str,
        response: PdfExtractionResponse,
    ) -> None:
        self._values[
            _cache_key(
                document_sha256,
                schema_version,
                prompt_version,
                model_name,
                content_fingerprint,
            )
        ] = response


class GeminiPdfExtractionService:
    def __init__(
        self,
        settings: PdfExtractionSettings,
        repository: PdfExtractionRepository,
        *,
        api_key: str | None,
        usage_repository: PostgresModelCallUsageRepository | None = None,
        ocr_settings: OcrSettings | None = None,
        ocr_transcriber: OcrTranscriber | None = None,
        rasterizer: PageRasterizer | None = None,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._api_key = api_key
        self._usage_repository = usage_repository
        self._ocr_settings = ocr_settings
        self._ocr_transcriber = ocr_transcriber
        self._rasterizer = rasterizer
        # Local OCR costs no credits, but re-rendering the same page inside one
        # process is pure waste; this memo is deliberately not the Gemini cache.
        self._ocr_memo: dict[tuple[str, int], OcrPageResult] = {}
        self._models = tuple(
            dict.fromkeys((settings.model_name, *settings.fallback_model_names))
        )
        enforce_model_price_cap(
            self._models,
            max_price_per_million_tokens_usd=(
                settings.max_price_per_million_tokens_usd
            ),
        )

    def plan(
        self,
        document: DocumentArtifact,
        content: bytes,
        *,
        document_id: str,
    ) -> PdfExtractionPlan:
        admission = assess_pdf_metadata(document, as_of=document.retrieved_at.date())
        probe = probe_pdf_input(
            content, text_threshold=self._settings.probe_text_threshold
        )
        fingerprint = hashlib.sha256(
            "\x1f".join(
                (
                    document.sha256,
                    self._settings.schema_version,
                    self._settings.prompt_version,
                    admission.model_dump_json(),
                    probe.model_dump_json(),
                )
            ).encode()
        ).hexdigest()
        return PdfExtractionPlan(
            document_id=document_id,
            document_sha256=document.sha256,
            admission=admission,
            input_probe=probe,
            schema_version=self._settings.schema_version,
            prompt_version=self._settings.prompt_version,
            model_names=self._models,
            content_fingerprint=fingerprint,
        )

    @property
    def _ocr_ready(self) -> bool:
        return bool(
            self._ocr_settings
            and self._ocr_settings.enabled
            and self._ocr_transcriber is not None
            and self._ocr_transcriber.available
            and self._rasterizer is not None
            and self._rasterizer.available
        )

    def _pages_needing_ocr(
        self, plan: PdfExtractionPlan, normalized: NormalizedDocument
    ) -> tuple[int, ...]:
        """Pages the probe called image-only that Gemini returned nothing for.

        Both halves matter. A machine-readable page that produced no blocks is a
        transcription problem OCR cannot fix, and re-reading it would only add a
        second, weaker opinion of the same text layer.
        """
        populated = _populated_pages(normalized)
        return tuple(
            page.page_number
            for page in plan.input_probe.pages
            if page.input_mode is PdfInputMode.IMAGE_ONLY
            and page.page_number not in populated
        )

    async def _transcribe_pages(
        self,
        content: bytes,
        plan: PdfExtractionPlan,
        pages: Sequence[int],
    ) -> OcrDocumentResult:
        settings = self._ocr_settings
        assert settings is not None and self._rasterizer is not None
        transcriber = self._ocr_transcriber
        assert transcriber is not None

        results: list[OcrPageResult] = []
        pending: list[int] = []
        for number in pages:
            memo = self._ocr_memo.get((plan.document_sha256, number))
            if memo is not None:
                results.append(memo)
            else:
                pending.append(number)

        if pending:
            # Page numbers, outcomes, and confidence only. Page images and
            # recognized body text never reach an exported span.
            with tracer.start_as_current_span("pdf ocr") as span:
                span.set_attribute("tariff.document_id", plan.document_id)
                span.set_attribute("tariff.ocr.pages_requested", len(pending))
                span.set_attribute("tariff.ocr.languages", settings.languages)
                span.set_attribute("tariff.ocr.render_dpi", settings.render_dpi)
                span.set_attribute(
                    "tariff.ocr.engine_version", transcriber.engine_version
                )
                results.extend(
                    await self._render_and_read(
                        content, pending, document_sha256=plan.document_sha256
                    )
                )
                transcribed = [
                    item
                    for item in results
                    if item.outcome is OcrPageOutcome.TRANSCRIBED
                ]
                span.set_attribute("tariff.ocr.pages_transcribed", len(transcribed))
                span.set_attribute(
                    "tariff.ocr.mean_confidence",
                    round(
                        sum(item.mean_confidence for item in transcribed)
                        / len(transcribed),
                        1,
                    )
                    if transcribed
                    else 0.0,
                )

        for result in sorted(results, key=lambda item: item.page_number):
            logger.info(
                "OCR page %s of %s: %s (confidence %.1f, %s words)%s",
                result.page_number,
                plan.document_id,
                result.outcome.value,
                result.mean_confidence,
                result.word_count,
                f" - {result.detail}" if result.detail else "",
            )
        return OcrDocumentResult(
            engine_version=transcriber.engine_version,
            languages=settings.languages,
            pages=tuple(sorted(results, key=lambda item: item.page_number)),
        )

    async def _render_and_read(
        self, content: bytes, pages: Sequence[int], *, document_sha256: str
    ) -> list[OcrPageResult]:
        settings = self._ocr_settings
        assert settings is not None and self._rasterizer is not None
        transcriber = self._ocr_transcriber
        assert transcriber is not None

        results: list[OcrPageResult] = []
        rendered = self._rasterizer.rasterize_pages(
            content,
            pages,
            dpi=settings.render_dpi,
            max_pages=settings.max_pages,
            max_pixels=settings.max_pixels_per_page,
        )
        for skipped in rendered.skipped:
            results.append(
                OcrPageResult(
                    page_number=skipped.page_number,
                    outcome=OcrPageOutcome.SKIPPED,
                    detail=skipped.reason,
                )
            )
        for page in rendered.pages:
            result = await transcriber.transcribe(
                page,
                languages=settings.languages,
                timeout_seconds=settings.timeout_seconds,
                min_confidence=settings.min_confidence,
            )
            self._ocr_memo[(document_sha256, page.page_number)] = result
            results.append(result)
        return results

    async def _apply_ocr(
        self,
        document: DocumentArtifact,
        plan: PdfExtractionPlan,
        normalized: NormalizedDocument,
        content: bytes,
    ) -> tuple[
        NormalizedDocument,
        OcrDocumentResult | None,
        tuple[tuple[int, PdfTranscriptionSource], ...],
    ]:
        """Fill scanned pages Gemini left empty, then record per-page provenance."""
        pages = self._pages_needing_ocr(plan, normalized)
        ocr_result: OcrDocumentResult | None = None
        if pages and self._ocr_ready:
            ocr_result = await self._transcribe_pages(content, plan, pages)
            blocks = _ocr_blocks(document, plan, ocr_result)
            if blocks:
                normalized = _with_ocr_blocks(normalized, plan, blocks)
        elif pages:
            logger.info(
                "PDF %s has %s image-only page(s) with no transcription and no "
                "OCR engine available; they stay empty rather than guessed",
                plan.document_id,
                len(pages),
            )
        return normalized, ocr_result, _page_sources(plan, normalized, ocr_result)

    async def _ocr_only(
        self,
        document: DocumentArtifact,
        plan: PdfExtractionPlan,
        content: bytes,
    ) -> PdfExtractionOutcome | None:
        """Engine-unavailable fallback: every Gemini model failed.

        A degraded transcription that says so is worth more than no evidence at
        all, but it must never be mistaken for the model path, so the document
        records the OCR engine as its extraction method.
        """
        if not self._ocr_ready:
            return None
        pages = tuple(page.page_number for page in plan.input_probe.pages)
        if not pages:
            return None
        ocr_result = await self._transcribe_pages(content, plan, pages)
        blocks = _ocr_blocks(document, plan, ocr_result)
        if not blocks:
            return None
        method = _ocr_method(ocr_result)
        populated = {
            ref.locator.pdf_page
            for block in blocks
            for ref in block.source_refs
            if ref.locator.pdf_page is not None
        }
        normalized = NormalizedDocument(
            id=plan.document_id,
            name=document.document_name,
            source_url=document.final_url,
            source_type=SourceType.PDF,
            mime_type=document.mime_type,
            content_sha256=document.sha256,
            extraction_method=method,
            quality_score=(
                len(populated) / plan.input_probe.page_count
                if plan.input_probe.page_count
                else 0.0
            ),
            pdf_input_mode=plan.input_probe.document_mode,
            pdf_admission=plan.admission,
            blocks=blocks,
        )
        logger.warning(
            "All Gemini PDF models failed for %s; recovered %s page(s) with %s",
            plan.document_id,
            len(populated),
            method,
        )
        return PdfExtractionOutcome(
            plan=plan,
            normalized_document=normalized,
            model_name=None,
            ocr=ocr_result,
            page_sources=_page_sources(plan, normalized, ocr_result),
        )

    def _skip_reason(self, plan: PdfExtractionPlan) -> str | None:
        """Decide from link metadata alone whether transcription is worth paying for."""
        if plan.admission.relevance is PdfAdmissionRelevance.IRRELEVANT:
            return "metadata relevance is irrelevant"
        if (
            self._settings.skip_historical
            and plan.admission.temporal_status is PdfTemporalStatus.HISTORICAL
        ):
            return "metadata temporal status is historical"
        return None

    async def extract(
        self,
        document: DocumentArtifact,
        content: bytes,
        *,
        document_id: str,
    ) -> PdfExtractionOutcome:
        plan = self.plan(document, content, document_id=document_id)
        logger.info(
            "PDF %s classified as %s (%s); metadata admission=%s/%s",
            document_id,
            plan.input_probe.document_mode.value,
            _page_mode_summary(plan),
            plan.admission.relevance.value,
            plan.admission.temporal_status.value,
        )
        skip_reason = self._skip_reason(plan)
        if skip_reason is not None:
            logger.info(
                "Skipping Gemini PDF transcription for %s: %s", document_id, skip_reason
            )
            return PdfExtractionOutcome(
                plan=plan,
                normalized_document=_empty_document(document, plan, "pdf_skipped"),
            )
        if self._api_key is None:
            raise RuntimeError("GEMINI_API_KEY is required for PDF extraction")

        failures: list[Exception] = []
        for index, model_name in enumerate(self._models, start=1):
            cached = await self._repository.get_exact(
                document_sha256=document.sha256,
                schema_version=plan.schema_version,
                prompt_version=plan.prompt_version,
                model_name=model_name,
                content_fingerprint=plan.content_fingerprint,
            )
            if cached is not None:
                _validate_response(cached, plan)
                await record_model_cache_hit(
                    self._usage_repository,
                    stage="pdf.transcription",
                    operation="generate_content",
                    model_id=model_name,
                )
                logger.info(
                    "Reusing cached Gemini PDF extraction for %s with %s",
                    document_id,
                    model_name,
                )
                normalized, ocr_result, sources = await self._apply_ocr(
                    document,
                    plan,
                    _normalize(document, plan, cached, model_name),
                    content,
                )
                return PdfExtractionOutcome(
                    plan=plan,
                    normalized_document=normalized,
                    model_name=model_name,
                    reused=True,
                    ocr=ocr_result,
                    page_sources=sources,
                )
            logger.info(
                "Gemini PDF model attempt %s/%s for %s: %s",
                index,
                len(self._models),
                document_id,
                model_name,
            )
            extractor = AdkGeminiPdfExtractor(
                model_name,
                api_key=self._api_key,
                max_attempts=self._settings.max_attempts,
                backoff_base_seconds=self._settings.backoff_base_seconds,
                max_backoff_seconds=self._settings.max_backoff_seconds,
                retry_jitter_ratio=self._settings.retry_jitter_ratio,
                usage_repository=self._usage_repository,
            )
            try:
                response = await extractor.extract(content, plan)
                _validate_response(response, plan)
            except (APIError, RuntimeError, ValueError) as exc:
                failures.append(exc)
                if index < len(self._models):
                    logger.warning(
                        "PDF model %s failed for %s (%s); falling back to %s",
                        model_name,
                        document_id,
                        _failure_summary(exc),
                        self._models[index],
                    )
                    continue
                recovered = await self._ocr_only(document, plan, content)
                if recovered is not None:
                    return recovered
                raise RuntimeError(
                    f"all Gemini PDF models failed for {document_id}: "
                    f"{_failure_summary(exc)}"
                ) from exc
            await self._repository.save(
                document_sha256=document.sha256,
                schema_version=plan.schema_version,
                prompt_version=plan.prompt_version,
                model_name=model_name,
                content_fingerprint=plan.content_fingerprint,
                response=response,
            )
            normalized, ocr_result, sources = await self._apply_ocr(
                document,
                plan,
                _normalize(document, plan, response, model_name),
                content,
            )
            return PdfExtractionOutcome(
                plan=plan,
                normalized_document=normalized,
                model_name=model_name,
                usage=extractor.usage,
                ocr=ocr_result,
                page_sources=sources,
            )
        raise AssertionError(f"PDF model sequence exhausted: {failures}")


def ocr_method_name(engine_version: str) -> str:
    """The single spelling of an OCR extraction method, used by every consumer."""
    return f"ocr:tesseract:{engine_version}"


def is_ocr_method(method: str | None) -> bool:
    return bool(method) and str(method).startswith("ocr:")


def _ocr_method(result: OcrDocumentResult) -> str:
    return ocr_method_name(result.engine_version)


def _populated_pages(document: NormalizedDocument) -> set[int]:
    pages = {
        ref.locator.pdf_page
        for block in document.blocks
        for ref in block.source_refs
        if ref.locator.pdf_page is not None
    }
    pages |= {
        ref.locator.pdf_page
        for table in document.tables
        for ref in table.source_refs
        if ref.locator.pdf_page is not None
    }
    return pages


def _ocr_blocks(
    document: DocumentArtifact,
    plan: PdfExtractionPlan,
    result: OcrDocumentResult,
) -> tuple[NormalizedBlock, ...]:
    """One block per transcribed page, carrying the OCR engine as its method."""
    method = _ocr_method(result)
    blocks: list[NormalizedBlock] = []
    for page in result.pages:
        if page.outcome is not OcrPageOutcome.TRANSCRIBED:
            continue
        text = normalize_multiline_text(page.text)
        if not text:
            continue
        block_id = ocr_block_id(plan.document_id, page.page_number)
        locator = SourceLocator(
            source_url=document.final_url,
            source_type=SourceType.PDF,
            pdf_page=page.page_number,
        )
        blocks.append(
            NormalizedBlock(
                id=block_id,
                type=NormalizedBlockType.PARAGRAPH,
                raw_text=page.text,
                text=text,
                scalar_candidates=extract_scalar_candidates(text),
                source_refs=(
                    SourceReference(source_item_id=block_id, locator=locator),
                ),
                extraction_method=method,
            )
        )
    return tuple(blocks)


def _with_ocr_blocks(
    normalized: NormalizedDocument,
    plan: PdfExtractionPlan,
    blocks: tuple[NormalizedBlock, ...],
) -> NormalizedDocument:
    merged = tuple(normalized.blocks) + blocks
    populated = _populated_pages(normalized.model_copy(update={"blocks": merged}))
    quality = (
        len(populated) / plan.input_probe.page_count
        if plan.input_probe.page_count
        else 0.0
    )
    return normalized.model_copy(update={"blocks": merged, "quality_score": quality})


def _page_sources(
    plan: PdfExtractionPlan,
    normalized: NormalizedDocument,
    result: OcrDocumentResult | None,
) -> tuple[tuple[int, PdfTranscriptionSource], ...]:
    """Record which engine actually produced each page's content."""
    ocr_pages = set(result.transcribed_pages) if result is not None else set()
    populated = _populated_pages(normalized)
    sources: list[tuple[int, PdfTranscriptionSource]] = []
    for page in plan.input_probe.pages:
        number = page.page_number
        if number in ocr_pages:
            source = PdfTranscriptionSource.OCR
        elif number in populated:
            source = PdfTranscriptionSource.GEMINI
        else:
            source = PdfTranscriptionSource.NONE
        sources.append((number, source))
    return tuple(sources)


def _validate_response(
    response: PdfExtractionResponse, plan: PdfExtractionPlan
) -> None:
    expected = set(range(1, plan.input_probe.page_count + 1))
    received = {page.page_number for page in response.pages}
    if received != expected:
        raise ValueError(
            f"Gemini PDF page coverage mismatch: expected {sorted(expected)}, "
            f"received {sorted(received)}"
        )


def _normalize(
    document: DocumentArtifact,
    plan: PdfExtractionPlan,
    response: PdfExtractionResponse,
    model_name: str,
) -> NormalizedDocument:
    blocks: list[NormalizedBlock] = []
    tables: list[NormalizedTable] = []
    method = f"gemini_pdf:{model_name}"
    block_types = {
        PdfExtractedBlockType.HEADING: NormalizedBlockType.HEADING,
        PdfExtractedBlockType.PARAGRAPH: NormalizedBlockType.PARAGRAPH,
        PdfExtractedBlockType.LIST: NormalizedBlockType.LIST,
        PdfExtractedBlockType.KEY_VALUE: NormalizedBlockType.KEY_VALUE,
        PdfExtractedBlockType.OTHER: NormalizedBlockType.OTHER,
    }
    for page in sorted(response.pages, key=lambda item: item.page_number):
        locator = SourceLocator(
            source_url=document.final_url,
            source_type=SourceType.PDF,
            pdf_page=page.page_number,
        )
        for index, item in enumerate(page.blocks):
            text = normalize_multiline_text(item.text)
            if not text:
                continue
            block_id = f"{plan.document_id}:page:{page.page_number}:block:{index}"
            blocks.append(
                NormalizedBlock(
                    id=block_id,
                    type=block_types[item.type],
                    raw_text=item.text,
                    text=text,
                    heading_path=item.heading_path,
                    scalar_candidates=extract_scalar_candidates(text),
                    source_refs=(
                        SourceReference(source_item_id=block_id, locator=locator),
                    ),
                    extraction_method=method,
                )
            )
        for index, note in enumerate(page.notes):
            text = normalize_multiline_text(note)
            if not text:
                continue
            block_id = f"{plan.document_id}:page:{page.page_number}:note:{index}"
            blocks.append(
                NormalizedBlock(
                    id=block_id,
                    type=NormalizedBlockType.OTHER,
                    raw_text=note,
                    text=text,
                    scalar_candidates=extract_scalar_candidates(text),
                    source_refs=(
                        SourceReference(source_item_id=block_id, locator=locator),
                    ),
                    extraction_method=method,
                )
            )
        for index, item in enumerate(page.tables):
            table_id = f"{plan.document_id}:page:{page.page_number}:table:{index}"
            table_ref = SourceReference(source_item_id=table_id, locator=locator)
            rows = tuple(
                NormalizedTableRow(
                    id=f"{table_id}:row:{row_index}",
                    cells=tuple(
                        NormalizedTableCell(
                            raw_text=cell,
                            text=normalize_multiline_text(cell),
                            scalar_candidates=extract_scalar_candidates(cell),
                            source_refs=(table_ref,),
                        )
                        for cell in row.cells
                    ),
                )
                for row_index, row in enumerate(item.rows)
            )
            tables.append(
                NormalizedTable(
                    id=table_id,
                    title=item.title,
                    headers=item.headers,
                    rows=rows,
                    notes=tuple(
                        NormalizedNote(
                            raw_text=note,
                            text=normalize_multiline_text(note),
                            source_refs=(table_ref,),
                        )
                        for note in item.notes
                        if normalize_multiline_text(note)
                    ),
                    source_refs=(table_ref,),
                )
            )
    populated_pages = {
        ref.locator.pdf_page
        for block in blocks
        for ref in block.source_refs
        if ref.locator.pdf_page is not None
    } | {
        ref.locator.pdf_page
        for table in tables
        for ref in table.source_refs
        if ref.locator.pdf_page is not None
    }
    quality = (
        len(populated_pages) / plan.input_probe.page_count
        if plan.input_probe.page_count
        else 0.0
    )
    return NormalizedDocument(
        id=plan.document_id,
        name=document.document_name,
        source_url=document.final_url,
        source_type=SourceType.PDF,
        mime_type=document.mime_type,
        content_sha256=document.sha256,
        extraction_method=method,
        quality_score=quality,
        pdf_input_mode=plan.input_probe.document_mode,
        pdf_admission=plan.admission,
        blocks=tuple(blocks),
        tables=tuple(tables),
    )


def _empty_document(
    document: DocumentArtifact, plan: PdfExtractionPlan, method: str
) -> NormalizedDocument:
    return NormalizedDocument(
        id=plan.document_id,
        name=document.document_name,
        source_url=document.final_url,
        source_type=SourceType.PDF,
        mime_type=document.mime_type,
        content_sha256=document.sha256,
        extraction_method=method,
        quality_score=0,
        pdf_input_mode=plan.input_probe.document_mode,
        pdf_admission=plan.admission,
    )


def _page_mode_summary(plan: PdfExtractionPlan) -> str:
    counts: dict[str, int] = {}
    for page in plan.input_probe.pages:
        counts[page.input_mode.value] = counts.get(page.input_mode.value, 0) + 1
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def _cache_key(
    document_sha256: str,
    schema_version: str,
    prompt_version: str,
    model_name: str,
    content_fingerprint: str,
) -> tuple[str, ...]:
    return (
        document_sha256,
        schema_version,
        prompt_version,
        model_name,
        content_fingerprint,
    )


def _failure_summary(error: Exception) -> str:
    if isinstance(error, APIError):
        message = (error.message or "no provider message").replace("\n", " ")[:500]
        return f"HTTP {error.code} / {error.status or 'UNKNOWN'}: {message}"
    message = str(error).replace("\n", " ")[:500]
    return f"{type(error).__name__}: {message}"
