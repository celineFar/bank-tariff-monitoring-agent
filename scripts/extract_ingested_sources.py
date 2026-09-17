"""Extract persisted HTML and PDF sources into structured JSON artifacts."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import load_settings
from app.domain.discovery import IngestedSource, StoredArtifact
from app.domain.extraction import ExtractedDocument, PersistedExtraction
from app.domain.product_registry import PRODUCT_REGISTRY
from app.repositories.content_extraction import PostgresContentExtractionRepository
from app.repositories.source_ingestion import PostgresSourceIngestionRepository
from app.services.content_extractor import (
    ContentExtractionError,
    DocumentContentExtractor,
)
from app.services.local_artifact_store import ArtifactIntegrityError, LocalArtifactStore

_SUPPORTED_MIME_TYPES = frozenset(
    ("text/html", "application/xhtml+xml", "application/pdf")
)


class _ArtifactOnlyExtractionRepository:
    async def save_extraction(self, extraction: ExtractedDocument) -> None:
        del extraction

    async def get_extraction(self, extraction_id: UUID) -> PersistedExtraction | None:
        del extraction_id
        return None


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    manifest_group = parser.add_mutually_exclusive_group()
    manifest_group.add_argument(
        "--manifest",
        help="artifact key such as manifests/<run-id>.json",
    )
    manifest_group.add_argument(
        "--latest-manifest",
        action="store_true",
        help="use the most recently modified local ingestion manifest",
    )
    parser.add_argument(
        "--product-id",
        action="append",
        choices=[product.product_id for product in PRODUCT_REGISTRY],
        help=(
            "filter manifest sources, or load this product from PostgreSQL when no "
            "manifest is selected; repeat to select several"
        ),
    )
    parser.add_argument(
        "--artifact-only",
        action="store_true",
        help="write extracted JSON without recording extraction metadata in PostgreSQL",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="stop after the first failed extraction",
    )
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    settings = load_settings()
    store = LocalArtifactStore(settings.application.artifact_storage_dir)
    product_ids = tuple(args.product_id or ())
    engine = None

    manifest_key = args.manifest
    if args.latest_manifest:
        manifest_key = _latest_manifest_key(settings.application.artifact_storage_dir)

    try:
        if manifest_key is not None:
            sources = await _manifest_sources(store, manifest_key, product_ids)
        else:
            selected_products = product_ids or tuple(
                product.product_id for product in PRODUCT_REGISTRY
            )
            engine = create_async_engine(settings.database.url.get_secret_value())
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            sources = await _database_sources(
                PostgresSourceIngestionRepository(session_factory),
                selected_products,
            )

        if engine is None and not args.artifact_only:
            engine = create_async_engine(settings.database.url.get_secret_value())
        if args.artifact_only:
            extraction_repository = _ArtifactOnlyExtractionRepository()
        else:
            assert engine is not None
            extraction_repository = PostgresContentExtractionRepository(
                async_sessionmaker(engine, expire_on_commit=False)
            )

        extractor = DocumentContentExtractor(
            store,
            extraction_repository,
            min_text_characters_per_page=(settings.ocr.min_text_chars_per_page),
        )
        extracted: list[dict[str, Any]] = []
        failed: list[dict[str, str]] = []
        skipped: list[dict[str, str]] = []
        for source in sources:
            mime_type = source.artifact.mime_type.partition(";")[0].strip().casefold()
            if mime_type not in _SUPPORTED_MIME_TYPES:
                skipped.append(
                    {
                        "product_id": source.product_id,
                        "source_url": source.source_url,
                        "mime_type": mime_type,
                        "reason": "unsupported_mime_type",
                    }
                )
                continue
            try:
                document = await extractor.extract(source)
            except (
                ArtifactIntegrityError,
                ContentExtractionError,
                OSError,
                ValueError,
            ) as exc:
                failed.append(
                    {
                        "product_id": source.product_id,
                        "source_url": source.source_url,
                        "error": str(exc),
                    }
                )
                if args.fail_fast:
                    break
                continue
            extracted.append(
                {
                    "extraction_id": str(document.extraction_id),
                    "product_id": document.product_id,
                    "source_url": document.source_url,
                    "blocks": document.statistics.block_count,
                    "pages": document.statistics.page_count,
                    "tables": document.statistics.table_count,
                    "text_characters": document.statistics.text_character_count,
                    "status": document.status.value,
                    "needs_ocr": document.status.value == "needs_ocr",
                    "pages_requiring_ocr": list(document.ocr.pages_requiring_ocr),
                    "warnings": document.statistics.warning_count,
                    "json_key": document.representation_artifact.storage_key,
                    "json_path": str(
                        (
                            settings.application.artifact_storage_dir
                            / document.representation_artifact.storage_key
                        ).resolve()
                    ),
                    "created": document.representation_artifact.created,
                }
            )

        payload = {
            "manifest_key": manifest_key,
            "artifact_root": str(settings.application.artifact_storage_dir.resolve()),
            "metadata_persisted": not args.artifact_only,
            "source_count": len(sources),
            "extracted_count": len(extracted),
            "skipped_count": len(skipped),
            "failed_count": len(failed),
            "extracted": extracted,
            "skipped": skipped,
            "failed": failed,
        }
        print(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            )
        )
        return 1 if failed else 0
    finally:
        if engine is not None:
            await engine.dispose()


async def _manifest_sources(
    store: LocalArtifactStore,
    manifest_key: str,
    product_ids: tuple[str, ...],
) -> tuple[IngestedSource, ...]:
    payload = await store.read_manifest(manifest_key)
    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("ingestion manifest must contain a sources array")
    fallback_retrieved_at = payload.get("completed_at") or payload.get("started_at")
    sources = []
    for raw_source in raw_sources:
        if not isinstance(raw_source, dict):
            raise ValueError("ingestion manifest source entries must be objects")
        source_payload = dict(raw_source)
        if "retrieved_at" not in source_payload:
            if fallback_retrieved_at is None:
                raise ValueError(
                    "legacy ingestion manifest has no source retrieval timestamp"
                )
            source_payload["retrieved_at"] = fallback_retrieved_at
        sources.append(IngestedSource.model_validate(source_payload))
    selected = set(product_ids)
    return _deduplicate_sources(
        source for source in sources if not selected or source.product_id in selected
    )


async def _database_sources(
    repository: PostgresSourceIngestionRepository,
    product_ids: tuple[str, ...],
) -> tuple[IngestedSource, ...]:
    sources: list[IngestedSource] = []
    for product_id in product_ids:
        origins = await repository.list_product_sources(product_id)
        sources.extend(
            IngestedSource(
                product_id=origin.product_id,
                candidate_type=origin.candidate_type,
                source_url=origin.source_url,
                final_url=origin.final_url,
                language=origin.language,
                referrer_urls=origin.referrer_urls,
                retrieved_at=origin.retrieved_at,
                artifact=StoredArtifact(
                    storage_key=origin.artifact.storage_key,
                    sha256=origin.artifact.sha256,
                    mime_type=origin.artifact.mime_type,
                    size_bytes=origin.artifact.size_bytes,
                    created=False,
                ),
            )
            for origin in origins
        )
    return _deduplicate_sources(sources)


def _deduplicate_sources(
    sources: Iterable[IngestedSource],
) -> tuple[IngestedSource, ...]:
    unique: dict[tuple[str, str, str, str], IngestedSource] = {}
    for source in sources:
        identity = (
            source.product_id,
            source.source_url,
            source.final_url,
            source.artifact.sha256,
        )
        current = unique.get(identity)
        if current is None or source.retrieved_at > current.retrieved_at:
            unique[identity] = source
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                item.product_id,
                item.source_url,
                item.final_url,
                item.artifact.sha256,
            ),
        )
    )


def _latest_manifest_key(artifact_root: Path) -> str:
    manifest_root = artifact_root.resolve() / "manifests"
    manifests = tuple(manifest_root.glob("*.json"))
    if not manifests:
        raise FileNotFoundError(
            f"no ingestion manifests were found under {manifest_root}"
        )
    latest = max(manifests, key=lambda path: (path.stat().st_mtime_ns, path.name))
    return latest.relative_to(artifact_root.resolve()).as_posix()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run(_arguments())))
