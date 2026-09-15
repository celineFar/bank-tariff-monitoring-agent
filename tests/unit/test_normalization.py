import pytest

from app.domain.normalization import normalize_money_text, normalize_percentage


def test_money_grouping_is_canonical() -> None:
    assert normalize_money_text("10 000 000 amd") == "10000000 AMD"
    assert normalize_money_text("10,000,000 AMD") == "10000000 AMD"


def test_percentage_is_canonical() -> None:
    assert normalize_percentage("13,50 %") == "13.5%"


def test_invalid_percentage_fails() -> None:
    with pytest.raises(ValueError):
        normalize_percentage("unknown")
