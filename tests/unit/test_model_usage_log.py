"""Model calls are logged by count first and cost second.

Spend alone hides the models that cost nothing and run out anyway. An embedding
model refused for quota bills $0.00, so a cost-shaped view shows silence while
the resource drains -- which is exactly how a day's quota can disappear
unnoticed. Every call is therefore logged, and a provider refusal keeps its HTTP
status so a quota wall is distinguishable from a bad request.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from app.services.model_call_usage import (
    MODEL_USAGE_LOGGER_NAME,
    CostEstimate,
    log_model_call,
    new_usage,
    provider_error_class,
)


class _ApiError(Exception):
    """Shaped like google.genai.errors.APIError: a code and a status."""

    def __init__(self, code: int, status: str) -> None:
        super().__init__(status)
        self.code = code
        self.status = status


def test_quota_refusal_is_distinguishable_from_any_other_client_error() -> None:
    exhausted = provider_error_class(_ApiError(429, "RESOURCE_EXHAUSTED"))
    forbidden = provider_error_class(_ApiError(403, "PERMISSION_DENIED"))

    assert exhausted == "_ApiError:http_429_RESOURCE_EXHAUSTED"
    assert exhausted != forbidden
    # The aggregate counts quota refusals with this pattern.
    assert "http_429" in exhausted
    assert "http_429" not in forbidden


def test_plain_errors_keep_their_name_and_no_error_is_none() -> None:
    assert provider_error_class(ValueError("boom")) == "ValueError"
    assert provider_error_class(None) is None


def test_a_refused_free_call_is_still_logged_although_it_cost_nothing(
    caplog,
) -> None:
    usage = new_usage(
        stage="indexing.embedding",
        operation="embed",
        model_id="gemini-embedding-001",
        outcome="failed",
        latency_ms=204,
        input_count=1,
        error_class="ClientError:http_429_RESOURCE_EXHAUSTED",
    )

    with caplog.at_level(logging.INFO, logger=MODEL_USAGE_LOGGER_NAME):
        log_model_call(
            usage,
            CostEstimate(None, None, None, None, "missing_input_usage"),
        )

    line = caplog.text
    assert "model=gemini-embedding-001" in line
    assert "outcome=failed" in line
    assert "error=ClientError:http_429_RESOURCE_EXHAUSTED" in line
    # The call is visible even though there is no cost to report.
    assert "cost_usd=-" in line
    assert "inputs=1" in line


def test_a_billed_call_reports_its_cost(caplog) -> None:
    usage = new_usage(
        stage="adk.cli",
        operation="generate",
        model_id="gemini-3.7-flash",
        outcome="succeeded",
        latency_ms=1200,
        input_tokens=22_000,
        output_tokens=300,
    )

    with caplog.at_level(logging.INFO, logger=MODEL_USAGE_LOGGER_NAME):
        log_model_call(
            usage,
            CostEstimate("1", Decimal("0.3"), Decimal("2.5"), Decimal("0.0141"), None),
        )

    line = caplog.text
    assert "cost_usd=0.014100" in line
    assert "in_tokens=22000" in line
    assert "cost_unknown=-" in line
