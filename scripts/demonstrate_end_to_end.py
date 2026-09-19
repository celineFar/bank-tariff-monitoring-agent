from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from app.config import Settings, load_settings
from app.domain.acquisition import PageArtifact, SourceType
from app.domain.models import ProductType
from app.domain.normalization import NormalizedSourceBundle
from app.domain.semantic_extraction import (
    SemanticExtractionPlan,
    SemanticExtractionResult,
)
from app.domain.source_discovery import SourceDiscoveryPlan, SourceDiscoveryResult
from app.repositories.file_pdf_extraction import FileSystemPdfExtractionRepository
from app.services.acquisition import build_acquisition_service
from app.services.artifact_store import FileSystemArtifactStore
from app.services.discovery_classifier import (
    AdkSourceDiscoveryClassifier,
    is_retryable_api_error,
)
from app.services.model_pricing import enforce_model_price_cap
from app.services.normalization import StructuralNormalizationService
from app.services.pdf_extraction import GeminiPdfExtractionService
from app.services.pipeline_audit import (
    human_filename,
    render_diff_markdown,
    render_document_markdown,
    render_pdf_response_markdown,
    render_semantic_extraction,
    render_source_selection,
)
from app.services.semantic_extraction import (
    AdkSemanticExtractor,
    InMemorySemanticExtractionRepository,
    SemanticExtractionService,
)
from app.services.source_discovery import (
    InMemorySourceDiscoveryRepository,
    SourceDiscoveryService,
)

DEFAULT_OUTPUT_DIRECTORY = Path("end-to-end")


class EndToEndStageError(RuntimeError):
    def __init__(self, stage: str, error: Exception) -> None:
        super().__init__(str(error))
        self.stage = stage
        self.error = error


class ModelSequenceError(RuntimeError):
    def __init__(
        self,
        error: Exception,
        *,
        plan: SourceDiscoveryPlan | SemanticExtractionPlan,
        attempts: list[dict[str, Any]],
    ) -> None:
        super().__init__(str(error))
        self.error = error
        self.plan = plan
        self.attempts = attempts


async def demonstrate(
    source_url: str,
    *,
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY,
    product: ProductType | None = None,
) -> Path:
    output = _prepare_output(output_directory)
    (output / "source_url.txt").write_text(source_url.strip() + "\n", encoding="utf-8")

    acquisition_directory = output / "acquisition"
    source_files = acquisition_directory / "source files"
    documents_directory = acquisition_directory / "documents"
    source_files.mkdir(parents=True)
    documents_directory.mkdir(parents=True)

    settings = load_settings(artifact_temp_dir=source_files / "artifacts")
    print("[1/4] Acquiring webpage and linked documents...", flush=True)
    artifact = await _acquire(source_url, settings)
    _write_acquisition_artifacts(artifact, source_files)
    acquired_page_markdown = artifact.markdown or _fallback_page_markdown(artifact)
    (acquisition_directory / "acquired_content.md").write_text(
        acquired_page_markdown, encoding="utf-8"
    )

    selected_product = product or _infer_product(source_url)
    api_key = (
        settings.models.api_key.get_secret_value()
        if settings.models.api_key is not None
        else None
    )
    if api_key is None:
        raise EndToEndStageError(
            "configuration",
            RuntimeError("GEMINI_API_KEY is required for the full end-to-end run"),
        )

    artifact_store = FileSystemArtifactStore(source_files / "artifacts")
    pdf_repository = FileSystemPdfExtractionRepository(source_files / "pdf_cache")
    pdf_service = GeminiPdfExtractionService(
        settings.pdf_extraction,
        pdf_repository,
        api_key=api_key,
    )

    print("[2/4] Parsing PDFs with Gemini and normalizing all sources...", flush=True)
    normalizer = StructuralNormalizationService(
        artifact_reader=artifact_store,
        pdf_extractor=pdf_service,
    )
    bundle = await normalizer.normalize(artifact)
    normalization_directory = output / "normalization"
    normalization_directory.mkdir()
    _write_json(normalization_directory / "normalized_bundle.json", bundle)
    await _write_document_artifacts(
        artifact,
        bundle,
        artifact_store=artifact_store,
        pdf_service=pdf_service,
        pdf_repository=pdf_repository,
        documents_directory=documents_directory,
        source_files=source_files,
        normalization_directory=normalization_directory,
    )
    _write_normalization_reports(
        artifact,
        bundle,
        acquired_page_markdown=acquired_page_markdown,
        documents_directory=documents_directory,
        normalization_directory=normalization_directory,
    )

    discovery_directory = output / "source-discovery"
    discovery_directory.mkdir()
    print(
        f"[3/4] Discovering sources for product={selected_product.value}...",
        flush=True,
    )
    try:
        discovery_plan, discovery_result, discovery_attempts = await _run_discovery(
            bundle, selected_product, settings, api_key
        )
    except Exception as exc:
        failure = exc.error if isinstance(exc, ModelSequenceError) else exc
        if isinstance(exc, ModelSequenceError):
            _write_json(discovery_directory / "plan.json", exc.plan)
            _write_json(discovery_directory / "model_attempts.json", exc.attempts)
        (discovery_directory / "selection.md").write_text(
            render_source_selection(bundle, None, error=failure), encoding="utf-8"
        )
        _write_json(
            discovery_directory / "failure.json",
            {
                "stage": "source-discovery",
                "type": type(failure).__name__,
                "message": str(failure),
            },
        )
        raise EndToEndStageError("source-discovery", failure) from None
    _write_json(discovery_directory / "plan.json", discovery_plan)
    _write_json(discovery_directory / "result.json", discovery_result)
    _write_json(discovery_directory / "model_attempts.json", discovery_attempts)
    (discovery_directory / "selection.md").write_text(
        render_source_selection(bundle, discovery_result), encoding="utf-8"
    )

    semantic_directory = output / "semantic-extraction"
    semantic_directory.mkdir()
    print("[4/4] Extracting and validating tariff fields...", flush=True)
    semantic_plan: SemanticExtractionPlan | None = None
    try:
        (
            semantic_plan,
            semantic_result,
            semantic_attempts,
        ) = await _run_semantic_extraction(
            bundle,
            discovery_result,
            settings,
            api_key,
            retrieved_at=artifact.retrieved_at,
        )
    except Exception as exc:
        failure = exc.error if isinstance(exc, ModelSequenceError) else exc
        if isinstance(exc, ModelSequenceError):
            semantic_plan = exc.plan
            _write_json(semantic_directory / "model_attempts.json", exc.attempts)
        elif semantic_plan is None:
            semantic_plan = await _build_semantic_plan(
                bundle, discovery_result, settings
            )
        _write_json(semantic_directory / "plan.json", semantic_plan)
        (semantic_directory / "extraction.md").write_text(
            render_semantic_extraction(
                discovery_result, semantic_plan, None, error=failure
            ),
            encoding="utf-8",
        )
        _write_json(
            semantic_directory / "failure.json",
            {
                "stage": "semantic-extraction",
                "type": type(failure).__name__,
                "message": str(failure),
            },
        )
        raise EndToEndStageError("semantic-extraction", failure) from None
    _write_json(semantic_directory / "plan.json", semantic_plan)
    _write_json(semantic_directory / "result.json", semantic_result)
    _write_json(semantic_directory / "loan_product.json", semantic_result.loan_product)
    _write_json(semantic_directory / "model_attempts.json", semantic_attempts)
    (semantic_directory / "extraction.md").write_text(
        render_semantic_extraction(discovery_result, semantic_plan, semantic_result),
        encoding="utf-8",
    )

    _write_json(
        source_files / "run_metadata.json",
        {
            "source_url": source_url,
            "canonical_url": str(artifact.canonical_url),
            "product": selected_product.value,
            "acquisition_content_hash": artifact.content_hash,
            "pdf_model_sequence": list(
                dict.fromkeys(
                    (
                        settings.pdf_extraction.model_name,
                        *settings.pdf_extraction.fallback_model_names,
                    )
                )
            ),
            "source_discovery_model": discovery_result.model_name,
            "semantic_extraction_model": semantic_result.model_name,
        },
    )
    print(f"End-to-end audit trail written to {output.resolve()}", flush=True)
    return output


async def _acquire(url: str, settings: Settings) -> PageArtifact:
    timeout = httpx.Timeout(settings.http.timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        return await build_acquisition_service(client, settings).acquire(url)


async def _write_document_artifacts(
    artifact: PageArtifact,
    bundle: NormalizedSourceBundle,
    *,
    artifact_store: FileSystemArtifactStore,
    pdf_service: GeminiPdfExtractionService,
    pdf_repository: FileSystemPdfExtractionRepository,
    documents_directory: Path,
    source_files: Path,
    normalization_directory: Path,
) -> None:
    normalized_by_id = {document.id: document for document in bundle.documents}
    response_directory = source_files / "pdf_responses"
    response_directory.mkdir(exist_ok=True)
    normalized_documents_directory = normalization_directory / "documents"
    normalized_documents_directory.mkdir(exist_ok=True)

    manifest: list[dict[str, Any]] = []
    for index, document in enumerate(artifact.downloadable_documents):
        content = await artifact_store.read(document.artifact)
        extension = (
            ".pdf"
            if document.mime_type == "application/pdf"
            else _url_extension(str(document.final_url))
        )
        original_name = human_filename(
            document.document_name, index=index, extension=extension
        )
        original_path = documents_directory / original_name
        original_path.write_bytes(content)

        document_id = f"document:{index}:{document.sha256[:12]}"
        normalized = normalized_by_id.get(document_id)
        reconstructed_name = original_path.with_suffix("").name + ".reconstructed.md"
        reconstructed_path = documents_directory / reconstructed_name
        normalized_name = original_path.with_suffix("").name + ".normalized.md"
        normalized_path = normalized_documents_directory / normalized_name
        response = None
        model_name = None
        if normalized is not None and normalized.extraction_method.startswith(
            "gemini_pdf:"
        ):
            model_name = normalized.extraction_method.split(":", 1)[1]
            plan = pdf_service.plan(document, content, document_id=document_id)
            response = await pdf_repository.get_exact(
                document_sha256=document.sha256,
                schema_version=plan.schema_version,
                prompt_version=plan.prompt_version,
                model_name=model_name,
                content_fingerprint=plan.content_fingerprint,
            )
        if response is not None:
            reconstructed = render_pdf_response_markdown(
                document.document_name, str(document.final_url), response
            )
            _write_json(
                response_directory / (original_path.with_suffix("").name + ".json"),
                response,
            )
        else:
            method = normalized.extraction_method if normalized else "unavailable"
            reconstructed = (
                f"# {document.document_name}\n\n"
                f"Source: <{document.final_url}>\n\n"
                f"**No Gemini reconstruction was available.** Method: `{method}`.\n"
            )
        reconstructed_path.write_text(reconstructed, encoding="utf-8")
        if normalized is not None:
            normalized_path.write_text(
                render_document_markdown(normalized), encoding="utf-8"
            )
        manifest.append(
            {
                "document_id": document_id,
                "source_url": str(document.source_url),
                "original_file": original_path.name,
                "reconstructed_markdown": reconstructed_path.name,
                "normalized_markdown": str(
                    normalized_path.relative_to(normalization_directory)
                ),
                "sha256": document.sha256,
                "model": model_name,
            }
        )
    _write_json(source_files / "document_manifest.json", manifest)


def _write_normalization_reports(
    artifact: PageArtifact,
    bundle: NormalizedSourceBundle,
    *,
    acquired_page_markdown: str,
    documents_directory: Path,
    normalization_directory: Path,
) -> None:
    page = next(
        (
            document
            for document in bundle.documents
            if document.source_type is SourceType.PAGE
        ),
        None,
    )
    normalized_page = render_document_markdown(page) if page else ""
    (normalization_directory / "normalized_webpage.md").write_text(
        normalized_page, encoding="utf-8"
    )
    (normalization_directory / "webpage_diff.md").write_text(
        render_diff_markdown(
            "Webpage normalization diff",
            (
                (
                    artifact.title or str(artifact.canonical_url),
                    acquired_page_markdown,
                    normalized_page,
                ),
            ),
        ),
        encoding="utf-8",
    )

    comparisons: list[tuple[str, str, str]] = []
    normalized_documents_directory = normalization_directory / "documents"
    for reconstructed_path in sorted(documents_directory.glob("*.reconstructed.md")):
        normalized_path = (
            normalized_documents_directory
            / reconstructed_path.name.replace(".reconstructed.md", ".normalized.md")
        )
        normalized = (
            normalized_path.read_text(encoding="utf-8")
            if normalized_path.is_file()
            else ""
        )
        comparisons.append(
            (
                reconstructed_path.stem.removesuffix(".reconstructed"),
                reconstructed_path.read_text(encoding="utf-8"),
                normalized,
            )
        )
    (normalization_directory / "documents_diff.md").write_text(
        render_diff_markdown("Document normalization diffs", tuple(comparisons)),
        encoding="utf-8",
    )


async def _run_discovery(
    bundle: NormalizedSourceBundle,
    product: ProductType,
    settings: Settings,
    api_key: str,
) -> tuple[SourceDiscoveryPlan, SourceDiscoveryResult, list[dict[str, Any]]]:
    models = _model_sequence(
        settings.models.generation_model,
        settings.source_discovery.fallback_model_names,
    )
    enforce_model_price_cap(
        models,
        max_price_per_million_tokens_usd=settings.source_discovery.max_price_per_million_tokens_usd,
    )
    attempts: list[dict[str, Any]] = []
    for index, model_name in enumerate(models):
        classifier = AdkSourceDiscoveryClassifier(
            model_name,
            api_key=api_key,
            max_attempts=settings.source_discovery.classifier_max_attempts,
            backoff_base_seconds=settings.source_discovery.classifier_backoff_base_seconds,
            max_backoff_seconds=settings.source_discovery.classifier_max_backoff_seconds,
            retry_jitter_ratio=settings.source_discovery.classifier_retry_jitter_ratio,
        )
        service = SourceDiscoveryService(
            classifier=classifier,
            repository=InMemorySourceDiscoveryRepository(),
            settings=settings.source_discovery,
            model_name=model_name,
        )
        plan = await service.plan(bundle, product)
        print(
            f"  source-discovery model {index + 1}/{len(models)}: {model_name}",
            flush=True,
        )
        try:
            result = await service.discover(bundle, product)
        except Exception as exc:
            attempts.append(_model_attempt(model_name, classifier.usage, exc))
            if is_retryable_api_error(exc) and index + 1 < len(models):
                print(f"  falling back to {models[index + 1]}", flush=True)
                continue
            raise ModelSequenceError(exc, plan=plan, attempts=attempts) from exc
        attempts.append(_model_attempt(model_name, classifier.usage, None))
        return plan, result, attempts
    raise AssertionError("source-discovery model sequence exhausted")


async def _build_semantic_plan(
    bundle: NormalizedSourceBundle,
    discovery: SourceDiscoveryResult,
    settings: Settings,
) -> SemanticExtractionPlan:
    service = SemanticExtractionService(
        extractor=None,
        repository=InMemorySemanticExtractionRepository(),
        settings=settings.semantic_extraction,
        model_name=settings.models.generation_model,
    )
    return await service.plan(bundle, discovery)


async def _run_semantic_extraction(
    bundle: NormalizedSourceBundle,
    discovery: SourceDiscoveryResult,
    settings: Settings,
    api_key: str,
    *,
    retrieved_at,
) -> tuple[SemanticExtractionPlan, SemanticExtractionResult, list[dict[str, Any]]]:
    models = _model_sequence(
        settings.models.generation_model,
        settings.source_discovery.fallback_model_names,
    )
    enforce_model_price_cap(
        models,
        max_price_per_million_tokens_usd=settings.source_discovery.max_price_per_million_tokens_usd,
    )
    attempts: list[dict[str, Any]] = []
    for index, model_name in enumerate(models):
        extractor = AdkSemanticExtractor(
            model_name,
            api_key=api_key,
            max_attempts=settings.source_discovery.classifier_max_attempts,
            backoff_base_seconds=settings.source_discovery.classifier_backoff_base_seconds,
            max_backoff_seconds=settings.source_discovery.classifier_max_backoff_seconds,
            retry_jitter_ratio=settings.source_discovery.classifier_retry_jitter_ratio,
        )
        service = SemanticExtractionService(
            extractor=extractor,
            repository=InMemorySemanticExtractionRepository(),
            settings=settings.semantic_extraction,
            model_name=model_name,
        )
        plan = await service.plan(bundle, discovery)
        print(f"  semantic model {index + 1}/{len(models)}: {model_name}", flush=True)
        try:
            result = await service.extract(bundle, discovery, retrieved_at=retrieved_at)
        except Exception as exc:
            attempts.append(_model_attempt(model_name, extractor.usage, exc))
            if is_retryable_api_error(exc) and index + 1 < len(models):
                print(f"  falling back to {models[index + 1]}", flush=True)
                continue
            raise ModelSequenceError(exc, plan=plan, attempts=attempts) from exc
        attempts.append(_model_attempt(model_name, extractor.usage, None))
        return plan, result, attempts
    raise AssertionError("semantic-extraction model sequence exhausted")


def _write_acquisition_artifacts(artifact: PageArtifact, directory: Path) -> None:
    _write_json(directory / "page_artifact.json", artifact)
    for name, values in (
        ("blocks.json", artifact.blocks),
        ("tables.json", artifact.tables),
        ("links.json", artifact.links),
        ("documents.json", artifact.downloadable_documents),
        ("images.json", artifact.images),
        ("interactive_controls.json", artifact.interactive_controls),
        ("network_payloads.json", artifact.network_payloads),
    ):
        _write_json(directory / name, values)
    if artifact.raw_html is not None:
        (directory / "raw.html").write_text(artifact.raw_html, encoding="utf-8")
    if artifact.rendered_html is not None:
        (directory / "rendered.html").write_text(
            artifact.rendered_html, encoding="utf-8"
        )


def _model_attempt(model_name: str, usage, error: Exception | None) -> dict[str, Any]:
    return {
        "model": model_name,
        "status": "failed" if error else "succeeded",
        "request_attempts": usage.request_attempts,
        "application_retries": usage.application_retries,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "thinking_tokens": usage.thinking_tokens,
        "total_tokens": usage.total_tokens,
        "error_type": type(error).__name__ if error else None,
        "message": str(error) if error else None,
    }


def _fallback_page_markdown(artifact: PageArtifact) -> str:
    title = artifact.title or str(artifact.canonical_url)
    return (
        "\n\n".join(
            (f"# {title}", *(block.markdown or block.text for block in artifact.blocks))
        )
        + "\n"
    )


def _infer_product(url: str) -> ProductType:
    return (
        ProductType.MORTGAGE
        if "mortgage" in url.casefold()
        else ProductType.CONSUMER_LOAN
    )


def _model_sequence(primary: str, fallbacks: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((primary, *fallbacks)))


def _url_extension(url: str) -> str:
    suffix = Path(url.split("?", 1)[0]).suffix
    return suffix if suffix and len(suffix) <= 10 else ".bin"


def _prepare_output(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.exists() and any(resolved.iterdir()):
        raise FileExistsError(
            f"Output directory is not empty: {resolved}. Pass a new --output-directory."
        )
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _write_json(path: Path, value: Any) -> None:
    if isinstance(value, BaseModel):
        serialized = value.model_dump(mode="json")
    elif isinstance(value, tuple):
        serialized = [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item
            for item in value
        ]
    else:
        serialized = value
    path.write_text(
        json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the complete tariff pipeline and write a human-readable audit trail."
    )
    parser.add_argument("source_url", help="Official HTTPS loan or mortgage page URL")
    parser.add_argument(
        "--product",
        choices=[item.value for item in ProductType],
        help="Override product inference (mortgage when URL contains 'mortgage'; otherwise consumer_loan)",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="New or empty output directory (default: end-to-end)",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    try:
        asyncio.run(
            demonstrate(
                args.source_url,
                output_directory=args.output_directory,
                product=ProductType(args.product) if args.product else None,
            )
        )
    except EndToEndStageError as exc:
        print(
            f"End-to-end demonstration stopped at {exc.stage}: "
            f"{type(exc.error).__name__}: {exc.error}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(
            f"End-to-end demonstration failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
