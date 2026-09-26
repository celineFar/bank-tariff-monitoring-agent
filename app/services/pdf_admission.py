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
_IRRELEVANT_TERMS = (
    "privacy-policy",
    "privacy policy",
    "cookie",
    "terms-of-use",
    "annual-report",
    "annual report",
    "financial-statement",
    "financial statement",
    "vacancy",
    "career",
    "press-release",
    "press release",
    "branch",
    "atm",
    "sitemap",
    "contact",
)
_FEE_TERMS = ("fee", "tariff", "commission", "վճար")
_LEGAL_TERMS = ("procedure", "regulation", "disclosure", "agreement")
_DATE = r"(?P<{name}>\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}})"
_RANGE_RE = re.compile(
    rf"(?:from\s+)?{_DATE.format(name='start')}\s*"
    rf"(?:to|until|till|through|[-\u2013\u2014])\s*"
    rf"{_DATE.format(name='end')}",
    re.IGNORECASE,
)
_ARMENIAN = re.compile(r"[\u0531-\u058f]")


def _term_pattern(term: str) -> re.Pattern[str]:
    """Match a term as a word, not inside one: `atm` is not in "treatment".

    English terms may take a plural ending. Armenian terms match as word
    starts, since they inflect (`վարկ`, `վարկի`, `վարկային`). Path fragments
    (`/archive/`) carry their own boundaries.
    """
    escaped = re.escape(term)
    if _ARMENIAN.search(term):
        return re.compile(rf"(?<!\w){escaped}")
    if not term[0].isalnum():
        return re.compile(escaped)
    return re.compile(rf"(?<!\w){escaped}(?:s|es)?(?!\w)")


def _matches(terms: tuple[str, ...], folded: str) -> tuple[str, ...]:
    return tuple(term for term in terms if _PATTERNS[term].search(folded))


_PATTERNS = {
    term: _term_pattern(term)
    for term in (
        *_RELEVANT_TERMS,
        *_HISTORICAL_TERMS,
        *_IRRELEVANT_TERMS,
        *_FEE_TERMS,
        *_LEGAL_TERMS,
    )
}


def assess_pdf_metadata(document: DocumentArtifact, *, as_of: date) -> PdfAdmission:
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
    relevant_matches = _matches(_RELEVANT_TERMS, folded)
    irrelevant_matches = _matches(_IRRELEVANT_TERMS, folded)
    historical_matches = _matches(_HISTORICAL_TERMS, folded)
    periods = _effective_periods(metadata)
    temporal = _temporal_status(periods, historical_matches, as_of)

    basis: list[str] = []
    if relevant_matches:
        basis.append("relevant metadata: " + ", ".join(relevant_matches[:6]))
    if irrelevant_matches and not relevant_matches:
        basis.append("irrelevant metadata: " + ", ".join(irrelevant_matches[:6]))
    if historical_matches:
        basis.append("historical metadata: " + ", ".join(historical_matches[:4]))
    if periods:
        basis.append("explicit effective period in link context")
    if document.origin_heading_path:
        basis.append("origin heading: " + " > ".join(document.origin_heading_path))

    # Product-relevant metadata always wins: a tariff sheet that happens to mention
    # a branch or contact line stays admissible. Only a document with no relevant
    # term at all and an explicit off-topic marker is rejected before transcription.
    if relevant_matches:
        relevance = PdfAdmissionRelevance.RELEVANT
    elif irrelevant_matches:
        relevance = PdfAdmissionRelevance.IRRELEVANT
    else:
        relevance = PdfAdmissionRelevance.AMBIGUOUS
    role = PdfAdmissionRole.PRODUCT_TERMS
    if _matches(_FEE_TERMS, folded):
        role = PdfAdmissionRole.FEES
    elif _matches(_LEGAL_TERMS, folded):
        role = PdfAdmissionRole.LEGAL_DISCLOSURE
    elif relevance is not PdfAdmissionRelevance.RELEVANT:
        role = PdfAdmissionRole.OTHER

    if relevance is PdfAdmissionRelevance.RELEVANT:
        reason = (
            "PDF was admitted from product-relevant link metadata; "
            "content discovery is unnecessary."
        )
    elif relevance is PdfAdmissionRelevance.IRRELEVANT:
        reason = (
            "PDF link metadata carries no product-relevant term and matches an "
            "off-topic marker; transcription is skipped."
        )
    else:
        reason = (
            "PDF metadata is inconclusive; extracted content still requires "
            "source discovery."
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
        periods.append(PdfEffectivePeriod(raw=match.group(0), start=start, end=end))
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
