from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

import httpx
from pydantic import BaseModel

from app.config import load_settings
from app.domain.acquisition import PageArtifact
from app.services.acquisition import build_acquisition_service

DEFAULT_INSPECTION_DIRECTORY = Path(".temp/acuisition_test")
_CASE_DIRECTORY = re.compile(r"^case_(\d+)$")


def write_inspection_bundle(
    artifact: PageArtifact,
    *,
    requested_url: str,
    inspection_directory: Path = DEFAULT_INSPECTION_DIRECTORY,
) -> Path:
    """Write one human-readable acquisition bundle and return its output path."""
    output_directory = inspection_directory / "output"
    output_directory.mkdir(parents=True, exist_ok=True)

    (inspection_directory / "source_url.txt").write_text(
        requested_url.strip() + "\n", encoding="utf-8"
    )
    (output_directory / "page_artifact.json").write_text(
        artifact.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_directory / "blocks.json").write_text(
        _models_json(artifact.blocks), encoding="utf-8"
    )
    (output_directory / "tables.json").write_text(
        _models_json(artifact.tables), encoding="utf-8"
    )
    (output_directory / "links.json").write_text(
        _models_json(artifact.links), encoding="utf-8"
    )
    (output_directory / "documents.json").write_text(
        _models_json(artifact.downloadable_documents), encoding="utf-8"
    )
    (output_directory / "images.json").write_text(
        _models_json(artifact.images), encoding="utf-8"
    )
    (output_directory / "interactive_controls.json").write_text(
        _models_json(artifact.interactive_controls), encoding="utf-8"
    )
    if artifact.raw_html is not None:
        (output_directory / "raw.html").write_text(artifact.raw_html, encoding="utf-8")
    if artifact.rendered_html is not None:
        (output_directory / "rendered.html").write_text(
            artifact.rendered_html, encoding="utf-8"
        )
    if artifact.markdown is not None:
        (output_directory / "page.md").write_text(artifact.markdown, encoding="utf-8")
    (output_directory / "summary.txt").write_text(_summary(artifact), encoding="utf-8")
    return output_directory


async def demonstrate(url: str, inspection_directory: Path) -> Path:
    case_directory = _next_case_directory(inspection_directory)
    output_directory = case_directory / "output"
    settings = load_settings(
        artifact_temp_dir=output_directory / "artifacts",
    )
    timeout = httpx.Timeout(settings.http.timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        artifact = await build_acquisition_service(client, settings).acquire(url)
    return write_inspection_bundle(
        artifact,
        requested_url=url,
        inspection_directory=case_directory,
    )


def _next_case_directory(inspection_directory: Path) -> Path:
    inspection_directory.mkdir(parents=True, exist_ok=True)
    existing_numbers = [
        int(match.group(1))
        for path in inspection_directory.iterdir()
        if path.is_dir() and (match := _CASE_DIRECTORY.fullmatch(path.name))
    ]
    case_number = max(existing_numbers, default=-1) + 1
    while True:
        case_directory = inspection_directory / f"case_{case_number:03d}"
        try:
            case_directory.mkdir(exist_ok=False)
        except FileExistsError:
            case_number += 1
            continue
        return case_directory


def _models_json(models: tuple[BaseModel, ...]) -> str:
    values = [model.model_dump(mode="json") for model in models]
    return json.dumps(values, ensure_ascii=False, indent=2)


def _summary(artifact: PageArtifact) -> str:
    lines = (
        f"Requested URL: {artifact.url}",
        f"Final URL: {artifact.final_url}",
        f"Canonical URL: {artifact.canonical_url}",
        f"Mode: {artifact.acquisition_mode.value}",
        f"Retrieved at: {artifact.retrieved_at.isoformat()}",
        f"Content hash: {artifact.content_hash}",
        f"Blocks: {len(artifact.blocks)}",
        f"Tables: {len(artifact.tables)}",
        f"Links: {len(artifact.links)}",
        f"Documents: {len(artifact.downloadable_documents)}",
        f"Images: {len(artifact.images)}",
        f"Interactive controls: {len(artifact.interactive_controls)}",
        f"Warnings: {len(artifact.warnings)}",
        *(f"- {warning}" for warning in artifact.warnings),
    )
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Acquire an official loan page and save a manual inspection bundle."
    )
    parser.add_argument("url", help="Official HTTPS page URL to acquire")
    parser.add_argument(
        "--inspection-directory",
        type=Path,
        default=DEFAULT_INSPECTION_DIRECTORY,
        help=(
            "Bundle directory containing source_url.txt and output/ "
            "inside incrementing case_NNN directories "
            "(default: .temp/acuisition_test)"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    output_directory = asyncio.run(demonstrate(args.url, args.inspection_directory))
    print(f"Acquisition bundle saved to {output_directory.resolve()}")


if __name__ == "__main__":
    main()
