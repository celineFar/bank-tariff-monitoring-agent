import pytest

from app.domain.structured_tariffs import FieldPath, fee_field_path, field_label


@pytest.mark.parametrize(
    "description",
    [
        "Early repayment fee",
        "Fee for early repayment of the loan",
        "Prepayment penalty: 1% of the repaid amount",
        "Վաղաժամկետ մարման վճար",
    ],
)
def test_early_repayment_wordings_are_one_field(description) -> None:
    assert fee_field_path(description) is FieldPath.FEE_EARLY_REPAYMENT


def test_other_fees_are_unchanged() -> None:
    assert fee_field_path("Loan disbursement fee") is FieldPath.FEE_DISBURSEMENT
    assert fee_field_path("Monthly service fee") is FieldPath.FEE_SERVICE


def test_label_rename() -> None:
    assert (
        field_label(FieldPath.FEE_EARLY_REPAYMENT)
        == "early repayment fee (prepayment penalty)"
    )
