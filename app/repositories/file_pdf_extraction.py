from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from app.domain.pdf_extraction import PdfExtractionResponse


class FileSystemPdfExtractionRepository:
    """Content-addressed local cache used by repeatable demonstration runs."""

    def __init__(self, root: Path) -> None:
        self._root = root

    async def get_exact(
        self,
        *,
        document_sha256: str,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprint: str,
    ) -> PdfExtractionResponse | None:
        path = self._path(
            document_sha256,
            schema_version,
            prompt_version,
            model_name,
            content_fingerprint,
        )
        if not path.is_file():
            return None
        return PdfExtractionResponse.model_validate_json(
            path.read_text(encoding="utf-8")
        )

    async def save(
        self,
        *,
        document_sha256: str,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprint: str,
        response: PdfExtractionResponse,
    ) -> None:
        path = self._path(
            document_sha256,
            schema_version,
            prompt_version,
            model_name,
            content_fingerprint,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        temporary.write_text(response.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)

    def _path(
        self,
        document_sha256: str,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprint: str,
    ) -> Path:
        identity = json.dumps(
            {
                "document_sha256": document_sha256,
                "schema_version": schema_version,
                "prompt_version": prompt_version,
                "model_name": model_name,
                "content_fingerprint": content_fingerprint,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(identity.encode()).hexdigest()
        return self._root / digest[:2] / f"{digest}.json"
