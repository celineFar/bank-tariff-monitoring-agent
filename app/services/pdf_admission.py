from __future__ import annotations

import re
from datetime import date
from urllib.parse import unquote, urlsplit

from app.domain.acquisition import DocumentArtifact
from app.domain.pdf_extraction import (
    PdfAdmission,
    PdfAdmissionRelevance,
    PdfAdmissionRole,
    PdfEffectivePeriod,
    PdfTemporalStatus,
)

_RELEVANT_TERMS = (
    "loan",
    "mortgage",
    "credit",
    "overdraft",
    "tariff",
    "fee",
    "interest rate",
    "lending",
    "collateral",
    "վարկ",
    "հիփոթեք",
)
_HISTORICAL_TERMS = (
    "previous terms",
    "previous loan",
    "archive",
    "expired",
    "historical",
    "/previous-loans/",
    "/archive/",
)
_FEE_TERMS = ("fee", "tariff", "commission", "վճար")
_LEGAL_TERMS = ("procedure", "regulation", "disclosure", "agreement")
_DATE = r"(?P<{name}>\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}})"
_RANGE_RE = re.compile(
    rf"(?:from\s+)?{_DATE.format(name='start')}\s*(?:to|until|[-\u2013\u2014])\s*"
    rf"{_DATE.format(name='end')}",
    re.IGNORECASE,
)


def assess_pdf_metadata(
    document: DocumentArtifact, *, as_of: date
) -> PdfAdmission:
    metadata = " ".join(
        (
            document.document_name,
            document.link_text,
            document.link_title or "",
            " ".join(document.origin_heading_path),
            document.nearby_text,
            unquote(urlsplit(str(document.final_url)).path),
        )
    )
    folded = metadata.casefold()
    relevant_matches = tuple(term for term in _RELEVANT_TERMS if term in folded)
    historical_matches = tuple(term for term in _HISTORICAL_TERMS if term in folded)
    periods = _effective_periods(metadata)
    temporal = _temporal_status(periods, historical_matches, as_of)

    basis: list[str] = []
    if relevant_matches:
        basis.append("relevant metadata: " + ", ".join(relevant_matches[:6]))
    if historical_matches:
        basis.append("historical metadata: " + ", ".join(historical_matches[:4]))
    if periods:
        basis.append("explicit effective period in link context")
    if document.origin_heading_path:
        basis.append(
            "origin heading: " + " > ".join(document.origin_heading_path)
        )

    relevance = (
        PdfAdmissionRelevance.RELEVANT
        if relevant_matches
        else PdfAdmissionRelevance.AMBIGUOUS
    )
    role = PdfAdmissionRole.PRODUCT_TERMS
    if any(term in folded for term in _FEE_TERMS):
        role = PdfAdmissionRole.FEES
    elif any(term in folded for term in _LEGAL_TERMS):
        role = PdfAdmissionRole.LEGAL_DISCLOSURE
    elif relevance is PdfAdmissionRelevance.AMBIGUOUS:
        role = PdfAdmissionRole.OTHER

    reason = (
        "PDF was admitted from product-relevant link metadata; content discovery is unnecessary."
        if relevance is PdfAdmissionRelevance.RELEVANT
        else "PDF metadata is inconclusive; extracted content still requires source discovery."
    )
    return PdfAdmission(
        relevance=relevance,
        role=role,
        temporal_status=temporal,
        decision_basis=tuple(basis),
        reason=reason,
        effective_periods=periods,
    )


def _effective_periods(value: str) -> tuple[PdfEffectivePeriod, ...]:
    periods: list[PdfEffectivePeriod] = []
    for match in _RANGE_RE.finditer(value):
        start = _parse_date(match.group("start"))
        end = _parse_date(match.group("end"))
        if start is None or end is None or end < start:
            continue
        periods.append(
            PdfEffectivePeriod(raw=match.group(0), start=start, end=end)
        )
    return tuple(periods)


def _parse_date(value: str) -> date | None:
    parts = re.split(r"[./-]", value)
    if len(parts) != 3:
        return None
    day, month, year = (int(part) for part in parts)
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _temporal_status(
    periods: tuple[PdfEffectivePeriod, ...],
    historical_matches: tuple[str, ...],
    as_of: date,
) -> PdfTemporalStatus:
    if periods:
        if any(
            period.start is not None
            and period.end is not None
            and period.start <= as_of <= period.end
            for period in periods
        ):
            return PdfTemporalStatus.CURRENT
        if all(period.end is not None and period.end < as_of for period in periods):
            return PdfTemporalStatus.HISTORICAL
        if all(period.start is not None and period.start > as_of for period in periods):
            return PdfTemporalStatus.FUTURE
        return PdfTemporalStatus.TIME_BOUNDED
    if historical_matches:
        return PdfTemporalStatus.HISTORICAL
    return PdfTemporalStatus.UNKNOWN
