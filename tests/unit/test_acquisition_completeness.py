from datetime import UTC, datetime

import pytest

from app.config import AcquisitionSettings
from app.domain.acquisition import AcquisitionInventory, AcquisitionMode, PageArtifact
from app.domain.monitoring import SourceFailureCode
from app.services.acquisition_completeness import (
    CompletenessGatedAcquisitionService,
    compare_inventory,
)
from app.services.acquisition_errors import AcquisitionError, AcquisitionFailure
from app.services.failure_mapping import source_failure_code

URL = "https://ameriabank.am/en/personal/loans/consumer-loans/overdraft"
NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
SETTINGS = AcquisitionSettings()

# The Overdraft page as measured live on 2026-09-26.
OVERDRAFT = AcquisitionInventory(main_chars=13_136, tables=3, pdf_links=10)


def _inventory(**changes) -> AcquisitionInventory:
    return OVERDRAFT.model_copy(update=changes)


def test_an_unchanged_page_passes() -> None:
    assert compare_inventory(OVERDRAFT, OVERDRAFT, SETTINGS) == ()


def test_growth_passes() -> None:
    grown = _inventory(pdf_links=17, main_chars=20_000, tables=4)

    assert compare_inventory(OVERDRAFT, grown, SETTINGS) == ()


def test_small_shrinkage_passes() -> None:
    edited = _inventory(pdf_links=9, main_chars=11_000)

    assert compare_inventory(OVERDRAFT, edited, SETTINGS) == ()


def test_tables_disappearing_fails() -> None:
    assert compare_inventory(OVERDRAFT, _inventory(tables=0), SETTINGS) == (
        "tables 3 -> 0",
    )


def test_a_baseline_stored_with_a_payload_count_still_loads_and_ignores_it() -> None:
    # Baselines written before payload capture was removed carry a "payloads"
    # count; it is ignored, so no page fails "payloads 17 -> 0".
    stored = AcquisitionInventory.model_validate(
        {"main_chars": 13_136, "tables": 3, "pdf_links": 10, "payloads": 17}
    )

    assert compare_inventory(stored, OVERDRAFT, SETTINGS) == ()


def test_losing_half_the_pdf_links_fails() -> None:
    baseline = _inventory(pdf_links=16)

    assert compare_inventory(baseline, _inventory(pdf_links=7), SETTINGS) == (
        "pdf_links 16 -> 7 (-56%)",
    )


def test_pdf_links_falling_to_zero_is_reported_once() -> None:
    assert compare_inventory(OVERDRAFT, _inventory(pdf_links=0), SETTINGS) == (
        "pdf_links 10 -> 0",
    )


def test_losing_most_main_content_fails() -> None:
    reasons = compare_inventory(OVERDRAFT, _inventory(main_chars=4_000), SETTINGS)

    assert reasons == ("main_chars 13136 -> 4000 (-70%)",)


def test_a_structure_the_page_never_had_is_not_required() -> None:
    campaign = AcquisitionInventory(main_chars=3_294, tables=0, pdf_links=0)

    assert compare_inventory(campaign, campaign, SETTINGS) == ()


class _Acquisition:
    def __init__(self, inventory: AcquisitionInventory) -> None:
        self.inventory = inventory

    async def acquire(self, url: str) -> PageArtifact:
        return PageArtifact(
            url=url,
            canonical_url=url,
            final_url=url,
            acquisition_mode=AcquisitionMode.BROWSER,
            raw_html="<html></html>",
            rendered_html=None,
            markdown=None,
            blocks=(),
            tables=(),
            links=(),
            downloadable_documents=(),
            inventory=self.inventory,
            retrieved_at=NOW,
            content_hash="a" * 64,
            page_content_hash="b" * 64,
        )


class _Baselines:
    def __init__(self, stored: AcquisitionInventory | None = None) -> None:
        self.stored = stored
        self.recorded: list[AcquisitionInventory] = []

    async def get(self, url: str) -> AcquisitionInventory | None:
        return self.stored

    async def record(self, url, inventory, *, recorded_at) -> None:
        self.recorded.append(inventory)
        self.stored = inventory


@pytest.mark.asyncio
async def test_a_first_passing_acquisition_becomes_the_baseline() -> None:
    baselines = _Baselines()

    await CompletenessGatedAcquisitionService(
        _Acquisition(OVERDRAFT), baselines, SETTINGS
    ).acquire(URL)

    assert baselines.recorded == [OVERDRAFT]


@pytest.mark.asyncio
async def test_a_passing_acquisition_moves_the_baseline_forward() -> None:
    grown = _inventory(pdf_links=12)
    baselines = _Baselines(OVERDRAFT)

    await CompletenessGatedAcquisitionService(
        _Acquisition(grown), baselines, SETTINGS
    ).acquire(URL)

    assert baselines.stored == grown


@pytest.mark.asyncio
async def test_a_sharp_drop_fails_and_leaves_the_baseline_alone() -> None:
    baselines = _Baselines(OVERDRAFT)
    gate = CompletenessGatedAcquisitionService(
        _Acquisition(_inventory(tables=0, pdf_links=0)), baselines, SETTINGS
    )

    with pytest.raises(AcquisitionError) as caught:
        await gate.acquire(URL)

    assert caught.value.reason is AcquisitionFailure.INCOMPLETE_CONTENT
    assert caught.value.reasons == ("tables 3 -> 0", "pdf_links 10 -> 0")
    assert "reset_acquisition_baseline" in str(caught.value)
    assert (
        source_failure_code(caught.value, stage="acquisition")
        is SourceFailureCode.INCOMPLETE_CONTENT
    )
    assert baselines.stored == OVERDRAFT
    assert baselines.recorded == []


@pytest.mark.asyncio
async def test_the_drop_keeps_failing_until_the_baseline_is_reset() -> None:
    redesigned = _inventory(tables=0)
    baselines = _Baselines(OVERDRAFT)
    gate = CompletenessGatedAcquisitionService(
        _Acquisition(redesigned), baselines, SETTINGS
    )

    for _ in range(3):
        with pytest.raises(AcquisitionError):
            await gate.acquire(URL)

    baselines.stored = None  # what the reset script leaves behind
    await gate.acquire(URL)

    assert baselines.stored == redesigned


@pytest.mark.asyncio
async def test_a_failing_baseline_write_does_not_fail_a_passing_acquisition() -> None:
    class _Broken(_Baselines):
        async def record(self, url, inventory, *, recorded_at) -> None:
            raise RuntimeError("database is unreachable")

    artifact = await CompletenessGatedAcquisitionService(
        _Acquisition(OVERDRAFT), _Broken(), SETTINGS
    ).acquire(URL)

    assert artifact.inventory == OVERDRAFT
