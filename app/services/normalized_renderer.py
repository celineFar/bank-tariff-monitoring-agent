from __future__ import annotations

import re

from app.domain.normalization import (
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedSourceBundle,
    NormalizedTable,
)


def render_normalized_markdown(bundle: NormalizedSourceBundle) -> str:
    parts: list[str] = []
    for document in bundle.documents:
        parts.append(f"# {_escape_plain(document.name)}")
        parts.append(f"Source: <{document.source_url}>")
        table_by_id = {table.id: table for table in document.tables}
        rendered_tables: set[str] = set()
        for block in document.blocks:
            if block.type is NormalizedBlockType.TABLE and block.table_id:
                table = table_by_id.get(block.table_id)
                if table is not None:
                    parts.append(_render_table(table))
                    rendered_tables.add(table.id)
                continue
            parts.append(_render_block(block))
        for table in document.tables:
            if table.id not in rendered_tables:
                parts.append(_render_table(table))
    return "\n\n".join(part for part in parts if part).strip() + "\n"


def _render_block(block: NormalizedBlock) -> str:
    if block.type is NormalizedBlockType.HEADING:
        level = min(max(len(block.heading_path), 1) + 1, 6)
        return f"{'#' * level} {_escape_plain(block.text)}"
    if block.type is NormalizedBlockType.LIST:
        return "\n".join(
            f"- {_escape_plain(line.lstrip('-•▪◦ ').strip())}"
            for line in block.text.splitlines()
            if line.strip()
        )
    if block.type is NormalizedBlockType.CARD and block.fields:
        title = block.fields.get("title", "")
        body = block.fields.get("body", "")
        return f"### {_escape_plain(title)}\n\n{_escape_plain(body)}".strip()
    return block.markdown or _escape_plain(block.text)


def _render_table(table: NormalizedTable) -> str:
    parts: list[str] = []
    if table.title:
        parts.append(f"### {_escape_plain(table.title)}")
    if table.headers:
        parts.append(
            "| "
            + " | ".join(_escape_plain_cell(value) for value in table.headers)
            + " |"
        )
        parts.append("| " + " | ".join("---" for _ in table.headers) + " |")
        for row in table.rows:
            values = [
                _escape_markdown_cell(cell.markdown)
                if cell.markdown
                else _escape_plain_cell(cell.text)
                for cell in row.cells
            ]
            parts.append("| " + " | ".join(values) + " |")
    for note in table.notes:
        marker = f"{note.marker} " if note.marker else ""
        parts.append(f"> {marker}{_escape_plain(note.text)}")
    return "\n".join(parts)


def _escape_plain_cell(value: str) -> str:
    return _escape_plain(value).replace("|", "\\|").replace("\n", "<br>")


def _escape_markdown_cell(value: str) -> str:
    return (
        value.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("|", "\\|")
        .replace("\n", "<br>")
    )


def _escape_plain(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"([\\`*_\[\]<>])", r"\\\1", normalized)
    return re.sub(r"(?m)^(\s*)([#>+\-]|\d+[.)])(?=\s)", r"\1\\\2", normalized)
