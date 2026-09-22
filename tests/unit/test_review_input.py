"""A reviewer types plain answers, and every field says what a valid one is."""

from __future__ import annotations

import pytest

from app.domain.semantic_extraction import ExtractionField
from app.services.review_input import (
    ReviewInputError,
    parse_review_field_text,
    review_field_format,
)
from app.services.semantic_extraction import validate_review_field_value


def test_every_extraction_field_states_an_entry_format() -> None:
    for field in ExtractionField:
        field_format = review_field_format(field)
        assert field_format.instruction
        assert field_format.examples
        for example in field_format.examples:
            parse_review_field_text(field, example, excerpts=(example,))


@pytest.mark.parametrize(
    ("field", "text", "expected"),
    [
        (
            ExtractionField.REPAYMENT,
            "Interest is repaid monthly and the utilized amount at the end of the term",
            [
                {
                    "value": {
                        "method": "Interest is repaid monthly and the utilized "
                        "amount at the end of the term"
                    },
                    "conditions": [],
                }
            ],
        ),
        (
            ExtractionField.REPAYMENT,
            "Annuity; differentiated",
            [
                {"value": {"method": "Annuity"}, "conditions": []},
                {"value": {"method": "differentiated"}, "conditions": []},
            ],
        ),
        (ExtractionField.PRODUCT_NAME, "Overdrafts", "Overdrafts"),
        (
            ExtractionField.LOAN_AMOUNT,
            "AMD 100,000-100,000,000",
            [
                {
                    "value": {
                        "type": "absolute",
                        "range": {
                            "min": 100000,
                            "max": 100000000,
                            "currency": "AMD",
                        },
                    },
                    "conditions": [],
                }
            ],
        ),
        (
            ExtractionField.LOAN_AMOUNT,
            "up to AMD 15 million",
            [
                {
                    "value": {
                        "type": "absolute",
                        "range": {"max": 15000000, "currency": "AMD"},
                    },
                    "conditions": [],
                }
            ],
        ),
        (
            ExtractionField.INTEREST_RATE,
            "15-21%",
            [
                {
                    "value": {
                        "min": 15,
                        "max": 21,
                        "rate_type": "unknown",
                        "basis": "annual",
                    },
                    "conditions": [],
                }
            ],
        ),
        (
            ExtractionField.EFFECTIVE_RATE,
            "16.06-23.13%",
            [
                {
                    "value": {
                        "min": 16.06,
                        "max": 23.13,
                        "rate_type": "unknown",
                        "basis": "annual",
                    },
                    "conditions": [],
                }
            ],
        ),
        (
            ExtractionField.TERM,
            "up to 5 years",
            [{"value": {"max_months": 60}, "conditions": []}],
        ),
        (
            ExtractionField.FEES,
            "Change of the loan repayment date: AMD 10,000",
            [
                {
                    "description": "Change of the loan repayment date",
                    "scope": "product",
                    "amount": 10000,
                    "currency": "AMD",
                    "conditions": [],
                }
            ],
        ),
        (ExtractionField.FEES, "none", []),
        (
            ExtractionField.REQUIRED_DOCUMENTS,
            "Passport; Income statement upon request",
            [
                {
                    "value": {"name": "Passport", "requirement": "required"},
                    "conditions": [],
                },
                {
                    "value": {
                        "name": "Income statement upon request",
                        "requirement": "upon_request",
                    },
                    "conditions": [],
                },
            ],
        ),
        (
            ExtractionField.AGE_REQUIREMENTS,
            "18-65",
            [{"value": {"min_age": 18, "max_age": 65}, "conditions": []}],
        ),
        (ExtractionField.GRACE_PERIOD_DAYS, "55 days", 55),
        (ExtractionField.REVOLVING, "yes", True),
        (
            ExtractionField.INCOME_VERIFICATION_REQUIRED,
            "not required",
            {"default_required": False, "exceptions": []},
        ),
    ],
)
def test_plain_entry_reaches_the_field_contract(
    field: ExtractionField, text: str, expected: object
) -> None:
    value = parse_review_field_text(field, text)

    assert value == expected
    validate_review_field_value(field, value)


def test_entry_that_cannot_be_read_repeats_the_accepted_format() -> None:
    with pytest.raises(ReviewInputError) as error:
        parse_review_field_text(ExtractionField.INTEREST_RATE, "quite high")

    message = str(error.value)
    assert "15-21%" in message
    assert error.value.field_format is review_field_format(
        ExtractionField.INTEREST_RATE
    )


def test_percentage_entry_is_kept_in_percentage_points() -> None:
    # The model-output heuristic reads 0 < x < 1 as a fraction; a reviewer who
    # types 0.5% means half a percentage point.
    assert parse_review_field_text(ExtractionField.DOWN_PAYMENT_PCT, "0.5%") == [
        {"value": 0.5, "conditions": []}
    ]


def test_open_ended_term_still_needs_a_passage_stating_its_end() -> None:
    supported = parse_review_field_text(
        ExtractionField.TERM,
        "Indefinite term",
        excerpts=("Term (months): Indefinite term (until requested back)",),
    )

    assert supported == [
        {"value": {"indefinite": True, "end_condition": "on_demand"}, "conditions": []}
    ]
    with pytest.raises(ReviewInputError, match="must state the end condition"):
        parse_review_field_text(
            ExtractionField.TERM,
            "Indefinite term",
            excerpts=("An indefinite term applies",),
        )


def test_structured_json_entry_is_still_accepted() -> None:
    assert parse_review_field_text(
        ExtractionField.REPAYMENT,
        '[{"value": {"method": "Annuity"}, "conditions": []}]',
    ) == [{"value": {"method": "Annuity"}, "conditions": []}]

    with pytest.raises(ReviewInputError, match="not valid JSON"):
        parse_review_field_text(ExtractionField.REPAYMENT, '[{"value": ')


def test_review_values_stay_json_native() -> None:
    import json

    for field, text in (
        (ExtractionField.INTEREST_RATE, "16.06%"),
        (ExtractionField.LOAN_AMOUNT, "AMD 100,000-10,000,000"),
        (ExtractionField.CREDIT_LIMIT, "up to AMD 15 million"),
        (ExtractionField.FEES, "Disbursement fee: AMD 75,000"),
    ):
        # A decision travels as JSON, so a Decimal here would break the resume.
        json.dumps(parse_review_field_text(field, text))
