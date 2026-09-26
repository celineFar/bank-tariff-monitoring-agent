"""Check the PDF content check against the hand labels.

    uv run python fix-process/source_discovery/survey/check_pdf_content.py \
        --label phase8 --max-usd 0.10

Takes every PDF link the Phase 7 link selection kept (`data/discovery-check-after.json`),
builds the PDF from its text layer (pypdf, one block per page, no Gemini
transcription), and runs source discovery on it with the real classifier and the
offering's context. Each PDF's document decision is compared with its label:
`current_product` and `shared_terms` must stay the offering's (`current_product` or
`unknown`, not excluded); `related_product` and `irrelevant` must not.

The text layer approximates what Gemini transcription produces; tables come out as
plain text. `GEMINI_API_KEY` from the environment; the run stops before any call if
the estimate exceeds `--max-usd`.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
CACHE = ROOT / "fix-process/normalization/.cache-live-2"
sys.path.insert(0, str(ROOT))

import pypdf  # noqa: E402

from app.config import load_settings  # noqa: E402
from app.config.seed_catalog import load_seed_catalog  # noqa: E402
from app.domain.acquisition import PageArtifact, SourceLocator, SourceType  # noqa: E402
from app.domain.normalization import (  # noqa: E402
    NormalizedBlock,
    NormalizedBlockType,
    NormalizedDocument,
    NormalizedSourceBundle,
    SourceReference,
)
from app.domain.pdf_extraction import (  # noqa: E402
    PdfAdmissionRole,
    PdfLinkChoice,
    PdfLinkLabel,
)
from app.domain.source_discovery import OfferingContext  # noqa: E402
from app.services.discovery_classifier import (  # noqa: E402
    AdkSourceDiscoveryClassifier,
    build_classifier_prompt,
)
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.model_pricing import get_model_price  # noqa: E402
from app.services.source_discovery import (  # noqa: E402
    InMemorySourceDiscoveryRepository,
    SourceDiscoveryService,
)

LABELS = json.loads((BASE / "data/seed-discovery-labels.json").read_text())
PDF_LABELS = json.loads(
    (ROOT / "fix-process/normalization/data/seed-pdf-labels.json").read_text()
)["pdfs"]
RUN = json.loads((BASE / "data/discovery-check-after.json").read_text())
AS_OF = date.fromisoformat(LABELS["as_of"])


def _pdf_document(path: Path, sha: str, name: str, url: str) -> NormalizedDocument:
    document_id = f"document:{sha[:12]}"
    blocks = []
    for number, page in enumerate(pypdf.PdfReader(str(path)).pages, start=1):
        text = " ".join((page.extract_text() or "").split())
        if not text:
            continue
        block_id = f"{document_id}:page:{number}:block:0"
        blocks.append(
            NormalizedBlock(
                id=block_id,
                type=NormalizedBlockType.PARAGRAPH,
                raw_text=text,
                text=text,
                source_refs=(
                    SourceReference(
                        source_item_id=block_id,
                        locator=SourceLocator(
                            source_url=url, source_type=SourceType.PDF, pdf_page=number
                        ),
                    ),
                ),
            )
        )
    return NormalizedDocument(
        id=document_id,
        name=name,
        source_url=url,
        source_type=SourceType.PDF,
        mime_type="application/pdf",
        content_sha256=sha,
        extraction_method="pypdf_text_layer",
        # The link step kept it; its label does not change the content check.
        pdf_selection=PdfLinkChoice(
            label=PdfLinkLabel.CURRENT_PRODUCT,
            role=PdfAdmissionRole.PRODUCT_TERMS,
            reason="kept by the Phase 7 link selection",
            decided_by="llm",
            model_name="recorded",
            link_fingerprint="0" * 64,
        ),
        blocks=tuple(blocks),
    )


async def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = load_settings()
    model = settings.source_discovery.model_name
    price = get_model_price(model)
    catalog = load_seed_catalog()
    entries = {entry.offering_id.value: entry for entry in catalog.offerings}
    parser = HtmlArtifactParser(settings.http.allowed_source_hosts)
    pdf_files = {
        hashlib.sha256(path.read_bytes()).hexdigest(): path
        for path in (CACHE / "pdfs").rglob("*")
        if path.is_file()
    }
    work = []
    for seed, value in RUN["seeds"].items():
        kept = {pdf["file"]: pdf["label"] for pdf in value["pdfs"] if pdf["selected"]}
        if not kept:
            continue
        artifact = PageArtifact.model_validate_json(
            (CACHE / f"{seed}.artifact.json").read_text()
        )
        parsed = parser.parse(
            artifact.rendered_html or "", source_url=str(artifact.final_url)
        )
        documents = []
        labels = {}
        for document in artifact.downloadable_documents:
            name = PDF_LABELS.get(document.sha256, {}).get("file")
            if name not in kept or document.sha256 not in pdf_files:
                continue
            if any(d.content_sha256 == document.sha256 for d in documents):
                continue
            documents.append(
                _pdf_document(
                    pdf_files[document.sha256],
                    document.sha256,
                    document.document_name,
                    str(document.final_url),
                )
            )
            labels[f"document:{document.sha256[:12]}"] = (name, kept[name])
        page = NormalizedDocument(
            id="page:0",
            name=artifact.title or seed,
            source_url=str(artifact.canonical_url),
            source_type=SourceType.PAGE,
            mime_type="text/html",
            content_sha256="0" * 64,
            extraction_method="browser",
        )
        bundle = NormalizedSourceBundle(
            canonical_url=str(artifact.canonical_url),
            acquisition_content_hash="0" * 64,
            documents=(page, *documents),
        )
        offering = OfferingContext.from_catalog_entry(
            entries[seed],
            page_title=artifact.title,
            page_blocks=parsed.blocks,
            catalog=catalog,
        )
        work.append((seed, bundle, offering, labels))

    estimate = 0.0
    for _, bundle, offering, _ in work:
        plan = await SourceDiscoveryService(
            None,
            InMemorySourceDiscoveryRepository(),
            settings.source_discovery,
            model_name=model,
        ).plan(bundle, offering, as_of=AS_OF)
        chars = sum(len(build_classifier_prompt(batch)) for batch in plan.batches)
        estimate += (
            (chars / 4 + 400 * len(plan.batches)) * price.input_per_million_tokens_usd
            + 200 * len(plan.llm_candidates) * price.output_per_million_tokens_usd
        ) / 1_000_000
    print(
        f"PDFs: {sum(len(w[3]) for w in work)}; estimated Gemini cost ${estimate:.4f}"
    )
    if estimate > args.max_usd:
        raise SystemExit("estimate exceeds --max-usd; nothing was sent")

    classifier = AdkSourceDiscoveryClassifier(
        model, api_key=os.environ["GEMINI_API_KEY"]
    )
    rows = []
    for seed, bundle, offering, labels in work:
        result = await SourceDiscoveryService(
            classifier,
            InMemorySourceDiscoveryRepository(),
            settings.source_discovery,
            model_name=model,
        ).discover(bundle, offering, as_of=AS_OF)
        for assessment in result.assessments:
            if (
                assessment.document_id not in labels
                or not assessment.source_id.startswith("document::")
            ):
                continue
            name, label = labels[assessment.document_id]
            kept_as_own = (
                assessment.relevance.value != "irrelevant"
                and assessment.product_association.value
                in {"current_product", "unknown"}
                and assessment.temporal_status.value not in {"possibly_stale", "future"}
            )
            expected_own = label in {"current_product", "shared_terms"}
            verdict = None
            if label in {"current_product", "shared_terms"} and not kept_as_own:
                verdict = "lost"
            if label in {"related_product", "irrelevant", "historical"} and kept_as_own:
                verdict = "leak"
            rows.append(
                {
                    "seed": seed,
                    "file": name,
                    "label": label,
                    "association": assessment.product_association.value,
                    "relevance": assessment.relevance.value,
                    "temporal": assessment.temporal_status.value,
                    "expected_own": expected_own,
                    "failure": verdict,
                    "reason": assessment.reason[:200],
                }
            )
    usage = classifier.usage
    spent = (
        usage.input_tokens * price.input_per_million_tokens_usd
        + usage.output_tokens * price.output_per_million_tokens_usd
    ) / 1_000_000
    report = {
        "model": model,
        "pdfs": len(rows),
        "lost": sum(1 for row in rows if row["failure"] == "lost"),
        "leak": sum(1 for row in rows if row["failure"] == "leak"),
        "usage": {
            "calls": usage.request_attempts,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "spent_usd": round(spent, 4),
        },
        "rows": rows,
    }
    for row in rows:
        if row["failure"]:
            print(row)
    print({key: report[key] for key in ("pdfs", "lost", "leak", "usage")})
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default=None)
    parser.add_argument("--max-usd", type=float, default=0.10)
    args = parser.parse_args()
    report = asyncio.run(run(args))
    if args.label:
        target = BASE / "data" / f"pdf-content-check-{args.label}.json"
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(f"written {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
