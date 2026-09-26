"""Replay a seed's sources for the semantic-extraction surveys, without any model call.

A seed's page comes from the normalization survey's last live capture
(`fix-process/normalization/.cache-live-2`, or `SURVEY_CACHE`), re-parsed by this
branch's parser. Its discovery assessments are the ones the source-discovery check
stored (`discovery-check-final.json`), so discovery is replayed, not re-run.

With `pdfs=True`, the seed's PDFs labelled `current_product` or `shared_terms` in the
source-discovery hand labels are added, when a stored Gemini transcription exists for
them (`pdf_extraction_cache` in `tariff_rt` and `tariff_monitor`, read-only). Their
assessments are built from the same hand labels (current product, or generic bank
information for shared terms), since the stored discovery run covered pages only. A
PDF with no stored transcription is reported as missing, never transcribed here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "fix-process/source_discovery/survey"))
os.environ.setdefault(
    "SURVEY_CACHE", str(ROOT / "fix-process/normalization/.cache-live-2")
)

import check_discovery_labels as cdl  # noqa: E402

from app.config import PdfExtractionSettings  # noqa: E402
from app.domain.acquisition import PageArtifact  # noqa: E402
from app.domain.normalization import (  # noqa: E402
    NormalizedDocument,
    NormalizedSourceBundle,
    SourceReference,
)
from app.domain.pdf_extraction import PdfExtractionResponse  # noqa: E402
from app.domain.source_discovery import (  # noqa: E402
    Authority,
    DecisionSource,
    DiscoveryScope,
    InformationRole,
    ProductAssociation,
    Relevance,
    SourceAssessment,
    SourceDiscoveryResult,
    TemporalStatus,
)
from app.services.discovery_prefilter import member_source_id  # noqa: E402
from app.services.normalization import StructuralNormalizationService  # noqa: E402
from app.services.pdf_extraction import GeminiPdfExtractionService  # noqa: E402

CACHE = cdl.CACHE
STORED = json.loads(
    (ROOT / "fix-process/source_discovery/data/discovery-check-final.json").read_text()
)
PDF_LABELS = cdl.LABELS  # seed-discovery-labels.json: per seed, file name -> label
PDF_FILES = cdl.PDF_LABELS  # seed-pdf-labels.json: sha256 -> {"file": ...}
KEPT_PDF_LABELS = {"current_product", "shared_terms"}


def forbid_gemini() -> list[str]:
    """Make any Gemini client construction fail; return the list of attempts."""
    import google.genai
    import google.genai.client

    attempts: list[str] = []

    def refuse(*_: Any, **__: Any) -> None:
        attempts.append("google.genai.Client")
        raise RuntimeError("Gemini is disabled in this survey")

    google.genai.Client.__init__ = refuse  # type: ignore[method-assign]
    google.genai.client.Client.__init__ = refuse  # type: ignore[method-assign]
    return attempts


def _database_password() -> str:
    # Read from the dev database container's environment, in memory only.
    return subprocess.run(
        [
            "docker",
            "exec",
            "bank-tariff-monitoring-agent-db-1",
            "sh",
            "-c",
            "echo $POSTGRES_PASSWORD",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


async def stored_transcriptions() -> dict[tuple[str, str], PdfExtractionResponse]:
    import asyncpg

    password = _database_password()
    stored: dict[tuple[str, str], PdfExtractionResponse] = {}
    for database in ("tariff_rt", "tariff_monitor"):
        connection = await asyncpg.connect(
            f"postgresql://tariff:{password}@localhost:5434/{database}"
        )
        try:
            rows = await connection.fetch(
                "SELECT DISTINCT ON (document_sha256, model_name) document_sha256, "
                "model_name, response::text AS response FROM pdf_extraction_cache "
                "ORDER BY document_sha256, model_name, updated_at DESC"
            )
        finally:
            await connection.close()
        for row in rows:
            stored.setdefault(
                (row["document_sha256"], row["model_name"]),
                PdfExtractionResponse.model_validate_json(row["response"]),
            )
    return stored


class ReplayRepository:
    """Serves stored transcriptions by PDF hash and model; never saves."""

    def __init__(self, stored: dict[tuple[str, str], PdfExtractionResponse]) -> None:
        self._stored = stored
        self.hits = 0

    async def get_exact(self, *, document_sha256: str, model_name: str, **_: Any):
        response = self._stored.get((document_sha256, model_name))
        self.hits += response is not None
        return response

    async def save(self, **_: Any) -> None:
        return None


class CapturedPdfs:
    async def read(self, artifact: Any) -> bytes:
        return (CACHE / "pdfs" / f"{artifact.sha256}.pdf").read_bytes()


@dataclass
class ReplayedSeed:
    seed: str
    entry: Any
    artifact: PageArtifact
    bundle: NormalizedSourceBundle
    discovery: SourceDiscoveryResult
    pdfs_added: list[str] = field(default_factory=list)
    pdfs_missing: list[str] = field(default_factory=list)


def _file_name(document: Any) -> str:
    return (
        PDF_FILES.get(document.sha256, {}).get("file")
        or str(document.final_url).rsplit("/", 1)[-1]
    )


def _pdf_assessments(
    document: NormalizedDocument, label: str
) -> list[SourceAssessment]:
    association = (
        ProductAssociation.CURRENT_PRODUCT
        if label == "current_product"
        else ProductAssociation.GENERIC_BANK_INFORMATION
    )
    items = [
        (DiscoveryScope.BLOCK, "block", block.id, block.source_refs)
        for block in document.blocks
        if block.table_id is None
    ]
    items += [
        (DiscoveryScope.TABLE, "table", table.id, table.source_refs)
        for table in document.tables
    ]
    return [
        SourceAssessment(
            source_id=member_source_id(document.id, kind, item_id),
            document_id=document.id,
            scope=scope,
            product_association=association,
            role=InformationRole.PRODUCT_TERMS,
            relevance=Relevance.RELEVANT,
            authority=Authority.OFFICIAL_TERMS,
            temporal_status=TemporalStatus.CURRENT,
            reason=f"replayed hand label: {label}",
            decision_source=DecisionSource.RULE,
            input_fingerprint="0" * 64,
            structural_fingerprint="0" * 64,
            source_refs=(
                SourceReference(source_item_id=item_id, locator=refs[0].locator),
            ),
        )
        for scope, kind, item_id, refs in items
    ]


async def load_seed(
    seed: str,
    parser: Any,
    catalog: dict[str, Any],
    *,
    stored_pdfs: dict[tuple[str, str], PdfExtractionResponse] | None = None,
) -> ReplayedSeed:
    path = CACHE / f"{seed}.artifact.json"
    artifact = cdl.reparsed(PageArtifact.model_validate_json(path.read_text()), parser)
    labels = PDF_LABELS["seeds"].get(seed, {}).get("pdfs", {})
    added: list[str] = []
    missing: list[str] = []
    documents = ()
    if stored_pdfs is not None:
        replayable = {sha for sha, _ in stored_pdfs}
        kept = []
        for document in artifact.downloadable_documents:
            name = _file_name(document)
            if labels.get(name) not in KEPT_PDF_LABELS:
                continue
            if document.sha256 in replayable:
                if name not in added:
                    kept.append(document)
                    added.append(name)
            elif name not in missing:
                missing.append(name)
        documents = tuple(kept)
    service = StructuralNormalizationService(
        artifact_reader=CapturedPdfs(),
        pdf_extractor=(
            GeminiPdfExtractionService(
                PdfExtractionSettings(),
                ReplayRepository(stored_pdfs),
                api_key="replay-only",
            )
            if stored_pdfs is not None
            else None
        ),
    )
    bundle = await service.normalize(
        artifact.model_copy(update={"downloadable_documents": documents})
    )
    unique: dict[str, SourceAssessment] = {}
    for value in STORED["seeds"][seed]["assessments"].values():
        assessment = SourceAssessment.model_validate(value)
        unique[assessment.source_id] = assessment
    names = {document.sha256: _file_name(document) for document in documents}
    for document in bundle.documents[1:]:
        label = labels.get(names.get(document.content_sha256, ""), "")
        for assessment in _pdf_assessments(document, label or "shared_terms"):
            unique[assessment.source_id] = assessment
    entry = catalog[seed]
    discovery = SourceDiscoveryResult(
        product=entry.product,
        offering_id=seed,
        input_content_hash=bundle.acquisition_content_hash,
        policy_version="replay",
        prompt_version="replay",
        model_name=STORED["model"],
        assessments=tuple(unique.values()),
        llm_batch_count=0,
        reused_assessment_count=0,
    )
    return ReplayedSeed(seed, entry, artifact, bundle, discovery, added, missing)


def catalog() -> dict[str, Any]:
    return cdl._catalog()


def seeds() -> list[str]:
    return sorted(
        path.name.removesuffix(".artifact.json")
        for path in CACHE.glob("*.artifact.json")
    )
