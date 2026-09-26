"""Where today falls against a set of effective periods.

One rule for everything that dates source material: PDF admission, which reads
periods from link context, and source discovery, whose classifier extracts
them from content. A period may be open at either end ("valid until
31.10.2026", "effective from 14.07.2026").
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from enum import StrEnum
from typing import Protocol


class PeriodStatus(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    FUTURE = "future"
    TIME_BOUNDED = "time_bounded"


class DatedPeriod(Protocol):
    start: date | None
    end: date | None


def period_status(periods: Iterable[DatedPeriod], as_of: date) -> PeriodStatus | None:
    """The periods' status on `as_of`, or None when none carries a date.

    Current when any period covers the day; historical when every period ended
    before it; future when every period starts after it; time-bounded otherwise.
    """
    dated = [period for period in periods if period.start or period.end]
    if not dated:
        return None
    if any(
        (period.start is None or period.start <= as_of)
        and (period.end is None or as_of <= period.end)
        for period in dated
    ):
        return PeriodStatus.CURRENT
    if all(period.end is not None and period.end < as_of for period in dated):
        return PeriodStatus.HISTORICAL
    if all(period.start is not None and period.start > as_of for period in dated):
        return PeriodStatus.FUTURE
    return PeriodStatus.TIME_BOUNDED
