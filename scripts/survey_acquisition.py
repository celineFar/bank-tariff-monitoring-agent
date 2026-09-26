"""Acquire every enabled seed once and report what acquisition produced.

Read-only against the bank: linked PDFs are not downloaded and nothing is
written to the database. Each seed prints one JSON line; with ``--output`` the
whole survey is also written as a JSON array, to compare before and after an
acquisition change.

    uv run python -m scripts.survey_acquisition --output survey.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from pathlib import Path

import httpx

from app.config import load_settings
from app.config.seed_catalog import load_seed_catalog
from app.domain.acquisition import AcquisitionWarningCode
from app.services.acquisition import build_acquisition_service
from app.services.failure_mapping import source_failure_code


async def survey(offering_ids: set[str] | None) -> list[dict[str, object]]:
    settings = load_settings()
    with tempfile.TemporaryDirectory() as artifacts:
        settings = settings.model_copy(
            update={
                "acquisition": settings.acquisition.model_copy(
                    update={"max_linked_documents": 0}
                ),
                "application": settings.application.model_copy(
                    update={"artifact_temp_dir": Path(artifacts)}
                ),
            }
        )
        catalog = load_seed_catalog(allowed_hosts=settings.http.allowed_source_hosts)
        rows: list[dict[str, object]] = []
        async with httpx.AsyncClient(timeout=settings.http.timeout_seconds) as client:
            acquisition = build_acquisition_service(client, settings)
            for offering in catalog.offerings:
                if offering_ids and offering.offering_id not in offering_ids:
                    continue
                row: dict[str, object] = {
                    "offering": offering.offering_id,
                    "url": str(offering.seed_url),
                }
                try:
                    artifact = await acquisition.acquire(str(offering.seed_url))
                except Exception as exc:
                    row["failure_code"] = source_failure_code(
                        exc, stage="acquisition"
                    ).value
                    row["failure"] = str(exc)[:500]
                else:
                    row.update(
                        mode=artifact.acquisition_mode.value,
                        page_content_hash=artifact.page_content_hash[:16],
                        inventory=artifact.inventory.model_dump(mode="json"),
                        # The survey turns PDF downloads off with a cap of 0,
                        # so the cap warning it causes says nothing about the page.
                        warnings=[
                            warning.model_dump(mode="json")
                            for warning in artifact.warnings
                            if warning.code
                            is not AcquisitionWarningCode.LINKED_DOCUMENT_CAP_REACHED
                        ],
                    )
                print(json.dumps(row, ensure_ascii=False), flush=True)
                rows.append(row)
        return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, help="write the survey as JSON here")
    parser.add_argument(
        "--offering",
        action="append",
        dest="offerings",
        help="survey only this offering id (repeatable)",
    )
    args = parser.parse_args()
    rows = asyncio.run(survey(set(args.offerings or ())))
    if args.output:
        args.output.write_text(
            json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
