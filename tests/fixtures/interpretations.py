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


Scripted = RequestInterpretation | Callable[[InterpretationRequest], RequestInterpretation]


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
