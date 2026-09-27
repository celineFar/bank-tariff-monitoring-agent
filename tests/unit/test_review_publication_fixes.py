"""Regression cases from the end-to-end review (fix/review-and-publication).

Each test names the review finding it covers: P1 quotes, P2 waiting reviews,
P3 reject_all scope, P4 orphaned reviews, P5 vanished answers, P6 nested
history fields, P7 transient linked-document failures.
"""

from __future__ import annotations

import hashlib

import pytest

from app.domain.acquisition import SourceLocator, SourceType
from app.domain.models import ProductType
from app.domain.semantic_extraction import (
    EvidenceItem,
    ExtractionField,
    ExtractionStatus,
    ModelCitation,
    ModelFieldResult,
)
from app.domain.source_discovery import (
    Authority,
    InformationRole,
    ProductAssociation,
    TemporalStatus,
)
from app.services.semantic_extraction import _validate_field_result, source_span
from app.services.structured_projection import StructuredTariffProjector

# --- P1: the stored quote is the source's own text --------------------------------

_ROW = "3. Loan terms > 3.4. Nominal annual interest rate:\n  Currency: AMD → 13.5% (Fixed)"


@pytest.mark.parametrize(
    ("quote", "expected"),
    [
        ("Currency: AMD → 13.5%", "Currency: AMD → 13.5%"),
        (
            "Nominal annual interest rate: Currency: AMD → 13.5%",
            "Nominal annual interest rate:\n  Currency: AMD → 13.5%",
        ),
        ("NOMINAL annual  interest", "Nominal annual interest"),
        ("not in the row", "not in the row"),
    ],
)
def test_p1_source_span_returns_the_matching_source_text(quote, expected) -> None:
    assert source_span(quote, _ROW) == expected


def test_p1_source_span_handles_expanding_case_folds() -> None:
    assert source_span("strasse 5", "Adresse: Straße 5, Yerevan") == "Straße 5"


def _row_evidence() -> EvidenceItem:
    return EvidenceItem(
        evidence_id="ev_" + hashlib.sha256(b"row").hexdigest()[:24],
        document_id="page:abc",
        source_item_id="t1:row:3",
        content=_ROW,
        role=InformationRole.PRICING,
        authority=Authority.OFFICIAL_PRODUCT_CONTENT,
        temporal_status=TemporalStatus.CURRENT,
        precedence=2,
        product_association=ProductAssociation.CURRENT_PRODUCT,
        locator=SourceLocator(
            source_url="https://ameriabank.am/en/personal/loans/consumer-loans/consumer-loans",
            source_type=SourceType.PAGE,
            block_id="t1",
        ),
    )


def test_p1_a_line_joined_quote_is_accepted_and_publishable() -> None:
    item = _row_evidence()
    catalog = {item.evidence_id: item}
    result = ModelFieldResult(
        field=ExtractionField.INTEREST_RATE,
        status=ExtractionStatus.FOUND,
        value_json=(
            '[{"value":{"min":13.5,"max":13.5,"rate_type":"fixed","basis":"annual"},'
            '"conditions":[{"dimension":"currency","value":"AMD"}]}]'
        ),
        evidence=(
            ModelCitation(
                evidence_id=item.evidence_id,
                quote="Nominal annual interest rate: Currency: AMD → 13.5%",
            ),
        ),
    )

    validated = _validate_field_result(
        result, catalog, product=ProductType.CONSUMER_LOAN, batch_id="b1"
    )
    verified = StructuredTariffProjector._evidence(validated.evidence, catalog)

    assert validated.evidence[0].quote in _ROW
    assert len(verified) == 1
