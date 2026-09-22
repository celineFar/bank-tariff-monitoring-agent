"""The deliverable demonstrations must stay wired and honestly scored."""

from __future__ import annotations

import asyncio

import pytest

from app.domain.pdf_extraction import PdfInputMode
from app.services.pdf_input_probe import probe_pdf_input
from scripts.demonstrations import Criterion, ScenarioResult, render
from scripts.demonstrations.document_processing import DIGITAL, SCANNED
from scripts.demonstrations.support import (
    DemonstrationError,
    demonstration_database_url,
)
from scripts.run_demonstration import ORDER, SCENARIOS, _run


def test_every_listed_scenario_is_runnable() -> None:
    assert set(ORDER) == set(SCENARIOS)
    assert len(ORDER) == 5
    for name in ORDER:
        runner, title = SCENARIOS[name]
        assert callable(runner)
        assert title.startswith("Deliverable ")


def test_a_scenario_with_one_failed_criterion_does_not_pass() -> None:
    result = ScenarioResult(deliverable="Deliverable 0", title="demo")
    result.check("a", "must hold", True, "held")
    result.check("b", "must hold", False, "did not hold")

    assert not result.passed
    assert "[FAIL] b" in render(result)


def test_a_scenario_with_no_criteria_does_not_pass() -> None:
    assert not ScenarioResult(deliverable="Deliverable 0", title="demo").passed


def test_render_shows_expectation_and_observation() -> None:
    result = ScenarioResult(deliverable="Deliverable 0", title="demo")
    result.step("did a thing")
    result.check("a", "must hold", True, "held")

    rendered = render(result)

    assert "did a thing" in rendered
    assert "expected: must hold" in rendered
    assert "observed: held" in rendered
    assert "RESULT: PASS (1/1 criteria)" in rendered


def test_check_coerces_truthiness_to_a_real_boolean() -> None:
    result = ScenarioResult(deliverable="Deliverable 0", title="demo")
    result.check("a", "must hold", [1], "a non-empty list")

    assert result.criteria[0].passed is True
    assert isinstance(
        Criterion(name="a", expectation="b", passed=True, observed="c").passed, bool
    )


def test_committed_scanned_fixture_has_an_image_and_no_text_layer() -> None:
    """The fixture ships in the repository, so a clean clone can run deliverable 11."""
    assert SCANNED.exists()
    probe = probe_pdf_input(SCANNED.read_bytes())

    assert probe.page_count == 1
    assert probe.document_mode is PdfInputMode.IMAGE_ONLY
    assert probe.pages[0].native_text_characters == 0
    assert probe.pages[0].images_detected


def test_committed_digital_fixture_has_a_text_layer() -> None:
    assert DIGITAL.exists()
    probe = probe_pdf_input(DIGITAL.read_bytes())

    assert probe.document_mode in (PdfInputMode.MACHINE_READABLE, PdfInputMode.MIXED)
    assert probe.pages[0].native_text_characters > 0


def test_demonstrations_refuse_a_database_that_is_not_disposable(monkeypatch) -> None:
    monkeypatch.setenv(
        "TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/tariff_monitor"
    )

    with pytest.raises(DemonstrationError, match="_test"):
        demonstration_database_url()

    monkeypatch.delenv("TEST_DATABASE_URL")
    with pytest.raises(DemonstrationError, match="TEST_DATABASE_URL"):
        demonstration_database_url()


def test_each_invocation_writes_a_new_run_directory(tmp_path, monkeypatch) -> None:
    """An invocation must never overwrite the transcripts of an earlier one."""
    result = ScenarioResult(deliverable="Deliverable 0", title="demo")
    result.check("a", "must hold", True, "held")

    async def runner() -> ScenarioResult:
        return result

    monkeypatch.setitem(SCENARIOS, "hitl", (runner, "Deliverable 0 — demo"))
    root = tmp_path / "demonstrations"
    asyncio.run(_run(["hitl"], root))
    asyncio.run(_run(["hitl"], root))

    assert (root / "run_001" / "hitl.md").is_file()
    assert (root / "run_002" / "hitl.md").is_file()


def test_no_audit_writes_no_transcript_directory(tmp_path, monkeypatch) -> None:
    result = ScenarioResult(deliverable="Deliverable 0", title="demo")
    result.check("a", "must hold", True, "held")

    async def runner() -> ScenarioResult:
        return result

    monkeypatch.setitem(SCENARIOS, "hitl", (runner, "Deliverable 0 — demo"))
    monkeypatch.chdir(tmp_path)
    asyncio.run(_run(["hitl"], None))

    assert list(tmp_path.iterdir()) == []
