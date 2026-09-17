"""Run the deterministic Phase-1 product crawler and print metadata as JSON."""

from __future__ import annotations

import argparse
import asyncio
import json

import httpx

from app.config import load_settings
from app.domain.product_registry import PRODUCT_REGISTRY
from app.services.product_crawler import ProductCrawler


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--product-id",
        action="append",
        choices=[product.product_id for product in PRODUCT_REGISTRY],
        help="crawl only this product; repeat to select several",
    )
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print statuses and source counts instead of complete metadata",
    )
    parser.add_argument(
        "--document-urls",
        action="store_true",
        help="include discovered document URLs in summary output",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> None:
    settings = load_settings().http
    selected_ids = set(args.product_id or ())
    products = tuple(
        product
        for product in PRODUCT_REGISTRY
        if not selected_ids or product.product_id in selected_ids
    )
    async with httpx.AsyncClient(follow_redirects=False) as client:
        async with ProductCrawler(client, settings) as crawler:
            result = await crawler.crawl_all(products)

    if args.summary:
        products_payload = [
            {
                "product_id": item.product_id,
                "status": item.status.value,
                "has_english_page": item.product_page_en is not None,
                "has_armenian_page": item.product_page_hy is not None,
                "supporting_pages": len(item.supporting_pages),
                "documents": len(item.documents),
                "calculators": len(item.calculators),
                "external_references": len(item.external_references),
                "warnings": [warning.reason for warning in item.warnings],
                "errors": [error.reason for error in item.errors],
                **(
                    {
                        "document_urls": [
                            url for document in item.documents for url in document.urls
                        ]
                    }
                    if args.document_urls
                    else {}
                ),
            }
            for item in result.inventories
        ]
        payload = {
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat(),
            "products": products_payload,
        }
    else:
        payload = result.model_dump(
            mode="json",
            exclude={
                "inventories": {
                    "__all__": {
                        "product_page_en": {"content"},
                        "product_page_hy": {"content"},
                        "supporting_pages": {"__all__": {"content"}},
                        "documents": {"__all__": {"content"}},
                    }
                }
            },
        )
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
        )
    )


if __name__ == "__main__":
    asyncio.run(_run(_arguments()))
