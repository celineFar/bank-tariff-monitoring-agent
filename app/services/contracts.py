from typing import Any, Protocol

from app.domain.discovery import StoredArtifact
from app.domain.models import ProductType


class TariffPipeline(Protocol):
    async def run(
        self, product: ProductType, trigger: str, query: str | None
    ) -> str: ...


class ArtifactStore(Protocol):
    async def put(
        self,
        *,
        content: bytes,
        sha256: str,
        mime_type: str,
    ) -> StoredArtifact: ...

    async def read(self, storage_key: str) -> bytes: ...

    async def put_extracted(
        self,
        *,
        content: bytes,
        sha256: str,
        source_sha256: str,
        extractor: str,
        extractor_version: str,
        extraction_id: str,
    ) -> StoredArtifact: ...

    async def write_manifest(self, run_id: str, payload: dict[str, Any]) -> str: ...
