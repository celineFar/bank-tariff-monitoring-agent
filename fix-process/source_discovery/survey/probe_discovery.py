"""Measure today's source discovery on the captured seeds, without Gemini.

    uv run python fix-process/source_discovery/survey/probe_discovery.py

Reads the normalization survey's captures (`fix-process/normalization/.cache`),
normalizes each page without PDFs, builds discovery candidates, and reports:

1. per seed: candidates, rule decisions, Gemini items, batches, items cut to the
   per-item budget, the navigation group, Gemini items with any site-chrome
   member, and structural fingerprints shared by several candidates;
2. per admitted PDF link: the admission result and whether discovery would send
   it to Gemini or decide it by rule, against the hand labels;
3. for four seeds: how many % values in each current PDF also appear on the page.

The output before any fix is in `data/probe-output-before.txt`.
"""

from __future__ import annotations

import asyncio
import collections
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.domain.acquisition import PageArtifact  # noqa: E402
from app.domain.models import ProductType  # noqa: E402
from app.services.acquisition import AcquisitionService  # noqa: E402
from app.services.discovery_prefilter import build_discovery_candidates  # noqa: E402
from app.services.html_parser import HtmlArtifactParser  # noqa: E402
from app.services.normalization import StructuralNormalizationService  # noqa: E402
from app.services.pdf_admission import assess_pdf_metadata  # noqa: E402
from app.services.source_discovery import (  # noqa: E402
    _build_batches,
    _rule_assessment,
)

# The last live capture of the normalization fix: its stored blocks match this
# branch's parser. `SURVEY_CACHE` picks another capture folder.
CACHE = Path(
    os.environ.get("SURVEY_CACHE", ROOT / "fix-process/normalization/.cache-live-2")
)
LABELS = json.loads(
    (ROOT / "fix-process/normalization/data/seed-pdf-labels.json").read_text()
)
AS_OF = date.fromisoformat(LABELS["as_of"])
PERCENT = re.compile(r"\d+(?:[.,]\d+)?\s*%")
OVERLAP_SEEDS = (
    "consumer_standard",
    "mortgage_primary",
    "overdraft",
    "mortgage_express",
)


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


def _artifacts():
    parser = HtmlArtifactParser(load_settings().http.allowed_source_hosts)
    for path in sorted(CACHE.glob("*.artifact.json")):
        yield (
            path.name.removesuffix(".artifact.json"),
            reparsed(PageArtifact.model_validate_json(path.read_text()), parser),
        )


async def _page_bundle(artifact: PageArtifact):
    page_only = artifact.model_copy(update={"downloadable_documents": ()})
    service = StructuralNormalizationService(artifact_reader=None, pdf_extractor=None)
    return await service.normalize(page_only)


async def candidates_report(parser: HtmlArtifactParser) -> None:
    settings = load_settings().source_discovery
    print("== 1. Candidates per seed (page only) ==")
    for seed, artifact in _artifacts():
        parsed = parser.parse(
            artifact.rendered_html or "", source_url=str(artifact.final_url)
        )
        bundle = await _page_bundle(artifact)
        candidates = build_discovery_candidates(bundle)
        rules = [c for c in candidates if _rule_assessment(c)]
        llm = [c for c in candidates if not _rule_assessment(c)]
        batches = _build_batches(ProductType.MORTGAGE, llm, {}, settings)
        cut = [c for c in llm if len(c.context_text) > settings.max_chars_per_item]
        nav = [
            c
            for c in candidates
            if c.title == "Unheaded page content" and len(c.member_source_ids) > 1
        ]
        chrome = [
            c
            for c in llm
            if any(m.split("::")[-1] in parsed.chrome_ids for m in c.member_source_ids)
        ]
        shared = collections.Counter(c.structural_fingerprint for c in candidates)
        shared_groups = [
            (n, next(c.title for c in candidates if c.structural_fingerprint == fp))
            for fp, n in shared.items()
            if n > 1
        ]
        print(f"    shared_structural_groups={len(shared_groups)}")
        print(
            f"{seed:32} candidates={len(candidates):3} rule={len(rules):2} "
            f"gemini={len(llm):3} batches={len(batches)} "
            f"cut>{settings.max_chars_per_item}={len(cut)} "
            f"nav_group={[len(c.member_source_ids) for c in nav]} "
            f"nav_rule={[bool(_rule_assessment(c)) for c in nav]} "
            f"gemini_items_with_chrome={len(chrome)}"
        )
        for c in cut:
            print(
                f"    cut: {c.scope.value:7} {len(c.context_text):6} chars  {c.title[:60]}"
            )
        for n, title in shared_groups:
            print(f"    shared structural fingerprint x{n}: {title[:60]}")


def pdf_report(parser: HtmlArtifactParser) -> None:
    print("\n== 2. Admitted PDF links: who decides ==")
    tally: collections.Counter[tuple[str, str]] = collections.Counter()
    for seed, artifact in _artifacts():
        parsed = parser.parse(
            artifact.rendered_html or "", source_url=str(artifact.final_url)
        )
        for document in artifact.downloadable_documents:
            origin = (
                AcquisitionService._document_origin(parsed, document.link_id)
                if document.link_id
                else {}
            )
            rebuilt = document.model_copy(
                update={
                    "origin_block_id": None,
                    "origin_heading_path": (),
                    "nearby_text": "",
                    **origin,
                }
            )
            admission = assess_pdf_metadata(rebuilt, as_of=AS_OF)
            if admission.temporal_status.value == "historical":
                continue  # skipped before transcription
            if admission.relevance.value == "irrelevant":
                route = "skipped"
            elif admission.relevance.value == "relevant":
                route = "rule"
            else:
                route = "gemini"
            label = LABELS["pdfs"].get(document.sha256, {})
            tally[(label.get("label", "?"), route)] += 1
            print(
                f"{seed:32} {label.get('label', '?'):10} "
                f"{admission.relevance.value:9} {admission.role.value:16} "
                f"{route:7} {label.get('file', '')}"
            )
    print("tally (label, route):", dict(tally))


async def overlap_report() -> None:
    print("\n== 3. % values in current PDFs that also appear on the page ==")
    try:
        import pypdf
    except ImportError:
        print("pypdf not installed; skipped")
        return
    pdfs = {
        hashlib.sha256(p.read_bytes()).hexdigest(): p
        for p in (CACHE / "pdfs").rglob("*")
        if p.is_file()
    }
    for seed, artifact in _artifacts():
        if seed not in OVERLAP_SEEDS:
            continue
        page = (await _page_bundle(artifact)).documents[0]
        html = " ".join(
            [b.text for b in page.blocks]
            + [c.text for t in page.tables for r in t.rows for c in r.cells]
        )
        on_page = {v.replace(" ", "") for v in PERCENT.findall(html)}
        print(f"{seed}: {len(on_page)} distinct % values on the page")
        for document in artifact.downloadable_documents:
            label = LABELS["pdfs"].get(document.sha256, {})
            if label.get("label") != "current" or document.sha256 not in pdfs:
                continue
            text = " ".join(
                page_.extract_text() or ""
                for page_ in pypdf.PdfReader(str(pdfs[document.sha256])).pages
            )
            in_pdf = {v.replace(" ", "") for v in PERCENT.findall(text)}
            print(
                f"    {label['file'][:48]:48} pdf={len(in_pdf):3} "
                f"also_on_page={len(in_pdf & on_page):3} pdf_only={len(in_pdf - on_page):3}"
            )


async def main() -> None:
    parser = HtmlArtifactParser(load_settings().http.allowed_source_hosts)
    await candidates_report(parser)
    pdf_report(parser)
    await overlap_report()


if __name__ == "__main__":
    asyncio.run(main())
