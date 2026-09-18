from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from pydantic import BaseModel

from app.config import load_settings
from app.domain.acquisition import PageArtifact
from app.domain.normalization import NormalizedSourceBundle
from app.services.artifact_store import FileSystemArtifactStore
from app.services.normalization import StructuralNormalizationService
from app.services.normalized_renderer import render_normalized_markdown


def write_normalization_bundle(
    bundle: NormalizedSourceBundle, *, output_directory: Path
) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "normalized_bundle.json").write_text(
        bundle.model_dump_json(indent=2), encoding="utf-8"
    )
    blocks = tuple(block for document in bundle.documents for block in document.blocks)
    tables = tuple(table for document in bundle.documents for table in document.tables)
    links = tuple(link for document in bundle.documents for link in document.links)
    scalars = [
        {
            "document_id": document.id,
            "container_id": block.id,
            **scalar.model_dump(mode="json"),
        }
        for document in bundle.documents
        for block in document.blocks
        for scalar in block.scalar_candidates
    ]
    scalars.extend(
        {
            "document_id": document.id,
            "container_id": row.id,
            "column_index": column_index,
            **scalar.model_dump(mode="json"),
        }
        for document in bundle.documents
        for table in document.tables
        for row in table.rows
        for column_index, cell in enumerate(row.cells)
        for scalar in cell.scalar_candidates
    )
    (output_directory / "normalized_blocks.json").write_text(
        _models_json(blocks), encoding="utf-8"
    )
    (output_directory / "normalized_tables.json").write_text(
        _models_json(tables), encoding="utf-8"
    )
    (output_directory / "normalized_links.json").write_text(
        _models_json(links), encoding="utf-8"
    )
    (output_directory / "normalized_scalars.json").write_text(
        json.dumps(scalars, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_directory / "normalized.md").write_text(
        render_normalized_markdown(bundle), encoding="utf-8"
    )
    (output_directory / "summary.txt").write_text(
        _summary(bundle), encoding="utf-8"
    )
    return output_directory


async def demonstrate(case_path: Path) -> Path:
    artifact_path, case_directory = _resolve_case(case_path)
    artifact = PageArtifact.model_validate_json(artifact_path.read_text(encoding="utf-8"))
    settings = load_settings()
    artifact_root = artifact_path.parent / "artifacts"
    service = StructuralNormalizationService(
        settings.ocr,
        artifact_reader=FileSystemArtifactStore(artifact_root),
    )
    bundle = await service.normalize(artifact)
    return write_normalization_bundle(
        bundle, output_directory=case_directory / "normalization"
    )


def _resolve_case(path: Path) -> tuple[Path, Path]:
    resolved = path.resolve()
    candidates = (
        resolved,
        resolved / "page_artifact.json",
        resolved / "output" / "page_artifact.json",
    )
    artifact_path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if artifact_path is None:
        raise FileNotFoundError(
            f"No page_artifact.json found at or below {resolved}"
        )
    case_directory = (
        artifact_path.parent.parent
        if artifact_path.parent.name == "output"
        else artifact_path.parent
    )
    return artifact_path, case_directory


def _models_json(models: tuple[BaseModel, ...]) -> str:
    return json.dumps(
        [model.model_dump(mode="json") for model in models],
        ensure_ascii=False,
        indent=2,
    )


def _summary(bundle: NormalizedSourceBundle) -> str:
    blocks = sum(len(document.blocks) for document in bundle.documents)
    tables = sum(len(document.tables) for document in bundle.documents)
    rows = sum(
        len(table.rows) for document in bundle.documents for table in document.tables
    )
    scalars = sum(
        len(block.scalar_candidates)
        for document in bundle.documents
        for block in document.blocks
    ) + sum(
        len(cell.scalar_candidates)
        for document in bundle.documents
        for table in document.tables
        for row in table.rows
        for cell in row.cells
    )
    lines = (
        f"Canonical URL: {bundle.canonical_url}",
        f"Acquisition content hash: {bundle.acquisition_content_hash}",
        f"Documents: {len(bundle.documents)}",
        f"Blocks: {blocks}",
        f"Tables: {tables}",
        f"Links: {sum(len(document.links) for document in bundle.documents)}",
        f"Table rows: {rows}",
        f"Scalar candidates: {scalars}",
        f"Warnings: {len(bundle.warnings)}",
        *(f"- [{warning.code}] {warning.source_id}: {warning.message}" for warning in bundle.warnings),
    )
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize an acquisition case into inspectable structural artifacts."
    )
    parser.add_argument(
        "case",
        type=Path,
        help="A case_NNN directory, its output directory, or page_artifact.json",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    output_directory = asyncio.run(demonstrate(args.case))
    print(f"Normalization bundle saved to {output_directory.resolve()}")


if __name__ == "__main__":
    main()
