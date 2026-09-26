"""Measure what semantic extraction's evidence selection sends to Gemini, per seed.

    uv run python fix-process/semantic_extraction/survey/probe_evidence_recall.py \
        [--label before]

No model call. For each of the 13 captured seed pages
(`fix-process/normalization/.cache-live-2`, or `SURVEY_CACHE`):

1. the page is normalized without PDFs, as the source-discovery check does;
2. it is joined with the discovery assessments stored by that check
   (`fix-process/source_discovery/data/discovery-check-final.json`), so discovery is
   replayed, not re-run;
3. today's `build_evidence_catalog` and `build_extraction_batches` build the batches.

Each ground-truth fact of the normalization survey
(`fix-process/normalization/data/seed-ground-truth.json`) that maps to an extraction
field is then located in the evidence and classified:

- `selected`: the item carrying it is in the batch that extracts the field;
- `sibling_excluded`: it belongs to another offering (discovery: related product) and is
  correctly left out;
- `no_marker`: it never passes the field's keyword marker, so it can never be selected
  for the field;
- `ranked_out`: it passes the marker but ranks below the per-field quota;
- `not_in_catalog`: it is on the page but discovery did not select it.

It also reports score ties at the quota cut, footnotes separated from their rows, and
batch sizes. With `--label`, the result goes to `data/evidence-recall-<label>.json` and
the printed summary to `data/probe-output-<label>.txt`.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import replay  # noqa: E402

from app.config import load_settings  # noqa: E402
from app.domain.semantic_extraction import ExtractionField as F  # noqa: E402
from app.domain.source_discovery import ProductAssociation  # noqa: E402
from app.services import extraction_planner as ep  # noqa: E402
from app.services.extraction_evidence import build_evidence_catalog  # noqa: E402
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.semantic_extraction import build_extraction_prompt  # noqa: E402
from app.services.source_selection import build_selected_source_bundle  # noqa: E402

GT = json.loads(
    (ROOT / "fix-process/normalization/data/seed-ground-truth.json").read_text()
)

# First-cell label of a ground-truth row -> the field it evidences.
ROW_RULES: tuple[tuple[str, F], ...] = (
    (r"term \(months\)", F.TERM),
    (r"annual percentage rate|\bapr\b", F.EFFECTIVE_RATE),
    (r"interest rate", F.INTEREST_RATE),
    (r"down payment", F.DOWN_PAYMENT_PCT),
    (r"loan limit|financing limit", F.LOAN_AMOUNT),
    (r"credit limits", F.CREDIT_LIMIT),
    (r"loan-to-collateral", F.LTV_PCT),
    (r"^security$|real estate to be pledged", F.COLLATERAL),
    (r"customer age", F.AGE_REQUIREMENTS),
    (r"^documents$|required documents", F.REQUIRED_DOCUMENTS),
    (r"grace period", F.GRACE_PERIOD_DAYS),
    (
        r"minimum payment required|prepayment|cash payment at the bank"
        r"|online via the bank|myameria app",
        F.REPAYMENT,
    ),
    (
        r"fee|fines|cashing of the loan|collateral-related costs"
        r"|increase of credit limit|term extension|change of the|provision of loan"
        r"|revision/modification",
        F.FEES,
    ),
)
# Headline blocks: text -> field. A bare percentage is typed by the label block that
# follows it on the page (see `_headline_rate_field`).
BLOCK_RULES: tuple[tuple[str, F | None], ...] = (
    (r"indefinite term|months", F.TERM),
    (r"^(?:loan amount )?(?:up to )?amd|mln|million", F.LOAN_AMOUNT),
    (r"down payment|^from \d+%", F.DOWN_PAYMENT_PCT),
    (r"nominal interest rate", F.INTEREST_RATE),
    (r"^[\d.,\s\u2013-]+%$", None),  # typed from the next block's label
    (r"no (?:other mandatory )?fee", F.FEES),
    (r"online application|how to apply", F.APPLICATION_CHANNEL),
    (r"mandatory valuation", F.COLLATERAL),
)


def norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def _row_field(label: str) -> F | None:
    folded = norm(re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", label))
    return next(
        (field for pattern, field in ROW_RULES if re.search(pattern, folded)), None
    )


def _headline_rate_field(text: str, blocks) -> F | None:
    for index, block in enumerate(blocks):
        if norm(block.text) == norm(text) and index + 1 < len(blocks):
            label = norm(blocks[index + 1].text)
            if "nominal" in label:
                return F.INTEREST_RATE
            if "actual" in label or "percentage" in label or "apr" in label:
                return F.EFFECTIVE_RATE
    return None


def facts_for(seed: str, blocks) -> list[dict]:
    spec = GT["seeds"][seed]
    facts = []
    for table in spec.get("tables", []):
        table = GT["templates"][table["template"]] if "template" in table else table
        for fact in table.get("facts", []):
            field = _row_field(fact["row"][0])
            if field is not None:
                facts.append(
                    {"field": field, "needles": fact["row"], "label": fact["row"][0]}
                )
    for block in spec.get("blocks", []):
        text = norm(block["text"])
        for pattern, field in BLOCK_RULES:
            if re.search(pattern, text):
                field = field or _headline_rate_field(block["text"], blocks)
                if field is not None:
                    facts.append(
                        {
                            "field": field,
                            "needles": [block["text"]],
                            "label": block["text"],
                        }
                    )
                break
    return facts


async def run(label: str | None, pdfs: bool, mode: str | None) -> None:
    settings = load_settings()
    limits = settings.semantic_extraction
    if mode is not None:
        limits = limits.model_copy(update={"evidence_mode": mode})
    parser = HtmlArtifactParser(settings.http.allowed_source_hosts)
    catalog = replay.catalog()
    attempts = replay.forbid_gemini()
    stored = await replay.stored_transcriptions() if pdfs else None
    rows: list[dict] = []
    seeds: dict[str, dict] = {}
    for seed in GT["seeds"]:
        replayed = await replay.load_seed(seed, parser, catalog, stored_pdfs=stored)
        entry, bundle, discovery = replayed.entry, replayed.bundle, replayed.discovery
        canonical = str(bundle.canonical_url)
        evidence = build_evidence_catalog(
            build_selected_source_bundle(bundle, discovery), discovery
        )
        batches = ep.build_extraction_batches(
            entry.product, evidence, limits, canonical_url=canonical
        )
        own = [
            item
            for item in evidence
            if item.product_association is not ProductAssociation.RELATED_PRODUCT
        ]
        seeds[seed] = {
            "product": entry.product.value,
            "catalog_items": len(evidence),
            "catalog_chars": sum(len(item.content) for item in evidence),
            "own_chars": sum(len(item.content) for item in own),
            "pdfs_added": replayed.pdfs_added,
            "pdfs_missing": replayed.pdfs_missing,
            "items_in_any_batch": len(
                {item.evidence_id for b in batches for item in b.evidence}
            ),
            "batches": {
                batch.group: {
                    "items": len(batch.evidence),
                    "evidence_chars": sum(len(item.content) for item in batch.evidence),
                    "prompt_chars": len(build_extraction_prompt(batch)),
                    "units_left_out": list(batch.units_left_out),
                }
                for batch in batches
            },
        }
        # Ground-truth facts.
        page_text = [norm(block.text) for block in bundle.documents[0].blocks] + [
            norm(" | ".join(cell.text for cell in row.cells))
            for table in bundle.documents[0].tables
            for row in table.rows
        ]
        for fact in facts_for(seed, bundle.documents[0].blocks):
            field = fact["field"]
            calls = [batch for batch in batches if field in batch.fields]
            if not calls:
                continue  # not extracted for this product family
            needles = [norm(needle) for needle in fact["needles"]]
            carriers = [
                item
                for item in evidence
                if all(n in norm(item.content) for n in needles)
            ]
            if not carriers and len(needles) > 1:
                carriers = [
                    item
                    for item in evidence
                    if all(n in norm(item.content) for n in needles[1:])
                ]
            sent = [
                item
                for item in carriers
                if all(
                    item.evidence_id in {e.evidence_id for e in call.evidence}
                    for call in calls
                )
            ]
            sibling = bool(carriers) and all(
                item.product_association is ProductAssociation.RELATED_PRODUCT
                for item in carriers
            )
            if not carriers:
                on_page = any(
                    all(n in text for n in (needles[1:] or needles))
                    for text in page_text
                )
                status = "not_in_catalog" if on_page else "not_on_page"
            elif sibling:
                # Another offering's fact: excluded, or sent only in the marked
                # "other products" block, never as the offering's own evidence.
                status = "sibling_in_related_block" if sent else "sibling_excluded"
            elif sent:
                status = "selected"
            else:
                status = "not_selected"
            best = (sent or carriers or [None])[0]
            rows.append(
                {
                    "seed": seed,
                    "field": field.value,
                    "call": calls[0].group,
                    "label": fact["label"][:80],
                    "status": status,
                    "association": best.product_association.value if best else None,
                    "source_item_id": best.source_item_id if best else None,
                    "section": best.section if best else None,
                }
            )

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print(f"evidence mode: {limits.evidence_mode}; pdfs: {pdfs}")
        print(f"{'seed':32} {'product':13} items chars own_chars in_batches")
        for seed, value in seeds.items():
            print(
                f"{seed:32} {value['product']:13} {value['catalog_items']:5} "
                f"{value['catalog_chars']:6} {value['own_chars']:9} "
                f"{value['items_in_any_batch']:10}"
            )
        status = Counter(row["status"] for row in rows)
        current = [row for row in rows if not row["status"].startswith("sibling")]
        print(f"\nground-truth facts: {len(rows)} {dict(status)}")
        print(
            f"current-product facts reaching their batch: {status['selected']}/"
            f"{len(current)} ({status['selected'] / len(current):.0%})"
        )
        by_field: dict[str, Counter] = defaultdict(Counter)
        for row in current:
            by_field[row["field"]][row["status"]] += 1
        for field, counts in sorted(by_field.items()):
            print(f"  {field:24} {dict(counts)}")
        prompt = [
            b["prompt_chars"] for s in seeds.values() for b in s["batches"].values()
        ]
        chars = [
            b["evidence_chars"] for s in seeds.values() for b in s["batches"].values()
        ]
        calls = [len(s["batches"]) for s in seeds.values()]
        per_offering = [
            sum(b["prompt_chars"] for b in s["batches"].values())
            for s in seeds.values()
        ]
        print(
            f"calls per offering {min(calls)}-{max(calls)}; batch evidence chars "
            f"{min(chars)}-{max(chars)}; prompt chars per call {min(prompt)}-"
            f"{max(prompt)}; prompt chars per offering {min(per_offering)}-"
            f"{max(per_offering)} (total {sum(per_offering)})"
        )
        print(f"gemini attempts: {len(attempts)}")
    print(out.getvalue())
    if label:
        data = BASE / "data"
        data.mkdir(exist_ok=True)
        (data / f"evidence-recall-{label}.json").write_text(
            json.dumps(
                {"mode": limits.evidence_mode, "seeds": seeds, "facts": rows},
                indent=1,
                ensure_ascii=False,
                default=str,
            )
        )
        (data / f"probe-output-{label}.txt").write_text(out.getvalue())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--pdfs",
        action="store_true",
        help="add the seeds' current and shared PDFs from stored transcriptions",
    )
    parser.add_argument(
        "--mode",
        choices=("full", "budgeted"),
        default=None,
        help="evidence mode (default: the configured one)",
    )
    args = parser.parse_args()
    asyncio.run(run(args.label, args.pdfs, args.mode))


if __name__ == "__main__":
    main()
