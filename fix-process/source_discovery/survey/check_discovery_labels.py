"""Check source discovery against the hand labels in `data/seed-discovery-labels.json`.

    uv run python fix-process/source_discovery/survey/check_discovery_labels.py \
        --classifier gemini --label before --max-usd 0.40

For every captured seed (`fix-process/normalization/.cache-live-2`, or `SURVEY_CACHE`), the
page is normalized without PDFs and discovery runs on it with the chosen classifier:

- `gemini`: the real classifier, `GEMINI_API_KEY` from the environment. Before any
  call, the prompt size of every batch is estimated; the run stops if the estimate
  exceeds `--max-usd`. Actual token use and cost are reported.
- `none`: no classifier; only rule decisions are scored (a dry run of the harness).

Each page block and table is then compared with its label:

- `current` fails when discovery excludes it or calls it another product
  (`lost`);
- `related` fails when discovery calls it the current product or `unknown`, since
  extraction treats both as the offering's own evidence (`leak`);
- `navigation` fails when discovery keeps it as current or unknown (`noise`);
- `historical` (a link to an old edition) fails when kept as current or unknown
  (`stale`);
- `any` is not scored.

PDF links are scored separately: `current_product` and `shared_terms` must be
selected for transcription; `related_product` and `irrelevant` must not be.
`generic_bank_information` is not scored.

With `--label`, the result is written to `data/discovery-check-<label>.json`. The
report keeps every block and table assessment, so `--rescore <report>` can score it
again after the labels change, without calling Gemini.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
CACHE = Path(
    os.environ.get("SURVEY_CACHE", ROOT / "fix-process/normalization/.cache-live-2")
)
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.domain.acquisition import PageArtifact  # noqa: E402
from app.domain.catalog import SeedCatalogEntry  # noqa: E402
from app.domain.source_discovery import (  # noqa: E402
    DiscoveryScope,
    ProductAssociation,
    Relevance,
    SourceAssessment,
    TemporalStatus,
)
from app.services.acquisition import AcquisitionService  # noqa: E402
from app.services.discovery_classifier import build_classifier_prompt  # noqa: E402
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.model_pricing import get_model_price  # noqa: E402
from app.services.normalization import StructuralNormalizationService  # noqa: E402
from app.services.pdf_admission import assess_pdf_metadata  # noqa: E402
from app.services.source_discovery import (  # noqa: E402
    InMemorySourceDiscoveryRepository,
    SourceDiscoveryService,
)

LABELS = json.loads((BASE / "data" / "seed-discovery-labels.json").read_text())
PDF_LABELS = json.loads(
    (ROOT / "fix-process/normalization/data/seed-pdf-labels.json").read_text()
)["pdfs"]
AS_OF = date.fromisoformat(LABELS["as_of"])


def reparsed(artifact: PageArtifact, parser: HtmlArtifactParser) -> PageArtifact:
    """The capture's page as this branch's parser reads it.

    Captures were stored before blocks carried `site_chrome`; re-parsing the
    stored rendered HTML gives the blocks, tables and links acquisition would
    produce today (as the normalization survey does for PDF link context).
    """
    parsed = parser.parse(
        artifact.rendered_html or "", source_url=str(artifact.final_url)
    )
    return artifact.model_copy(
        update={"blocks": parsed.blocks, "tables": parsed.tables, "links": parsed.links}
    )


class _GuardedClassifier:
    """Refuses to call the model once the running estimate passes the budget."""

    def __init__(self, inner: Any, price: Any, max_usd: float) -> None:
        self.inner = inner
        self.price = price
        self.max_usd = max_usd
        self.calls = 0

    def spent_usd(self) -> float:
        usage = self.inner.usage
        return (
            usage.input_tokens * self.price.input_per_million_tokens_usd
            + (usage.output_tokens + usage.thinking_tokens)
            * self.price.output_per_million_tokens_usd
        ) / 1_000_000

    async def classify(self, batch: Any) -> Any:
        if self.spent_usd() >= self.max_usd:
            raise RuntimeError(
                f"spend guard: ${self.spent_usd():.4f} >= ${self.max_usd}"
            )
        self.calls += 1
        return await self.inner.classify(batch)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


def _catalog() -> dict[str, SeedCatalogEntry]:
    from app.config.seed_catalog import load_seed_catalog

    return {entry.offering_id.value: entry for entry in load_seed_catalog().offerings}


def _outcome(assessment: SourceAssessment | None) -> str:
    if assessment is None:
        return "missing"
    if assessment.relevance is Relevance.IRRELEVANT:
        return "excluded"
    if assessment.temporal_status in {
        TemporalStatus.POSSIBLY_STALE,
        TemporalStatus.FUTURE,
    }:
        return "excluded"
    return {
        ProductAssociation.CURRENT_PRODUCT: "current",
        ProductAssociation.UNKNOWN: "unknown",
        ProductAssociation.RELATED_PRODUCT: "related",
        ProductAssociation.GENERIC_BANK_INFORMATION: "generic",
        ProductAssociation.GLOBAL_NAVIGATION: "excluded",
        ProductAssociation.HISTORICAL_VERSION: "excluded",
        ProductAssociation.FUTURE_VERSION: "excluded",
    }[assessment.product_association]


def _verdict(expected: str, outcome: str) -> str | None:
    """None when the outcome is acceptable, else the kind of failure."""
    if expected == "any":
        return None
    if expected == "historical":
        return "stale" if outcome in {"current", "unknown", "missing"} else None
    if expected == "current":
        return "lost" if outcome in {"excluded", "related", "missing"} else None
    if expected == "related":
        return "leak" if outcome in {"current", "unknown", "missing"} else None
    if expected == "navigation":
        return "noise" if outcome in {"current", "unknown", "missing"} else None
    raise ValueError(expected)


def _block_label(
    spec: dict, block, *, in_footer: bool, before_heading: bool, chrome: bool
) -> str:
    if chrome or in_footer or before_heading:
        return "navigation"
    if any(
        block.text.startswith(prefix) for prefix in LABELS.get("navigation_text", ())
    ):
        return "navigation"
    if any(
        re.search(pattern, block.text, re.IGNORECASE)
        for pattern in LABELS.get("historical_text", ())
    ):
        return "historical"
    folded = block.text.casefold()
    if any(token.casefold() in folded for token in spec.get("text_any", ())):
        return "any"
    path = " > ".join(block.heading_path)
    if block.type.value == "heading":
        # A heading opens its own section: a cross-sell card's title belongs
        # to the card, not to the section above it.
        path = f"{path} > {block.text}" if path else block.text
    for rule in spec["sections"]:
        if "path_endswith" in rule and path.endswith(rule["path_endswith"]):
            return rule["label"]
        if "path_contains" in rule and rule["path_contains"] in path:
            return rule["label"]
    return spec["default"]


async def _discover(service: SourceDiscoveryService, bundle, entry: SeedCatalogEntry):
    """Call discovery with whichever signature the code on this branch has."""
    parameters = inspect.signature(service.discover).parameters
    if "offering" in parameters:
        from app.domain.source_discovery import OfferingContext

        offering = OfferingContext.from_catalog_entry(
            entry,
            page_title=bundle.documents[0].name,
            page_blocks=bundle.documents[0].blocks,
        )
        kwargs = {"as_of": AS_OF} if "as_of" in parameters else {}
        return await service.discover(bundle, offering, **kwargs)
    return await service.discover(bundle, entry.product)


def _estimate_usd(plan, price, settings) -> float:
    input_chars = sum(len(build_classifier_prompt(batch)) for batch in plan.batches)
    input_tokens = input_chars / settings.estimated_chars_per_input_token + 400 * len(
        plan.batches
    )
    output_tokens = settings.estimated_output_tokens_per_item * sum(
        len(batch.items) for batch in plan.batches
    )
    return (
        input_tokens * price.input_per_million_tokens_usd
        + output_tokens * price.output_per_million_tokens_usd
    ) / 1_000_000


def _rebuilt_documents(artifact: PageArtifact, parser) -> tuple:
    """The capture's PDF links with their context rebuilt by this branch's code."""
    parsed = parser.parse(
        artifact.rendered_html or "", source_url=str(artifact.final_url)
    )
    documents = []
    for document in artifact.downloadable_documents:
        origin = (
            AcquisitionService._document_origin(parsed, document.link_id)
            if document.link_id
            else {}
        )
        documents.append(
            document.model_copy(
                update={
                    "origin_block_id": None,
                    "origin_heading_path": (),
                    "nearby_text": "",
                    **origin,
                }
            )
        )
    return tuple(documents)


def _file_name(sha256: str, fallback: str) -> str:
    return PDF_LABELS.get(sha256, {}).get("file") or fallback


def _admission_decisions(documents) -> dict[str, bool]:
    """Before PDF link selection: every admitted PDF is transcribed and kept."""
    decisions: dict[str, bool] = {}
    for document in documents:
        admission = assess_pdf_metadata(document, as_of=AS_OF)
        if admission.temporal_status.value == "historical":
            continue
        name = _file_name(document.sha256, document.document_name)
        decisions[name] = (
            decisions.get(name, False) or admission.relevance.value != "irrelevant"
        )
    return decisions


class _LabelSelector:
    """Replays the hand labels as a selector: checks the plumbing, not Gemini."""

    def __init__(self, seed: str) -> None:
        self.labels = LABELS["seeds"][seed]["pdfs"]

    async def classify(self, batch):
        from app.domain.pdf_extraction import PdfAdmissionRole, PdfLinkLabel
        from app.domain.source_discovery import (
            PdfLinkBatchResponse,
            PdfLinkModelDecision,
        )

        label_map = {
            "current_product": PdfLinkLabel.CURRENT_PRODUCT,
            "shared_terms": PdfLinkLabel.SHARED_TERMS,
            "related_product": PdfLinkLabel.RELATED_PRODUCT,
            "generic_bank_information": PdfLinkLabel.GENERIC_BANK_INFORMATION,
            "irrelevant": PdfLinkLabel.GENERIC_BANK_INFORMATION,
        }
        return PdfLinkBatchResponse(
            items=tuple(
                PdfLinkModelDecision(
                    id=link.id,
                    label=label_map.get(
                        self.labels.get(link.file_name, ""), PdfLinkLabel.UNCLEAR
                    ),
                    role=PdfAdmissionRole.OTHER,
                    reason="replayed hand label",
                )
                for link in batch.links
            )
        )


async def _selection_decisions(
    artifact: PageArtifact,
    documents,
    offering,
    classifier,
    model: str,
    repository=None,
) -> dict[str, bool]:
    """With PDF link selection: only current, shared and unclear PDFs are kept."""
    from app.services.pdf_link_selection import (
        InMemoryPdfLinkSelectionRepository,
        PdfLinkSelectionService,
    )

    service = PdfLinkSelectionService(
        ((model, classifier),),
        repository or InMemoryPdfLinkSelectionRepository(),
        policy_version="survey",
    )
    selection = await service.select(
        artifact.model_copy(update={"downloadable_documents": documents}), offering
    )
    decisions: dict[str, bool] = {}
    names = {document.sha256: document.document_name for document in documents}
    for sha, choice in selection.choices.items():
        name = _file_name(sha, names[sha])
        decisions[name] = decisions.get(name, False) or choice.transcribe
    # Admitted-but-historical and off-topic links are skipped before selection.
    for document in documents:
        decisions.setdefault(_file_name(document.sha256, document.document_name), False)
    return decisions


async def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = load_settings()
    discovery_settings = settings.source_discovery
    model = args.model or discovery_settings.model_name
    price = get_model_price(model)
    parser = HtmlArtifactParser(settings.http.allowed_source_hosts)
    catalog = _catalog()
    guard = None
    stored = json.loads(Path(args.rescore).read_text()) if args.rescore else None
    if stored is not None:
        model = stored["model"]
    if args.classifier == "gemini" and stored is None:
        from app.services.discovery_classifier import AdkSourceDiscoveryClassifier

        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise SystemExit("GEMINI_API_KEY is required for --classifier gemini")
        guard = _GuardedClassifier(
            AdkSourceDiscoveryClassifier(model, api_key=key), price, args.max_usd
        )

    pdf_guard = None
    if args.pdf_selector == "gemini":
        from app.services.pdf_link_selection import AdkPdfLinkClassifier

        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise SystemExit("GEMINI_API_KEY is required for --pdf-selector gemini")
        pdf_guard = _GuardedClassifier(
            AdkPdfLinkClassifier(model, api_key=key), price, args.max_usd
        )

    seeds: dict[str, Any] = {}
    plans = []
    bundles = {}
    for path in sorted(CACHE.glob("*.artifact.json")):
        seed = path.name.removesuffix(".artifact.json")
        if args.seed and seed not in args.seed:
            continue
        artifact = reparsed(PageArtifact.model_validate_json(path.read_text()), parser)
        page_only = artifact.model_copy(update={"downloadable_documents": ()})
        normalizer = StructuralNormalizationService(
            artifact_reader=None, pdf_extractor=None
        )
        bundle = await normalizer.normalize(page_only)
        bundles[seed] = (artifact, bundle)

    # Estimate the whole run before the first call.
    estimate = 0.0
    for seed, (_artifact, bundle) in bundles.items():
        service = SourceDiscoveryService(
            None,
            InMemorySourceDiscoveryRepository(),
            discovery_settings,
            model_name=model,
        )
        plan_parameters = inspect.signature(service.plan).parameters
        if "offering" in plan_parameters:
            from app.domain.source_discovery import OfferingContext

            plan = await service.plan(
                bundle,
                OfferingContext.from_catalog_entry(
                    catalog[seed],
                    page_title=bundle.documents[0].name,
                    page_blocks=bundle.documents[0].blocks,
                ),
            )
        else:
            plan = await service.plan(bundle, catalog[seed].product)
        plans.append(plan)
        estimate += _estimate_usd(plan, price, discovery_settings)
    print(f"estimated Gemini cost: ${estimate:.4f} (guard ${args.max_usd:.2f})")
    if stored is not None:
        print(f"re-scoring {args.rescore} without Gemini")
    elif guard is not None and estimate > args.max_usd:
        raise SystemExit("estimate exceeds the spend guard; nothing was sent")

    totals = {
        "lost": 0,
        "leak": 0,
        "noise": 0,
        "stale": 0,
        "scored": 0,
        "tables_scored": 0,
    }
    # Shared across seeds and passes, so `--repeat 2` measures the cache.
    discovery_repository = InMemorySourceDiscoveryRepository()
    link_repository = None
    if args.pdf_selector != "admission":
        from app.services.pdf_link_selection import InMemoryPdfLinkSelectionRepository

        link_repository = InMemoryPdfLinkSelectionRepository()
    for seed, (artifact, bundle) in bundles.items():
        spec = LABELS["seeds"][seed]
        entry = catalog[seed]
        service = SourceDiscoveryService(
            guard,
            discovery_repository,
            discovery_settings,
            model_name=model,
        )
        if guard is None or stored is not None:
            result = None
        else:
            result = await _discover(service, bundle, entry)
        parsed = parser.parse(
            artifact.rendered_html or "", source_url=str(artifact.final_url)
        )
        page = bundle.documents[0]
        by_item: dict[str, SourceAssessment] = {}
        if stored is not None:
            by_item = {
                item_id: SourceAssessment.model_validate(value)
                for item_id, value in stored["seeds"][seed]["assessments"].items()
            }
            result = True
        elif result is not None:
            for assessment in result.assessments:
                if assessment.scope in {DiscoveryScope.BLOCK, DiscoveryScope.TABLE}:
                    for ref in assessment.source_refs:
                        by_item.setdefault(ref.source_item_id, assessment)
        failures: list[dict[str, str]] = []
        counts = {"lost": 0, "leak": 0, "noise": 0, "stale": 0, "scored": 0}
        seen_heading = False
        in_footer = False
        for block in page.blocks:
            if block.table_id:
                continue
            # The page's main heading ends the header (as in discovery itself).
            if block.heading_path or block.type.value == "heading":
                seen_heading = True
            if any(block.text.startswith(marker) for marker in LABELS["footer_from"]):
                in_footer = True
            expected = _block_label(
                spec,
                block,
                in_footer=in_footer,
                before_heading=not seen_heading,
                chrome=block.id in parsed.chrome_ids,
            )
            if result is None or expected == "any":
                continue
            outcome = _outcome(by_item.get(block.id))
            counts["scored"] += 1
            if (kind := _verdict(expected, outcome)) is not None:
                counts[kind] += 1
                failures.append(
                    {
                        "kind": kind,
                        "item": "block",
                        "path": " > ".join(block.heading_path),
                        "text": block.text[:100],
                        "expected": expected,
                        "outcome": outcome,
                        "reason": (
                            by_item[block.id].reason[:200]
                            if block.id in by_item
                            else None
                        ),
                    }
                )
        tables = []
        for table in page.tables:
            expected = spec["tables"].get(table.title or "", "unlabelled")
            outcome = (
                _outcome(by_item.get(table.id)) if result is not None else "not run"
            )
            kind = (
                _verdict(expected, outcome)
                if result is not None and expected not in {"unlabelled"}
                else None
            )
            assessed = by_item.get(table.id)
            tables.append(
                {
                    "title": table.title,
                    "expected": expected,
                    "outcome": outcome,
                    "failure": kind,
                    "temporal": assessed.temporal_status.value if assessed else None,
                    "reason": assessed.reason[:300] if assessed else None,
                }
            )
            if kind:
                counts[kind] += 1
                failures.append(
                    {
                        "kind": kind,
                        "item": "table",
                        "path": table.title or "",
                        "text": "",
                        "expected": expected,
                        "outcome": outcome,
                    }
                )
        documents = _rebuilt_documents(artifact, parser)
        if args.pdf_selector == "admission":
            pdf_selected = _admission_decisions(documents)
        else:
            from app.domain.source_discovery import OfferingContext

            pdf_selected = await _selection_decisions(
                artifact,
                documents,
                OfferingContext.from_catalog_entry(
                    entry, page_title=artifact.title, page_blocks=artifact.blocks
                ),
                _LabelSelector(seed) if args.pdf_selector == "labels" else pdf_guard,
                model,
                link_repository,
            )
        pdfs = []
        for name, label in spec["pdfs"].items():
            selected = pdf_selected.get(name)
            if selected is None:
                verdict = "not linked"
            elif label in {"current_product", "shared_terms"}:
                verdict = None if selected else "lost"
            elif label in {"related_product", "irrelevant"}:
                verdict = "leak" if selected else None
            else:
                verdict = None
            pdfs.append(
                {"file": name, "label": label, "selected": selected, "failure": verdict}
            )
        seeds[seed] = {
            "counts": counts,
            "tables": tables,
            "pdfs": pdfs,
            "failures": failures,
            "llm_batches": (
                result.llm_batch_count
                if result is not None and result is not True
                else None
            ),
            # Every block and table assessment, so the run can be re-scored
            # against changed labels with `--rescore`, without Gemini.
            "assessments": {
                item_id: assessment.model_dump(mode="json")
                for item_id, assessment in by_item.items()
            },
        }
        for key in ("lost", "leak", "noise", "stale", "scored"):
            totals[key] += counts[key]
        totals["tables_scored"] += sum(
            1 for t in tables if t["expected"] != "unlabelled"
        )
        print(
            f"{seed:32} scored={counts['scored']:3} lost={counts['lost']:3} "
            f"leak={counts['leak']:3} noise={counts['noise']:3} "
            f"tables={[(t['expected'][:3], t['outcome']) for t in tables]} "
            f"pdf_failures={[p['file'] for p in pdfs if p['failure'] not in (None, 'not linked')]}"
        )

    rerun = None
    if args.repeat > 1 and guard is not None and stored is None:
        # The same pass again with the same caches: nothing should reach Gemini.
        calls_before = guard.calls
        pdf_calls_before = pdf_guard.calls if pdf_guard is not None else 0
        reused = 0
        for seed, (artifact, bundle) in bundles.items():
            entry = catalog[seed]
            service = SourceDiscoveryService(
                guard, discovery_repository, discovery_settings, model_name=model
            )
            again = await _discover(service, bundle, entry)
            reused += again.reused_assessment_count
            if pdf_guard is not None:
                from app.domain.source_discovery import OfferingContext

                await _selection_decisions(
                    artifact,
                    _rebuilt_documents(artifact, parser),
                    OfferingContext.from_catalog_entry(
                        entry, page_title=artifact.title, page_blocks=artifact.blocks
                    ),
                    pdf_guard,
                    model,
                    link_repository,
                )
        rerun = {
            "discovery_calls": guard.calls - calls_before,
            "pdf_selector_calls": (
                pdf_guard.calls - pdf_calls_before if pdf_guard is not None else None
            ),
            "reused_assessments": reused,
        }
        print("cache re-run:", rerun)

    pdf_totals = {"lost": 0, "leak": 0}
    for value in seeds.values():
        for pdf in value["pdfs"]:
            if pdf["failure"] in pdf_totals:
                pdf_totals[pdf["failure"]] += 1
    report: dict[str, Any] = {
        "as_of": LABELS["as_of"],
        "classifier": args.classifier,
        "model": model,
        "estimated_usd": round(estimate, 4),
        "totals": totals,
        "pdf_totals": pdf_totals,
        "cache_rerun": rerun,
        "seeds": seeds,
    }
    if stored is not None:
        report["rescored_from"] = args.rescore
        report["usage"] = stored.get("usage")
        report["classifier"] = stored.get("classifier")
    if guard is not None and stored is None:
        usage = guard.inner.usage
        report["usage"] = {
            "calls": guard.calls,
            "request_attempts": usage.request_attempts,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "thinking_tokens": usage.thinking_tokens,
            "spent_usd": round(guard.spent_usd(), 4),
        }
    report["pdf_selector"] = args.pdf_selector
    if pdf_guard is not None:
        usage = pdf_guard.inner.usage
        report["pdf_selector_usage"] = {
            "calls": pdf_guard.calls,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "spent_usd": round(pdf_guard.spent_usd(), 4),
        }
    print(
        "totals:",
        totals,
        "pdf:",
        pdf_totals,
        "usage:",
        report.get("usage"),
        "pdf selector:",
        report.get("pdf_selector_usage"),
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classifier", choices=("gemini", "none"), default="none")
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-usd", type=float, default=0.40)
    parser.add_argument("--label", default=None)
    parser.add_argument("--seed", action="append")
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="run discovery (and selection) again with the same caches; 2 checks reuse",
    )
    parser.add_argument(
        "--pdf-selector",
        choices=("admission", "labels", "gemini"),
        default="admission",
        help=(
            "how PDFs are chosen: today's keyword admission, the hand labels replayed "
            "through the link selector (plumbing check), or the Gemini link selector"
        ),
    )
    parser.add_argument(
        "--rescore",
        default=None,
        help="score the assessments stored in an earlier report instead of running discovery",
    )
    args = parser.parse_args()
    report = asyncio.run(run(args))
    if args.label:
        target = BASE / "data" / f"discovery-check-{args.label}.json"
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(f"written {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
