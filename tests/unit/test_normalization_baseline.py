"""N20: the HTML page quality score, measured against the page's seed baseline."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import load_seed_catalog
from app.domain.acquisition import AcquisitionInventory, AcquisitionMode, PageArtifact
from app.domain.normalization import NormalizationWarningCode
from app.services.artifact_store import FileSystemArtifactStore
from app.services.html_parser import HtmlArtifactParser
from app.services.normalization import NoPdfExtractor, StructuralNormalizationService
from app.services.normalization_baseline import (
    NormalizationBaseline,
    load_normalization_baseline,
)

URL = "https://ameriabank.am/en/personal/loans/test"
PAGE = """
<h1>Consumer loan</h1><p>No fee for cash withdrawal</p>
<table><tr><td colspan="2">Consumer loan terms</td></tr>
<tr><td>Annual interest rate</td><td>Fixed {rate}</td></tr>
<tr><td colspan="2">USD loans</td></tr><tr><td>Fee</td><td>0%</td></tr>
<tr><td colspan="2">¹ Fixed for the first year</td></tr></table>
"""
BASELINE = NormalizationBaseline.model_validate(
    {
        "pages": [
            {
                "offering_id": "test",
                "urls": [URL],
                "recorded_on": "2026-09-26",
                "tables": [
                    {
                        "find": "Consumer loan terms",
                        "title": "Consumer loan terms",
                        "header_row": None,
                        "rows": [
                            {"label": "Annual interest rate"},
                            {"label": "Fee", "section": "USD loans"},
                        ],
                        "notes": [
                            {"marker": "1", "starts": "Fixed for the first year"}
                        ],
                    }
                ],
                "blocks": [{"text": "No fee for cash withdrawal"}],
            }
        ]
    }
)


def _artifact(body: str, url: str = URL) -> PageArtifact:
    parsed = HtmlArtifactParser(("ameriabank.am",)).parse(
        f"<html><body>{body}</body></html>", source_url=url
    )
    return PageArtifact(
        url=url,
        canonical_url=url,
        final_url=url,
        acquisition_mode=AcquisitionMode.BROWSER,
        raw_html=None,
        rendered_html="",
        markdown=None,
        blocks=parsed.blocks,
        tables=parsed.tables,
        links=parsed.links,
        downloadable_documents=(),
        retrieved_at=datetime(2026, 9, 26, tzinfo=UTC),
        inventory=AcquisitionInventory(main_chars=0, tables=1, pdf_links=0),
        content_hash="a" * 64,
        page_content_hash="b" * 64,
    )


def _service(baseline: NormalizationBaseline | None = BASELINE):
    return StructuralNormalizationService(
        artifact_reader=FileSystemArtifactStore(Path(".")),
        pdf_extractor=NoPdfExtractor(),
        baseline=baseline,
    )


@pytest.mark.asyncio
async def test_a_page_with_all_its_structure_scores_one() -> None:
    bundle = await _service().normalize(_artifact(PAGE.format(rate="20%")))
    assert bundle.documents[0].quality_score == 1.0
    assert bundle.warnings == () or all(
        w.code is not NormalizationWarningCode.BASELINE_MISMATCH
        for w in bundle.warnings
    )


@pytest.mark.asyncio
async def test_a_changed_tariff_value_is_not_a_quality_drop() -> None:
    bundle = await _service().normalize(_artifact(PAGE.format(rate="21.5%")))
    assert bundle.documents[0].quality_score == 1.0


@pytest.mark.asyncio
async def test_lost_structure_lowers_the_score_and_says_what_is_missing() -> None:
    # The section label row is gone, and so is the text block.
    damaged = (
        PAGE.format(rate="20%")
        .replace('<tr><td colspan="2">USD loans</td></tr>', "")
        .replace("<p>No fee for cash withdrawal</p>", "")
    )
    bundle = await _service().normalize(_artifact(damaged))
    document = bundle.documents[0]
    # 2 (found, header) + title + 2 rows + 1 note + 1 block = 7 checks, 2 fail.
    assert document.quality_score == round(5 / 7, 4)
    (warning,) = [
        w
        for w in bundle.warnings
        if w.code is NormalizationWarningCode.BASELINE_MISMATCH
    ]
    assert "2 of 7" in warning.message
    assert "'Fee' under 'USD loans'" in warning.message


@pytest.mark.asyncio
async def test_a_missing_table_fails_all_its_checks() -> None:
    bundle = await _service().normalize(_artifact("<p>No fee for cash withdrawal</p>"))
    assert bundle.documents[0].quality_score == round(1 / 7, 4)


@pytest.mark.asyncio
async def test_a_page_without_a_baseline_is_not_scored() -> None:
    bundle = await _service().normalize(
        _artifact(PAGE.format(rate="20%"), url="https://ameriabank.am/en/other")
    )
    assert bundle.documents[0].quality_score is None
    bundle = await _service(None).normalize(_artifact(PAGE.format(rate="20%")))
    assert bundle.documents[0].quality_score is None


def test_the_shipped_baseline_covers_every_enabled_seed() -> None:
    baseline = load_normalization_baseline()
    for entry in load_seed_catalog().offerings:
        if not entry.enabled:
            continue
        page = baseline.for_urls(str(entry.seed_url))
        assert page is not None, entry.offering_id.value
        assert page.checks > 0
    # Structure only: no block expectation quotes a figure.
    assert not any(
        any(character.isdigit() for character in block.text)
        for page in baseline.pages
        for block in page.blocks
    )
