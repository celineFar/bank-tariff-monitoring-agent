"""Test doubles for the request interpreter (fix plan T1)."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from app.domain.intent import RequestIntent, RequestLanguage
from app.domain.interpretation import (
    InterpretationClarification,
    InterpretationRequest,
    InterpretedIntent,
    QueryShape,
    ReplyKind,
    RequestInterpretation,
)
from app.domain.models import OfferingId, ProductType
from app.domain.query_shape import Currency
from app.domain.structured_tariffs import FieldPath, QueryOperation, RankDirection


def interp(
    intent: RequestIntent,
    *,
    replies_to: ReplyKind = ReplyKind.NONE,
    accepts: bool | None = None,
    language: RequestLanguage = RequestLanguage.ENGLISH,
    product: ProductType | None = None,
    offering_ids: tuple[OfferingId, ...] = (),
    family_wide: bool = False,
    standalone_question: str = "",
    operation: QueryOperation | None = None,
    fields: tuple[FieldPath, ...] = (),
    rank_field: FieldPath | None = None,
    rank_direction: RankDirection | None = None,
    currency: str | None = None,
    clarify: tuple[str, ...] = (),
) -> RequestInterpretation:
    """A concise `RequestInterpretation` for tests."""
    return RequestInterpretation(
        intent=InterpretedIntent(intent.value),
        replies_to=replies_to,
        accepts=accepts,
        language=language,
        product=product,
        offering_ids=offering_ids,
        family_wide=family_wide,
        standalone_question=standalone_question,
        query=(
            QueryShape(
                operation=operation,
                fields=fields,
                rank_field=rank_field,
                rank_direction=rank_direction,
                currency=Currency(currency) if currency else None,
            )
            if operation is not None
            else None
        ),
        clarification=InterpretationClarification(
            needed=bool(clarify), option_ids=clarify
        ),
    )


Scripted = (
    RequestInterpretation | Callable[[InterpretationRequest], RequestInterpretation]
)


class ScriptedInterpreter:
    """Answers each message with the interpretation a test scripted for it."""

    def __init__(self, script: Mapping[str, Scripted]) -> None:
        self._script = dict(script)
        self.calls = 0
        self.requests: list[InterpretationRequest] = []

    async def interpret(self, request: InterpretationRequest) -> RequestInterpretation:
        self.calls += 1
        self.requests.append(request)
        if request.message not in self._script:
            raise LookupError(f"no scripted interpretation for {request.message!r}")
        scripted = self._script[request.message]
        return scripted(request) if callable(scripted) else scripted


def tool_test_script() -> dict[str, RequestInterpretation]:
    """Interpretations for the phrases the tool tests say."""
    answer = RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION
    express = (OfferingId.MORTGAGE_EXPRESS,)
    rate = (FieldPath.NOMINAL_RATE_MINIMUM, FieldPath.NOMINAL_RATE_MAXIMUM)
    return {
        "current Express Mortgage rate": interp(
            answer,
            offering_ids=express,
            operation=QueryOperation.SINGLE,
            fields=rate,
            standalone_question="What is the current Express Mortgage interest rate?",
        ),
        "What is the Express Mortgage rate?": interp(
            answer,
            offering_ids=express,
            operation=QueryOperation.SINGLE,
            fields=rate,
            standalone_question="What is the Express Mortgage interest rate?",
        ),
        "current mortgage tariffs": interp(
            RequestIntent.GET_CURRENT_TARIFFS,
            product=ProductType.MORTGAGE,
            family_wide=True,
            standalone_question="What are the current mortgage tariffs?",
        ),
        "What changed recently?": interp(
            RequestIntent.GET_CHANGE_HISTORY,
            operation=QueryOperation.HISTORY,
            standalone_question="What tariffs changed recently?",
        ),
        "What changed for Express Mortgage?": interp(
            RequestIntent.GET_CHANGE_HISTORY,
            offering_ids=express,
            operation=QueryOperation.HISTORY,
            standalone_question="What changed for the Express Mortgage?",
        ),
        "show me all current tariffs": interp(
            RequestIntent.GET_CURRENT_TARIFFS,
            standalone_question="Show all current tariffs.",
        ),
        "yes": interp(
            RequestIntent.START_MONITORING_RUN,
            replies_to=ReplyKind.SCOPE_CONFIRMATION,
            accepts=True,
        ),
        "review the Express Mortgage candidates": interp(
            RequestIntent.REVIEW_PENDING_CANDIDATES,
            offering_ids=express,
        ),
        "What is the nominal interest rate for Overdraft?": interp(
            answer,
            offering_ids=(OfferingId.OVERDRAFT,),
            operation=QueryOperation.SINGLE,
            fields=(FieldPath.NOMINAL_RATE_MINIMUM, FieldPath.NOMINAL_RATE_MAXIMUM),
            standalone_question="What is the nominal interest rate for the Overdraft?",
        ),
        "What are mortgage rates?": interp(
            answer,
            product=ProductType.MORTGAGE,
            family_wide=True,
            operation=QueryOperation.OVERVIEW,
            fields=rate,
        ),
    }


def scripted_resolver(script=None):
    """A `RequestResolver` answering from a script (default: the tool-test phrases)."""
    from app.config.seed_catalog import load_seed_catalog
    from app.services.intent_resolution import RequestResolver

    return RequestResolver(
        load_seed_catalog(),
        interpreter=ScriptedInterpreter(
            tool_test_script() if script is None else script
        ),
    )


def recorded_resolver():
    """A `RequestResolver` replaying the recorded interpretation case set."""
    from app.config.seed_catalog import load_seed_catalog
    from app.services.intent_resolution import RequestResolver
    from tests.fixtures.recorded_interpretations import RecordedInterpreter

    return RequestResolver(load_seed_catalog(), interpreter=RecordedInterpreter())
