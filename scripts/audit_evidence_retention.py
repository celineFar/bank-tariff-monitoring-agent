"""Check whether legacy chunk embeddings can be deprecated safely.

Read-only and model-free. Reports every active accepted fact whose citation
would stop being verifiable once the old summary/source embeddings are removed.

Usage: uv run python scripts/audit_evidence_retention.py
"""

from __future__ import annotations

import asyncio
import json

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.services.evidence_retention_audit import EvidenceRetentionAuditor


async def _audit() -> dict[str, object]:
    engine = create_async_engine(get_settings().database.url.get_secret_value())
    try:
        report = await EvidenceRetentionAuditor(async_sessionmaker(engine)).audit()
        return report.as_dict()
    finally:
        await engine.dispose()


def main() -> None:
    print(json.dumps(asyncio.run(_audit()), default=str, indent=2))


if __name__ == "__main__":
    main()
