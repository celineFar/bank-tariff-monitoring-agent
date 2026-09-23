"""Deliverable 13 — controlled failure scenarios that never fabricate data."""

from __future__ import annotations

import httpx

from app.config.models import HttpSettings
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SourceFailureCode
from app.domain.structured_tariffs import QueryStatus
from app.repositories.structured_tariff_query import (
    PostgresStructuredTariffQueryRepository,
)
from app.security.urls import DisallowedSourceUrl, validate_source_url
from app.services.failure_mapping import source_failure_code
from app.services.html_retriever import HtmlRetrievalError, HtmlRetriever
from app.services.structured_query_planning import issue_typed_resolution_plan
from app.services.structured_tariff_query import StructuredTariffQueryService
from scripts.demonstrations import ScenarioResult
from scripts.demonstrations.support import demonstration_sessions

ALLOWED = ("ameriabank.am", "www.ameriabank.am")
PAGE = "https://www.ameriabank.am/en/personal/loans/consumer-loans"


def _settings(**overrides) -> HttpSettings:
    values = {
        "allowed_source_hosts": ALLOWED,
        "allowed_download_mime_types": ("application/pdf", "text/html"),
        "user_agent": "ameria-tariff-monitor/demo",
        "timeout_seconds": 1.0,
        "max_attempts": 2,
        "backoff_base_seconds": 0.0,
        "retry_jitter_ratio": 0.0,
        "max_retry_delay_seconds": 1.0,
        "max_redirects": 2,
    }
    values.update(overrides)
    return HttpSettings(**values)


async def _retrieve(handler) -> Exception | None:
    """Drive the real retriever over a scripted transport, without sleeping."""

    async def _no_sleep(_seconds: float) -> None:
        return None

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=False
    ) as client:
        retriever = HtmlRetriever(client, _settings(), sleep=_no_sleep)
        try:
            await retriever.retrieve(PAGE)
        except Exception as exc:
            return exc
    return None


async def run() -> ScenarioResult:
    result = ScenarioResult(
        deliverable="Deliverable 13",
        title="Controlled failure scenarios with safe, typed outcomes",
    )

    # 1. A URL outside the approved bank domain never reaches the network.
    off_domain: Exception | None = None
    try:
        validate_source_url("https://evil.example.com/tariffs.pdf", ALLOWED)
    except DisallowedSourceUrl as exc:
        off_domain = exc
    result.step(
        "1) Requested a document from a host outside the allowlist: rejected "
        f"before any request with {type(off_domain).__name__}: {off_domain}."
    )

    # 2. A missing document on an allowed host.
    attempts = {"count": 0}

    def _not_found(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(404, text="not found")

    missing = await _retrieve(_not_found)
    missing_code = source_failure_code(missing, stage="html")
    result.step(
        f"2) Requested a page that returns 404: raised "
        f"{type(missing).__name__} mapped to {missing_code.value} after "
        f"{attempts['count']} attempt(s); a client error is not retried."
    )

    # 3. A transport timeout, with bounded retries.
    timeouts = {"count": 0}

    def _timeout(request: httpx.Request) -> httpx.Response:
        timeouts["count"] += 1
        raise httpx.ConnectTimeout("connect timed out", request=request)

    timed_out = await _retrieve(_timeout)
    timeout_code = source_failure_code(timed_out, stage="html")
    result.step(
        f"3) Simulated a connect timeout: raised {type(timed_out).__name__} "
        f"mapped to {timeout_code.value} after exactly {timeouts['count']} "
        "bounded attempt(s), then gave up."
    )

    # 4. A content type the pipeline must not admit.
    def _wrong_mime(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": "application/zip"}, content=b"PK\x03\x04"
        )

    wrong_mime = await _retrieve(_wrong_mime)
    mime_code = source_failure_code(wrong_mime, stage="html")
    result.step(
        f"4) Served an unexpected content type: rejected as {mime_code.value} "
        "instead of being parsed."
    )

    # 5. A question about an offering with no accepted snapshot.
    async with demonstration_sessions() as sessions:
        service = StructuredTariffQueryService(
            PostgresStructuredTariffQueryRepository(sessions)
        )
        question = "What application fee applies to the Express Mortgage?"
        plan = issue_typed_resolution_plan(
            question,
            product=ProductType.MORTGAGE,
            offering_ids=(OfferingId.MORTGAGE_EXPRESS,),
            session_id="demo-failures",
            turn_id="turn-1",
        )
        answer = await service.answer(plan, question)
    result.step(
        f"5) Asked about an offering with no accepted snapshot: "
        f"status={answer.status.value}, reason='{answer.reason}', "
        f"{len(answer.facts)} facts returned."
    )

    result.check(
        "off-domain source rejected",
        "a URL outside the approved bank domain is refused before any request",
        isinstance(off_domain, DisallowedSourceUrl),
        f"{type(off_domain).__name__}",
    )
    result.check(
        "missing document handled",
        "a 404 maps to the specific source.not_found code, not a generic error",
        isinstance(missing, HtmlRetrievalError)
        and missing_code is SourceFailureCode.NOT_FOUND,
        f"{type(missing).__name__} -> {missing_code.value}",
    )
    result.check(
        "client errors are not retried",
        "a 404 is attempted once rather than burning the retry budget",
        attempts["count"] == 1,
        f"{attempts['count']} attempt(s)",
    )
    result.check(
        "timeout maps to a typed code",
        "a connect timeout becomes source.timeout",
        timeout_code is SourceFailureCode.TIMEOUT,
        f"{timeout_code.value}",
    )
    result.check(
        "retries are bounded",
        "a transient failure retries at most max_attempts times",
        timeouts["count"] == _settings().max_attempts,
        f"{timeouts['count']} attempt(s), limit {_settings().max_attempts}",
    )
    result.check(
        "unexpected content type rejected",
        "a non-HTML payload is refused instead of parsed",
        mime_code is SourceFailureCode.MIME_REJECTED,
        f"{mime_code.value}",
    )
    result.check(
        "missing snapshot abstains",
        "a question with no accepted data returns a stated absence",
        answer.status is QueryStatus.MISSING and bool(answer.reason),
        f"status={answer.status.value}",
    )
    result.check(
        "no fabricated business data",
        "every failure path returns zero tariff values",
        not answer.facts and answer.answer is None,
        f"{len(answer.facts)} facts, answer={answer.answer!r}",
    )
    result.note(
        "Transport failures are scripted through httpx.MockTransport so the "
        "demonstration is reproducible offline, but the retriever, allowlist, "
        "retry policy, and failure mapping are the production code paths."
    )
    return result
