import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from app.domain.discovery import (
    IngestedSource,
    SourceCandidateType,
    SourceIngestionResult,
)
from app.services.local_artifact_store import LocalArtifactStore
from scripts.extract_ingested_sources import _latest_manifest_key, _run

NOW = datetime(2026, 9, 17, 6, tzinfo=UTC)
RUN_ID = UUID("7ed4f4c4-c71e-477e-8150-7c32ef5b439f")
URL = "https://ameriabank.am/en/personal/loans/consumer-finance"


@pytest.mark.asyncio
async def test_manifest_artifact_only_cli_writes_viewable_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "artifacts"
    store = LocalArtifactStore(root)
    html = (
        b'<html lang="en"><main id="wsc_main_content">'
        b"<h1>Consumer finance</h1><dl><dt>Loan amount</dt>"
        b"<dd>50,000 - 6,000,000 AMD</dd></dl></main></html>"
    )
    artifact = await store.put(
        content=html,
        sha256=hashlib.sha256(html).hexdigest(),
        mime_type="text/html",
    )
    source = IngestedSource(
        product_id="consumer.finance",
        candidate_type=SourceCandidateType.PRODUCT_PAGE,
        source_url=URL,
        final_url=URL,
        retrieved_at=NOW,
        artifact=artifact,
    )
    ingestion = SourceIngestionResult(
        run_id=RUN_ID,
        started_at=NOW,
        completed_at=NOW,
        manifest_key=f"manifests/{RUN_ID}.json",
        products=(),
        sources=(source,),
        candidates=(),
    )
    manifest_key = await store.write_manifest(
        str(RUN_ID), ingestion.model_dump(mode="json")
    )
    monkeypatch.setenv("ARTIFACT_STORAGE_DIR", str(root))
    args = argparse.Namespace(
        manifest=None,
        latest_manifest=True,
        product_id=None,
        artifact_only=True,
        fail_fast=False,
        pretty=True,
    )

    exit_code = await _run(args)
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["manifest_key"] == manifest_key
    assert output["metadata_persisted"] is False
    assert output["extracted_count"] == 1
    assert output["failed_count"] == 0
    extracted_path = Path(output["extracted"][0]["json_path"])
    assert extracted_path.is_file()
    extracted = json.loads(extracted_path.read_text(encoding="utf-8"))
    assert extracted["blocks"][1]["label"] == "Loan amount"
    assert _latest_manifest_key(root) == manifest_key


@pytest.mark.asyncio
async def test_cli_accepts_legacy_manifest_without_source_timestamp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "artifacts"
    store = LocalArtifactStore(root)
    html = b'<html><main><h1>Legacy source</h1><p>Saved content.</p></main></html>'
    artifact = await store.put(
        content=html,
        sha256=hashlib.sha256(html).hexdigest(),
        mime_type="text/html",
    )
    source = IngestedSource(
        product_id="consumer.finance",
        candidate_type=SourceCandidateType.PRODUCT_PAGE,
        source_url=URL,
        final_url=URL,
        retrieved_at=NOW,
        artifact=artifact,
    )
    source_payload = source.model_dump(mode="json", exclude={"retrieved_at"})
    manifest_key = await store.write_manifest(
        "legacy",
        {
            "run_id": "legacy",
            "started_at": NOW.isoformat(),
            "completed_at": NOW.isoformat(),
            "sources": [source_payload],
        },
    )
    monkeypatch.setenv("ARTIFACT_STORAGE_DIR", str(root))
    args = argparse.Namespace(
        manifest=manifest_key,
        latest_manifest=False,
        product_id=None,
        artifact_only=True,
        fail_fast=False,
        pretty=False,
    )

    assert await _run(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["extracted_count"] == 1
