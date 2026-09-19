from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

from app.domain.models import ProductType
from app.domain.semantic_extraction import ExtractionBatchResponse


class FileSystemSemanticExtractionRepository:
    """Content-addressed semantic-extraction cache for repeatable local demos."""

    def __init__(self, root: Path) -> None:
        self._root = root

    async def get_exact(
        self,
        *,
        product: ProductType,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        fingerprints: Sequence[str],
    ) -> dict[str, ExtractionBatchResponse]:
        values: dict[str, ExtractionBatchResponse] = {}
        for fingerprint in fingerprints:
            path = self._path(
                product,
                schema_version,
                prompt_version,
                model_name,
                fingerprint,
            )
            if path.is_file():
                values[fingerprint] = ExtractionBatchResponse.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
        return values

    async def save(
        self,
        *,
        product: ProductType,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        values: Sequence[tuple[str, ExtractionBatchResponse]],
    ) -> None:
        for fingerprint, response in values:
            path = self._path(
                product,
                schema_version,
                prompt_version,
                model_name,
                fingerprint,
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
            temporary.write_text(response.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(path)

    def _path(
        self,
        product: ProductType,
        schema_version: str,
        prompt_version: str,
        model_name: str,
        fingerprint: str,
    ) -> Path:
        identity = json.dumps(
            {
                "product": product.value,
                "schema_version": schema_version,
                "prompt_version": prompt_version,
                "model_name": model_name,
                "fingerprint": fingerprint,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(identity.encode()).hexdigest()
        return self._root / digest[:2] / f"{digest}.json"
