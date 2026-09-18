from datetime import date

import pytest

from app.services.model_pricing import get_model_price
from scripts.demonstrate_source_discovery import _next_run_directory


def test_model_price_catalog_selects_effective_period() -> None:
    introductory = get_model_price(
        "gemini-3.7-flash", on_date=date(2026, 9, 18)
    )
    standard = get_model_price("gemini-3.7-flash", on_date=date(2027, 1, 1))

    assert introductory.input_per_million_tokens_usd == 0.75
    assert introductory.output_per_million_tokens_usd == 3.75
    assert standard.input_per_million_tokens_usd == 1.50
    assert standard.output_per_million_tokens_usd == 7.50


def test_unknown_model_price_fails_explicitly() -> None:
    with pytest.raises(ValueError, match="No Gemini Developer API price"):
        get_model_price("unknown-model", on_date=date(2026, 9, 18))


def test_live_run_directories_increment_without_overwriting(tmp_path) -> None:
    first = _next_run_directory(tmp_path)
    marker = first / "keep.txt"
    marker.write_text("preserve", encoding="utf-8")
    second = _next_run_directory(tmp_path)

    assert first.name == "llm_run_000"
    assert second.name == "llm_run_001"
    assert marker.read_text(encoding="utf-8") == "preserve"
