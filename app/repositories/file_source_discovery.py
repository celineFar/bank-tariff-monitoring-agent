from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

from app.domain.models import ProductType
from app.domain.source_discovery import SourceAssessment


class FileSystemSourceDiscoveryRepository:
    """Content-addressed source-discovery cache for repeatable local demos."""

    def __init__(self, root: Path) -> None:
        self._root = root

    async def get_exact(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprints: Sequence[str],
    ) -> dict[str, SourceAssessment]:
        return self._read_many(
            "exact",
            product,
            policy_version,
            prompt_version,
            model_name,
            content_fingerprints,
        )

    async def get_structural_priors(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        structural_fingerprints: Sequence[str],
    ) -> dict[str, SourceAssessment]:
        return self._read_many(
            "structural",
            product,
            policy_version,
            prompt_version,
            model_name,
            structural_fingerprints,
        )

    async def save(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        assessments: Sequence[SourceAssessment],
    ) -> None:
        for assessment in assessments:
            for namespace, fingerprint in (
                ("exact", assessment.input_fingerprint),
                ("structural", assessment.structural_fingerprint),
            ):
                path = self._path(
                    namespace,
                    product,
                    policy_version,
                    prompt_version,
                    model_name,
                    fingerprint,
                )
                _atomic_write(path, assessment.model_dump_json(indent=2))

    def _read_many(
        self,
        namespace: str,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        fingerprints: Sequence[str],
    ) -> dict[str, SourceAssessment]:
        values: dict[str, SourceAssessment] = {}
        for fingerprint in fingerprints:
            path = self._path(
                namespace,
                product,
                policy_version,
                prompt_version,
                model_name,
                fingerprint,
            )
            if path.is_file():
                values[fingerprint] = SourceAssessment.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
        return values

    def _path(
        self,
        namespace: str,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        fingerprint: str,
    ) -> Path:
        identity = json.dumps(
            {
                "product": product.value,
                "policy_version": policy_version,
                "prompt_version": prompt_version,
                "model_name": model_name,
                "fingerprint": fingerprint,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(identity.encode()).hexdigest()
        return self._root / namespace / digest[:2] / f"{digest}.json"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
