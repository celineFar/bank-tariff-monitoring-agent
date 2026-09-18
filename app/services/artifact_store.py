from __future__ import annotations

import asyncio
import hashlib
import os
import threading
from pathlib import Path
from uuid import uuid4

from app.domain.acquisition import StoredArtifact


class ArtifactStoreError(RuntimeError):
    pass


class FileSystemArtifactStore:
    """Content-addressed storage whose paths never derive from source URLs."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._write_lock = threading.Lock()

    async def save(
        self,
        content: bytes,
        *,
        role: str,
        media_type: str,
        extension: str,
    ) -> StoredArtifact:
        return await asyncio.to_thread(
            self._save_sync,
            content,
            role=role,
            media_type=media_type,
            extension=extension,
        )

    def _save_sync(
        self,
        content: bytes,
        *,
        role: str,
        media_type: str,
        extension: str,
    ) -> StoredArtifact:
        checksum = hashlib.sha256(content).hexdigest()
        safe_extension = extension.lower().lstrip(".")
        if not safe_extension.isalnum() or len(safe_extension) > 10:
            raise ArtifactStoreError("artifact extension is invalid")

        root = self._root.resolve()
        directory = (root / checksum[:2]).resolve()
        if root != directory and root not in directory.parents:
            raise ArtifactStoreError("artifact path escaped the configured root")
        directory.mkdir(parents=True, exist_ok=True)

        relative_path = Path(checksum[:2]) / f"{checksum}.{safe_extension}"
        target = (root / relative_path).resolve()
        if root not in target.parents:
            raise ArtifactStoreError("artifact path escaped the configured root")

        with self._write_lock:
            if not target.exists():
                temporary = directory / f".{checksum}.{uuid4().hex}.tmp"
                try:
                    temporary.write_bytes(content)
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)

        return StoredArtifact(
            role=role,
            sha256=checksum,
            size_bytes=len(content),
            media_type=media_type,
            relative_path=relative_path.as_posix(),
        )
