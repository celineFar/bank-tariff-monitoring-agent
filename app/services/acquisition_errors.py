from __future__ import annotations

from enum import StrEnum


class AcquisitionFailure(StrEnum):
    BROWSER_UNAVAILABLE = "BROWSER_UNAVAILABLE"
    BROWSER_FAILED = "BROWSER_FAILED"
    INCOMPLETE_CONTENT = "INCOMPLETE_CONTENT"


class AcquisitionError(RuntimeError):
    """An acquisition that must fail the offering rather than degrade silently.

    `reasons` are short, bank-content-free statements of what was missing, such
    as ``tables 3 -> 0`` or ``main_chars 368 < 3000``, for the run record and
    the audit.
    """

    def __init__(
        self,
        reason: AcquisitionFailure,
        message: str,
        *,
        reasons: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.reasons = reasons
