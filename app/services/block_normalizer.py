from __future__ import annotations

from app.domain.acquisition import ContentBlock, ContentBlockType
from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    SourceReference,
    normalize_multiline_text,
    normalize_text,
)
from app.services.scalar_normalizer import extract_scalar_candidates


def normalize_block(
    block: ContentBlock,
    *,
    table_id: str | None = None,
    extraction_method: str = "html",
) -> NormalizedBlock:
    text = normalize_multiline_text(block.text)
    fields: dict[str, str] = {}
    if block.type is ContentBlockType.CARD:
        lines = tuple(line for line in text.splitlines() if line)
        if lines:
            fields["title"] = lines[0]
        if len(lines) > 1:
            fields["body"] = "\n".join(lines[1:])
    elif block.type is ContentBlockType.KEY_VALUE and block.key_value is not None:
        key, value = (normalize_multiline_text(part) for part in block.key_value)
        if key and value:
            fields = {"key": key, "value": value}
    elif block.type is ContentBlockType.KEY_VALUE:
        key, separator, value = text.partition(":")
        if separator and normalize_text(key) and normalize_text(value):
            fields = {"key": normalize_text(key), "value": normalize_text(value)}

    return NormalizedBlock(
        id=block.id,
        type=NormalizedBlockType(block.type.value),
        raw_text=block.text,
        text=text,
        markdown=(normalize_multiline_text(block.markdown) if block.markdown else None),
        heading_path=tuple(normalize_text(value) for value in block.heading_path),
        parent_id=block.parent_id,
        link_ids=block.link_ids,
        visible=block.visible,
        table_id=table_id,
        fields=fields,
        scalar_candidates=extract_scalar_candidates(text),
        source_refs=(SourceReference(source_item_id=block.id, locator=block.locator),),
        extraction_method=extraction_method,
    )
