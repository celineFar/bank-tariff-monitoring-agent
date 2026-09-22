"""The deliverable demonstrations must stay wired and honestly scored."""

from __future__ import annotations

import pytest

from app.domain.pdf_extraction import PdfInputMode
from app.services.pdf_input_probe import probe_pdf_input
from scripts.demonstrations import Criterion, ScenarioResult, render
from scripts.demonstrations.document_processing import image_only_pdf
from scripts.demonstrations.support import (
    DemonstrationError,
    demonstration_database_url,
)
from scripts.run_demonstration import ORDER, SCENARIOS


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


def test_synthetic_scanned_page_has_an_image_and_no_text_layer() -> None:
    probe = probe_pdf_input(image_only_pdf())

    assert probe.page_count == 1
    assert probe.document_mode is PdfInputMode.IMAGE_ONLY
    assert probe.pages[0].native_text_characters == 0
    assert probe.pages[0].images_detected


def test_demonstrations_refuse_a_database_that_is_not_disposable(monkeypatch) -> None:
    monkeypatch.setenv(
        "TEST_DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/tariff_monitor"
    )

    with pytest.raises(DemonstrationError, match="_test"):
        demonstration_database_url()

    monkeypatch.delenv("TEST_DATABASE_URL")
    with pytest.raises(DemonstrationError, match="TEST_DATABASE_URL"):
        demonstration_database_url()
