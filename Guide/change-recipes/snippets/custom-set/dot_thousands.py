from decimal import Decimal

import pytest

from app.domain.normalization import normalize_money_text, strip_dot_thousands
from app.services.review_input import _parse_amounts
from app.services.scalar_normalizer import extract_scalar_candidates


@pytest.mark.parametrize("text", ["10.000.000 AMD", "10 000 000 AMD", "10,000,000 AMD"])
def test_every_grouping_is_the_same_money(text) -> None:
    assert normalize_money_text(text) == "10000000 AMD"


def test_single_dot_group_is_thousands_only_for_money() -> None:
    assert strip_dot_thousands("500.000", money=True) == "500000"
    assert strip_dot_thousands("rate 1.500") == "rate 1.500"
    assert strip_dot_thousands("12.5% and 3.25") == "12.5% and 3.25"


def test_scalar_scanner_reads_ten_million() -> None:
    (scalar,) = extract_scalar_candidates("10.000.000 AMD")
    assert scalar.value == Decimal("10000000") and scalar.unit == "AMD"


def test_scalar_scanner_reads_a_dotted_range() -> None:
    (scalar,) = extract_scalar_candidates("1.000.000 - 10.000.000 AMD")
    assert (scalar.min_value, scalar.max_value) == (
        Decimal("1000000"),
        Decimal("10000000"),
    )


def test_reviewer_can_type_dotted_amounts() -> None:
    (amount,) = _parse_amounts("AMD 500.000 - 10.000.000")
    assert amount["range"]["min"] == Decimal("500000")
    assert amount["range"]["max"] == Decimal("10000000")
