from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.domain.discovery import StoredArtifact

_EXTENSIONS = {
    "application/pdf": ".pdf",
    "text/html": ".html",
    "application/msword": ".doc",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


class ArtifactIntegrityError(RuntimeError):
    pass


class LocalArtifactStore:
    """Immutable content-addressed storage rooted in one configured directory."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    async def put(
        self,
        *,
        content: bytes,
        sha256: str,
        mime_type: str,
    ) -> StoredArtifact:
        return await asyncio.to_thread(
            self._put_sync,
            content=content,
            sha256=sha256,
            mime_type=mime_type,
        )

    async def read(self, storage_key: str) -> bytes:
        return await asyncio.to_thread(self._safe_path(storage_key).read_bytes)

    async def write_manifest(self, run_id: str, payload: dict[str, Any]) -> str:
        storage_key = f"manifests/{run_id}.json"
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")
        await asyncio.to_thread(
            self._write_manifest_sync,
            self._safe_path(storage_key),
            encoded,
        )
        return storage_key

    async def read_manifest(self, storage_key: str) -> dict[str, Any]:
        content = await self.read(storage_key)
        loaded = json.loads(content)
        if not isinstance(loaded, dict):
            raise ArtifactIntegrityError(
                "ingestion manifest must contain a JSON object"
            )
        return loaded

    def _put_sync(
        self,
        *,
        content: bytes,
        sha256: str,
        mime_type: str,
    ) -> StoredArtifact:
        actual_sha256 = hashlib.sha256(content).hexdigest()
        normalized_sha256 = sha256.casefold()
        if actual_sha256 != normalized_sha256:
            raise ArtifactIntegrityError(
                "artifact bytes did not match the supplied SHA-256"
            )
        extension = _EXTENSIONS.get(mime_type.casefold(), ".bin")
        storage_key = f"raw/{normalized_sha256[:2]}/{normalized_sha256}{extension}"
        path = self._safe_path(storage_key)
        created = not path.exists()
        if created:
            self._atomic_write(path, content, replace=False)
        else:
            existing = path.read_bytes()
            if hashlib.sha256(existing).hexdigest() != normalized_sha256:
                raise ArtifactIntegrityError(
                    "existing artifact did not match its content-addressed key"
                )
        return StoredArtifact(
            storage_key=storage_key,
            sha256=normalized_sha256,
            mime_type=mime_type.casefold(),
            size_bytes=len(content),
            created=created,
        )

    def _safe_path(self, storage_key: str) -> Path:
        if not storage_key or Path(storage_key).is_absolute():
            raise ValueError("artifact storage key must be relative")
        path = (self._root / storage_key).resolve()
        if path != self._root and self._root not in path.parents:
            raise ValueError("artifact storage key escaped the configured root")
        return path

    def _write_manifest_sync(self, path: Path, content: bytes) -> None:
        if path.exists():
            if path.read_bytes() != content:
                raise ArtifactIntegrityError(
                    "an ingestion manifest with this run ID already exists"
                )
            return
        self._atomic_write(path, content, replace=False)

    @staticmethod
    def _atomic_write(path: Path, content: bytes, *, replace: bool = True) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if not replace and path.exists():
                return
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
