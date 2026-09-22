from __future__ import annotations

import hashlib
import logging

from google.genai.errors import APIError
from pydantic import BaseModel, ConfigDict

from app.config import PdfExtractionSettings
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
    PdfAdmissionRelevance,
    PdfExtractedBlockType,
    PdfExtractionPlan,
    PdfExtractionResponse,
    PdfModelUsage,
)
from app.repositories.contracts import PdfExtractionRepository
from app.services.gemini_pdf_extractor import AdkGeminiPdfExtractor
from app.services.model_call_usage import (
    PostgresModelCallUsageRepository,
    record_model_cache_hit,
)
from app.services.model_pricing import enforce_model_price_cap
from app.services.pdf_admission import assess_pdf_metadata
from app.services.pdf_input_probe import probe_pdf_input
from app.services.scalar_normalizer import extract_scalar_candidates

logger = logging.getLogger(__name__)


class PdfExtractionOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan: PdfExtractionPlan
    normalized_document: NormalizedDocument
    model_name: str | None = None
    usage: PdfModelUsage = PdfModelUsage()
    reused: bool = False


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
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._api_key = api_key
        self._usage_repository = usage_repository
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
        if plan.admission.relevance is PdfAdmissionRelevance.IRRELEVANT:
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
                return PdfExtractionOutcome(
                    plan=plan,
                    normalized_document=_normalize(document, plan, cached, model_name),
                    model_name=model_name,
                    reused=True,
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
            return PdfExtractionOutcome(
                plan=plan,
                normalized_document=_normalize(document, plan, response, model_name),
                model_name=model_name,
                usage=extractor.usage,
            )
        raise AssertionError(f"PDF model sequence exhausted: {failures}")


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
