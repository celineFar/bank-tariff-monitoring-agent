from __future__ import annotations

import asyncio

from app.app_utils.services import ensure_session_service_ready


async def main() -> None:
    await ensure_session_service_ready()
    print("ADK session schema is ready (version 1, compatible with ADK 2.9.2).")


if __name__ == "__main__":
    asyncio.run(main())
