from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from app.domain.normalization import NormalizedScalar, ScalarKind

_NUMBER = r"\d+(?:[\s,]\d{3})*(?:[.,]\d+)?"
_CURRENCY = r"(?:AMD|USD|EUR|֏|\$|€|դրամ|drams?|US\s+dollars?|dollars?|euros?)"
_UNIT = rf"(?:%|{_CURRENCY}|months?|years?|days?)"
_RANGE_RE = re.compile(
    rf"(?P<raw>(?P<minimum>{_NUMBER})\s*(?:-|\u2013|\u2014|to)\s*"
    rf"(?P<maximum>{_NUMBER})(?:\s*(?P<unit>{_UNIT}))?)",
    re.IGNORECASE,
)
_PREFIX_RANGE_RE = re.compile(
    rf"(?P<raw>(?P<unit>{_CURRENCY})\s*(?P<minimum>{_NUMBER})\s*"
    rf"(?:-|\u2013|\u2014|to)\s*(?:(?:{_CURRENCY})\s*)?"
    rf"(?P<maximum>{_NUMBER}))",
    re.IGNORECASE,
)
_REPEATED_UNIT_RANGE_RE = re.compile(
    rf"(?P<raw>(?P<minimum>{_NUMBER})\s*(?P<unit>%|{_CURRENCY})\s*"
    rf"(?:-|\u2013|\u2014|to)\s*(?P<maximum>{_NUMBER})\s*(?:%|{_CURRENCY}))",
    re.IGNORECASE,
)
_COMPARISON_RE = re.compile(
    rf"(?P<raw>(?P<operator>up\s+to|at\s+least|not\s+less\s+than|"
    rf"not\s+more\s+than|from|over|under)\s+(?P<value>{_NUMBER})\s*"
    rf"(?P<unit>{_UNIT}))",
    re.IGNORECASE,
)
_VALUE_RE = re.compile(
    rf"(?P<raw>(?P<value>{_NUMBER})\s*(?P<unit>{_UNIT}))",
    re.IGNORECASE,
)
_PREFIX_VALUE_RE = re.compile(
    rf"(?P<raw>(?P<unit>{_CURRENCY})\s*(?P<value>{_NUMBER}))",
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(
    r"\b(?P<year>(?:19|20)\d{2})[-/.](?P<month>\d{1,2})[-/.](?P<day>\d{1,2})\b"
)
_DMY_DATE_RE = re.compile(
    r"\b(?P<day>\d{1,2})[./](?P<month>\d{1,2})[./](?P<year>(?:19|20)\d{2})\b"
)
_MONTH_DATE_RE = re.compile(
    r"\b(?P<month_name>January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(?P<day>\d{1,2}),?\s+"
    r"(?P<year>(?:19|20)\d{2})\b",
    re.IGNORECASE,
)

_OPERATORS = {
    "up to": "<=",
    "not more than": "<=",
    "under": "<",
    "at least": ">=",
    "not less than": ">=",
    "from": ">=",
    "over": ">",
}
_UNITS = {
    "%": "percent",
    "դրամ": "AMD",
    "֏": "AMD",
    "dram": "AMD",
    "drams": "AMD",
    "$": "USD",
    "us dollar": "USD",
    "us dollars": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "€": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "month": "month",
    "months": "month",
    "year": "year",
    "years": "year",
    "day": "day",
    "days": "day",
}
_MONTHS = {
    name.lower(): index
    for index, name in enumerate(
        (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ),
        start=1,
    )
}


def extract_scalar_candidates(text: str) -> tuple[NormalizedScalar, ...]:
    """Find syntax-level scalar candidates without assigning tariff semantics."""
    candidates: list[tuple[int, int, NormalizedScalar]] = []
    occupied: list[tuple[int, int]] = []

    for pattern, builder in (
        (_PREFIX_RANGE_RE, _range_scalar),
        (_REPEATED_UNIT_RANGE_RE, _range_scalar),
        (_RANGE_RE, _range_scalar),
        (_COMPARISON_RE, _comparison_scalar),
    ):
        for match in pattern.finditer(text):
            if _overlaps(match.span(), occupied):
                continue
            scalar = builder(match)
            if scalar is not None:
                candidates.append((match.start(), match.end(), scalar))
                occupied.append(match.span())

    for pattern in (_ISO_DATE_RE, _DMY_DATE_RE, _MONTH_DATE_RE):
        for match in pattern.finditer(text):
            if _overlaps(match.span(), occupied):
                continue
            try:
                month = (
                    _MONTHS[match.group("month_name").lower()]
                    if "month_name" in match.groupdict()
                    else int(match.group("month"))
                )
                parsed = date(
                    int(match.group("year")),
                    month,
                    int(match.group("day")),
                )
            except ValueError:
                continue
            scalar = NormalizedScalar(
                raw=match.group(0), kind=ScalarKind.DATE, normalized_date=parsed
            )
            candidates.append((match.start(), match.end(), scalar))
            occupied.append(match.span())

    for pattern in (_PREFIX_VALUE_RE, _VALUE_RE):
        for match in pattern.finditer(text):
            if _overlaps(match.span(), occupied):
                continue
            value = _decimal(match.group("value"))
            if value is None:
                continue
            candidates.append(
                (
                    match.start(),
                    match.end(),
                    NormalizedScalar(
                        raw=match.group("raw"),
                        kind=ScalarKind.NUMBER,
                        value=value,
                        unit=_unit(match.group("unit")),
                    ),
                )
            )
            occupied.append(match.span())

    candidates.sort(key=lambda item: (item[0], item[1]))
    return tuple(item[2] for item in candidates)


def _range_scalar(match: re.Match[str]) -> NormalizedScalar | None:
    minimum = _decimal(match.group("minimum"))
    maximum = _decimal(match.group("maximum"))
    if minimum is None or maximum is None:
        return None
    return NormalizedScalar(
        raw=match.group("raw"),
        kind=ScalarKind.RANGE,
        min_value=minimum,
        max_value=maximum,
        unit=_unit(match.group("unit")) if match.group("unit") else None,
    )


def _comparison_scalar(match: re.Match[str]) -> NormalizedScalar | None:
    value = _decimal(match.group("value"))
    if value is None:
        return None
    operator = re.sub(r"\s+", " ", match.group("operator").lower())
    return NormalizedScalar(
        raw=match.group("raw"),
        kind=ScalarKind.NUMBER,
        operator=_OPERATORS[operator],
        value=value,
        unit=_unit(match.group("unit")),
    )


def _decimal(value: str) -> Decimal | None:
    compact = value.replace(" ", "")
    if compact.count(",") == 1 and "." not in compact:
        right = compact.rsplit(",", 1)[1]
        compact = (
            compact.replace(",", ".") if len(right) != 3 else compact.replace(",", "")
        )
    else:
        compact = compact.replace(",", "")
    try:
        return Decimal(compact)
    except InvalidOperation:
        return None


def _unit(value: str) -> str:
    normalized = value.strip()
    return _UNITS.get(normalized.lower(), normalized.upper())


def _overlaps(span: tuple[int, int], occupied: list[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in occupied)
