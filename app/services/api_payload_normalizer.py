from __future__ import annotations

import json
from collections.abc import Iterator

from app.domain.acquisition import NetworkPayload, SourceLocator, SourceType
from app.domain.normalization import (
    NormalizationWarning,
    NormalizationWarningCode,
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    SourceReference,
    normalize_multiline_text,
)
from app.services.scalar_normalizer import extract_scalar_candidates


def normalize_network_payload(
    payload: NetworkPayload, *, index: int
) -> tuple[NormalizedDocument, tuple[NormalizationWarning, ...]]:
    document_id = f"api:{index}:{payload.sha256[:12]}"
    warnings: list[NormalizationWarning] = []
    blocks: list[NormalizedBlock] = []
    is_json = "json" in payload.mime_type.lower()

    if is_json:
        try:
            value = json.loads(payload.body_text)
        except (json.JSONDecodeError, UnicodeError) as exc:
            warnings.append(
                NormalizationWarning(
                    code=NormalizationWarningCode.INVALID_JSON,
                    source_id=document_id,
                    message=f"JSON payload could not be decoded: {exc}",
                )
            )
        else:
            for block_index, (path, item) in enumerate(_json_leaves(value)):
                text = _display_value(item)
                locator = SourceLocator(
                    source_url=payload.url,
                    source_type=SourceType.API,
                    json_path=path,
                )
                blocks.append(
                    NormalizedBlock(
                        id=f"{document_id}:block:{block_index}",
                        type=NormalizedBlockType.KEY_VALUE,
                        raw_text=text,
                        text=text,
                        fields={"path": path, "value": text},
                        scalar_candidates=extract_scalar_candidates(text),
                        source_refs=(
                            SourceReference(source_item_id=document_id, locator=locator),
                        ),
                        extraction_method="json",
                    )
                )

    if not blocks and (text := normalize_multiline_text(payload.body_text)):
        blocks.append(
            NormalizedBlock(
                id=f"{document_id}:block:0",
                type=NormalizedBlockType.OTHER,
                raw_text=payload.body_text,
                text=text,
                scalar_candidates=extract_scalar_candidates(text),
                source_refs=(
                    SourceReference(source_item_id=document_id, locator=payload.locator),
                ),
                extraction_method="text",
            )
        )

    return (
        NormalizedDocument(
            id=document_id,
            name=str(payload.url),
            source_url=payload.url,
            source_type=SourceType.API,
            mime_type=payload.mime_type,
            content_sha256=payload.sha256,
            extraction_method="json" if is_json and not warnings else "text",
            quality_score=1.0 if blocks else 0.0,
            blocks=tuple(blocks),
        ),
        tuple(warnings),
    )


def _json_leaves(value: object, path: str = "$") -> Iterator[tuple[str, object]]:
    if isinstance(value, dict):
        for key, item in value.items():
            escaped = str(key).replace("\\", "\\\\").replace("'", "\\'")
            yield from _json_leaves(item, f"{path}['{escaped}']")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _json_leaves(item, f"{path}[{index}]")
    else:
        yield path, value


def _display_value(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    return text if text else '""'
