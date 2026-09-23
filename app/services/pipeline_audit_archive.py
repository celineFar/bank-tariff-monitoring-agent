"""Collect the rendered pipeline audit Markdown of every run in one directory.

The renderers in :mod:`app.services.pipeline_audit` produce the colour-coded
Markdown overlays that show what each stage did to the source content. This
module is the deterministic sink that writes them for ordinary pipeline runs,
so the same reports the demonstration scripts emit are also available for API
and worker runs. Filenames are prefixed with the pipeline stage number:

``2_`` normalization, ``3_`` source discovery, ``4_`` semantic extraction.
Acquisition (stage 1) has no rendered overlay of its own; its content is the
baseline of the stage 2 normalization diff.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.domain.acquisition import PageArtifact, SourceType
from app.domain.models import OfferingId, ProductType
from app.domain.normalization import NormalizedSourceBundle
from app.domain.semantic_extraction import (
    SemanticExtractionPlan,
    SemanticExtractionResult,
)
from app.domain.source_discovery import SourceDiscoveryResult
from app.services.normalized_renderer import render_normalized_markdown
from app.services.pipeline_audit import (
    render_diff_markdown,
    render_document_markdown,
    render_pre_validation,
    render_review_queue,
    render_semantic_extraction,
    render_source_selection,
    render_source_selection_diff,
)
from app.services.source_selection import build_selected_source_bundle

logger = logging.getLogger(__name__)

DEFAULT_AUDIT_DIRECTORY = Path("artifacts/pipeline-audit")


@dataclass(frozen=True)
class AuditContext:
    """Identifies the run and offering a set of audit reports belongs to."""

    run_id: UUID
    offering_execution_id: UUID
    product: ProductType
    offering_id: OfferingId
    seed_url: str


class PipelineAuditArchive(Protocol):
    async def record_normalization(
        self,
        context: AuditContext,
        artifact: PageArtifact,
        bundle: NormalizedSourceBundle,
    ) -> None: ...

    async def record_source_discovery(
        self,
        context: AuditContext,
        bundle: NormalizedSourceBundle,
        result: SourceDiscoveryResult | None,
        *,
        error: Exception | None = None,
    ) -> None: ...

    async def record_semantic_extraction(
        self,
        context: AuditContext,
        bundle: NormalizedSourceBundle,
        discovery: SourceDiscoveryResult,
        plan: SemanticExtractionPlan,
        result: SemanticExtractionResult | None,
        *,
        error: Exception | None = None,
    ) -> None: ...


class FileSystemPipelineAuditArchive:
    """Write stage-numbered audit Markdown under ``root/<run>/<offering>``."""

    def __init__(self, root: Path = DEFAULT_AUDIT_DIRECTORY) -> None:
        self._root = Path(root)

    def directory(self, context: AuditContext) -> Path:
        return self._root / f"run_{context.run_id}" / context.offering_id.value

    async def record_normalization(
        self,
        context: AuditContext,
        artifact: PageArtifact,
        bundle: NormalizedSourceBundle,
    ) -> None:
        await self._write(context, _normalization_reports, artifact, bundle)

    async def record_source_discovery(
        self,
        context: AuditContext,
        bundle: NormalizedSourceBundle,
        result: SourceDiscoveryResult | None,
        *,
        error: Exception | None = None,
    ) -> None:
        await self._write(
            context, _source_discovery_reports, bundle, result, error=error
        )

    async def record_semantic_extraction(
        self,
        context: AuditContext,
        bundle: NormalizedSourceBundle,
        discovery: SourceDiscoveryResult,
        plan: SemanticExtractionPlan,
        result: SemanticExtractionResult | None,
        *,
        error: Exception | None = None,
    ) -> None:
        await self._write(
            context,
            _semantic_extraction_reports,
            bundle,
            discovery,
            plan,
            result,
            error=error,
        )

    async def _write(self, context: AuditContext, build, *args, **kwargs) -> None:
        """Render off the event loop and never fail the pipeline stage."""
        await asyncio.to_thread(self._write_reports, context, build, *args, **kwargs)

    def _write_reports(self, context: AuditContext, build, *args, **kwargs) -> None:
        directory = self.directory(context)
        try:
            directory.mkdir(parents=True, exist_ok=True)
            _write_context(directory, context)
        except Exception:
            _log_failure(context, "0_run_context.md")
            return
        for name, render in build(*args, **kwargs):
            try:
                (directory / name).write_text(render(), encoding="utf-8")
            except Exception:
                _log_failure(context, name)


def _log_failure(context: AuditContext, name: str) -> None:
    """One unwritable report must not cost the run or the other reports."""
    logger.warning(
        "Failed to write pipeline audit report %s for run %s offering %s",
        name,
        context.run_id,
        context.offering_id.value,
        exc_info=True,
    )


def _write_context(directory: Path, context: AuditContext) -> None:
    (directory / "0_run_context.md").write_text(
        "\n".join(
            (
                "# Pipeline audit trail",
                "",
                f"- Run: `{context.run_id}`",
                f"- Offering execution: `{context.offering_execution_id}`",
                f"- Product: `{context.product.value}`",
                f"- Offering: `{context.offering_id.value}`",
                f"- Seed URL: <{context.seed_url}>",
                "",
                "Files are prefixed with the pipeline stage that produced them: "
                "`2_` normalization, `3_` source discovery, `4_` semantic extraction. "
                "Acquisition (stage 1) has no rendered overlay; the acquired content "
                "is the baseline of the stage 2 normalization diff.",
                "",
            )
        ),
        encoding="utf-8",
    )


def _normalization_reports(
    artifact: PageArtifact,
    bundle: NormalizedSourceBundle,
) -> tuple[tuple[str, Callable[[], str]], ...]:
    page = next(
        (
            document
            for document in bundle.documents
            if document.source_type is SourceType.PAGE
        ),
        None,
    )

    def normalized_page() -> str:
        return render_document_markdown(page) if page is not None else ""

    def diff() -> str:
        return render_diff_markdown(
            "Webpage normalization diff",
            (
                (
                    artifact.title or str(bundle.canonical_url),
                    artifact.markdown or "",
                    normalized_page(),
                ),
            ),
        )

    return (
        ("2_normalized_webpage.md", normalized_page),
        ("2_normalization_diff.md", diff),
    )


def _source_discovery_reports(
    bundle: NormalizedSourceBundle,
    result: SourceDiscoveryResult | None,
    *,
    error: Exception | None = None,
) -> tuple[tuple[str, Callable[[], str]], ...]:
    reports: list[tuple[str, Callable[[], str]]] = [
        (
            "3_source_selection_decisions.md",
            lambda: render_source_selection(bundle, result, error=error),
        ),
        (
            "3_source_selection_diff.md",
            lambda: render_source_selection_diff(bundle, result, error=error),
        ),
    ]
    if result is not None:
        reports.append(
            (
                "3_selected_sources.md",
                lambda: render_normalized_markdown(
                    build_selected_source_bundle(bundle, result)
                ),
            )
        )
    return tuple(reports)


def _semantic_extraction_reports(
    bundle: NormalizedSourceBundle,
    discovery: SourceDiscoveryResult,
    plan: SemanticExtractionPlan,
    result: SemanticExtractionResult | None,
    *,
    error: Exception | None = None,
) -> tuple[tuple[str, Callable[[], str]], ...]:
    reports: list[tuple[str, Callable[[], str]]] = [
        (
            "4_extraction_evidence.md",
            lambda: render_semantic_extraction(
                build_selected_source_bundle(bundle, discovery),
                discovery,
                plan,
                result,
                error=error,
            ),
        )
    ]
    if result is not None:
        reports.append(("4_pre_validation.md", lambda: render_pre_validation(result)))
        reports.append(
            ("4_review_queue.md", lambda: render_review_queue(result.review_items))
        )
    return tuple(reports)
