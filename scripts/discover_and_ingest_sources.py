"""Discover official product sources and persist validated bytes locally."""

from __future__ import annotations

import argparse
import asyncio
import json

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import load_settings
from app.domain.product_registry import PRODUCT_REGISTRY
from app.repositories.source_ingestion import PostgresSourceIngestionRepository
from app.services.local_artifact_store import LocalArtifactStore
from app.services.official_source_discovery import OfficialSourceDiscovery
from app.services.source_ingestion import SourceIngestionService


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--product-id",
        action="append",
        choices=[product.product_id for product in PRODUCT_REGISTRY],
        help="discover only this product; repeat to select several",
    )
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    parser.add_argument(
        "--artifact-only",
        action="store_true",
        help="skip PostgreSQL metadata (intended only for storage diagnostics)",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> None:
    settings = load_settings()
    selected_ids = set(args.product_id or ())
    products = tuple(
        product
        for product in PRODUCT_REGISTRY
        if not selected_ids or product.product_id in selected_ids
    )
    async with httpx.AsyncClient(follow_redirects=False) as client:
        async with OfficialSourceDiscovery(client, settings.http) as discovery_service:
            discovery = await discovery_service.discover(products)

    store = LocalArtifactStore(settings.application.artifact_storage_dir)
    engine = None
    metadata_repository = None
    if not args.artifact_only:
        engine = create_async_engine(settings.database.url.get_secret_value())
        metadata_repository = PostgresSourceIngestionRepository(
            async_sessionmaker(engine, expire_on_commit=False)
        )
    try:
        result = await SourceIngestionService(
            store,
            metadata_repository=metadata_repository,
        ).ingest(discovery)
    finally:
        if engine is not None:
            await engine.dispose()

    unique_artifacts = {
        source.artifact.sha256: source.artifact for source in result.sources
    }
    payload = {
        "run_id": str(result.run_id),
        "manifest_key": result.manifest_key,
        "artifact_root": str(settings.application.artifact_storage_dir),
        "stored_sources": len(result.sources),
        "metadata_persisted": metadata_repository is not None,
        "new_artifacts": sum(item.created for item in unique_artifacts.values()),
        "reused_artifacts": sum(not item.created for item in unique_artifacts.values()),
        "candidates": len(result.candidates),
        "products": {
            product.product_id: {
                "retrieved_sources": sum(
                    source.product_id == product.product_id for source in result.sources
                ),
                "candidates": len(product.candidates),
                "errors": [issue.reason for issue in product.errors],
            }
            for product in discovery.products
        },
        "warnings": [warning.reason for warning in result.warnings],
    }
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
        )
    )


if __name__ == "__main__":
    asyncio.run(_run(_arguments()))
