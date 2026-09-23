"""Read-only canonical-versus-projection audit for accepted snapshots.

Usage: uv run python scripts/audit_structured_projection.py
No raw source text or model calls are used.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.services.structured_projection_audit import StructuredProjectionAuditor


async def _audit() -> dict[str, object]:
    engine = create_async_engine(get_settings().database.url.get_secret_value())
    try:
        sessions = async_sessionmaker(engine)
        async with sessions() as session:
            ids = (
                (
                    await session.execute(
                        text(
                            "SELECT id FROM tariff_snapshots WHERE status = 'accepted' "
                            "ORDER BY accepted_at, id"
                        )
                    )
                )
                .scalars()
                .all()
            )
        auditor = StructuredProjectionAuditor(sessions)
        results = [
            asdict(await auditor.audit_snapshot(snapshot_id)) for snapshot_id in ids
        ]
        return {"accepted_snapshots": len(ids), "results": results}
    finally:
        await engine.dispose()


def main() -> None:
    print(json.dumps(asyncio.run(_audit()), default=str, indent=2))


if __name__ == "__main__":
    main()
