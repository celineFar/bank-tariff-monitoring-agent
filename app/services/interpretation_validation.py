"""Turn a proposed `RequestInterpretation` into an authoritative `IntentResolution`.

The interpreter proposes; this module decides (fix plan T1, rules V1-V10). It
is pure: no model, no database. Everything with authority - the scope, the
clarification options, the query shape, the method, the route - is derived
here from the catalog and the conversation state, never taken on trust.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.catalog import CatalogLanguage, SeedCatalog
from app.domain.intent import (
    ClarificationOption,
    ConversationResolutionState,
    IntentResolution,
    PendingClarification,
    RequestIntent,
    RequestLanguage,
    ResolutionCandidate,
    ResolutionMethod,
    ResolutionScope,
)
from app.domain.interpretation import (
    InterpretationContext,
    OfferKind,
    OptionView,
    PendingClarificationView,
    PendingOffer,
    RequestInterpretation,
    ScopeView,
    route_for,
)
from app.domain.models import OfferingId, ProductType
from app.domain.query_shape import QueryShape, ReplyKind
from app.domain.structured_tariffs import QueryOperation
from app.domain.tariff_comparison import RANKABLE_PATHS

_LETTER = re.compile(r"[a-zA-ZԱ-ֆ]")
_MULTI = (QueryOperation.COMPARE, QueryOperation.OVERVIEW)
# Intents that never carry a product scope.
_SCOPELESS = frozenset(
    {
        RequestIntent.LIST_SUPPORTED_PRODUCTS,
        RequestIntent.GET_RUN_STATUS,
        RequestIntent.UNSUPPORTED_OR_GENERAL,
    }
)
_OFFER_REPLY = {
    OfferKind.MONITORING: ReplyKind.MONITORING_OFFER,
    OfferKind.SCOPE_CONFIRMATION: ReplyKind.SCOPE_CONFIRMATION,
}


class InterpretationRejected(ValueError):
    """The interpretation names something the catalog does not allow (V1)."""


@dataclass(frozen=True)
class _Scope:
    product: ProductType | None
    offerings: tuple[OfferingId, ...]
    cross_family: bool = False


def build_context(
    state: ConversationResolutionState, pending_offer: PendingOffer | None = None
) -> InterpretationContext:
    """What the interpreter may know about the conversation, bounded."""
    pending = state.pending_clarification
    last_scope = (
        ScopeView(
            product=state.latest_product,
            offering_ids=state.latest_offering_ids
            or ((state.latest_offering_id,) if state.latest_offering_id else ()),
        )
        if state.latest_product is not None
        else None
    )
    return InterpretationContext(
        conversation_language=state.conversation_language,
        last_scope=last_scope,
        last_question=state.last_question,
        pending_clarification=(
            PendingClarificationView(
                question=pending.original_query,
                intent=pending.intent,
                options=tuple(
                    OptionView(id=option.option_id, label=option.label)
                    for option in pending.options
                ),
            )
            if pending is not None
            else None
        ),
        pending_offer=pending_offer,
    )


def has_letters(message: str) -> bool:
    return bool(_LETTER.search(message))


def offer_accepted(resolution: IntentResolution, offer: PendingOffer | None) -> bool:
    """V4: the message takes up exactly this offer, explicitly."""
    return (
        offer is not None
        and resolution.replies_to is _OFFER_REPLY[offer.kind]
        and resolution.accepts is True
    )


class InterpretationValidator:
    def __init__(self, catalog: SeedCatalog) -> None:
        self._catalog = catalog
        self._enabled = {
            family.product: tuple(
                entry.offering_id for entry in catalog.enabled_for(family.product)
            )
            for family in catalog.families
        }
        self._family_labels = {
            family.product: {
                language: terms.name
                for language, terms in family.localized_names.items()
            }
            for family in catalog.families
        }
        self._offering_labels = {
            entry.offering_id: {
                language: terms.name
                for language, terms in entry.localized_names.items()
            }
            for entry in catalog.offerings
            if entry.enabled
        }

    def enabled(self, product: ProductType) -> tuple[OfferingId, ...]:
        return self._enabled[product]

    def validate(
        self,
        interpretation: RequestInterpretation,
        *,
        message: str,
        normalized_query: str,
        detected_language: RequestLanguage,
        state: ConversationResolutionState,
        pending_offer: PendingOffer | None,
        exact_offerings: tuple[OfferingId, ...] = (),
    ) -> IntentResolution:
        pending = state.pending_clarification
        language = self._language(interpretation, message, detected_language, state)
        intent = interpretation.request_intent
        replies_to = interpretation.replies_to
        # A reply needs something to reply to (V4, V10).
        if replies_to is ReplyKind.CLARIFICATION and pending is None:
            replies_to = ReplyKind.NONE
        if replies_to in (
            ReplyKind.MONITORING_OFFER,
            ReplyKind.SCOPE_CONFIRMATION,
        ) and (
            pending_offer is None or replies_to is not _OFFER_REPLY[pending_offer.kind]
        ):
            replies_to = ReplyKind.NONE
        if intent in _SCOPELESS and replies_to is ReplyKind.CLARIFICATION:
            replies_to = ReplyKind.NONE
        accepts = (
            interpretation.accepts
            if replies_to in (ReplyKind.MONITORING_OFFER, ReplyKind.SCOPE_CONFIRMATION)
            else None
        )
        question = interpretation.standalone_question or message.strip()
        shape = interpretation.query
        base = _Base(
            language=language,
            normalized_query=normalized_query,
            question=question[:1000],
            replies_to=replies_to,
            accepts=accepts,
            replying=replies_to is ReplyKind.CLARIFICATION,
            single_value=(
                intent is RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION
                and (shape is None or shape.operation is QueryOperation.SINGLE)
            ),
            pending_single_value=(
                replies_to is ReplyKind.CLARIFICATION
                and pending is not None
                and pending.expects_single_value
            ),
        )

        if replies_to in (ReplyKind.MONITORING_OFFER, ReplyKind.SCOPE_CONFIRMATION):
            assert pending_offer is not None
            if accepts is True:
                # The scope is the offer's, never one the interpreter restates.
                return self._resolved(
                    base,
                    RequestIntent.START_MONITORING_RUN,
                    _Scope(
                        pending_offer.product,
                        (pending_offer.offering_id,)
                        if pending_offer.offering_id
                        else (),
                    ),
                    query=None,
                )
            if intent is RequestIntent.START_MONITORING_RUN:
                intent = RequestIntent.UNSUPPORTED_OR_GENERAL

        if intent in _SCOPELESS:
            return self._resolved(base, intent, _Scope(None, ()), query=None)

        scope = self._scope(interpretation)
        if scope.cross_family:
            return self._clarify(base, intent, self._family_options(language))

        requested = self._interpreter_options(interpretation, language)
        if requested is not None:
            return self._clarify(base, intent, requested)

        # V5: an offering the user named, replaced by a different one without
        # context to explain it, is asked about instead of guessed.
        conflict = self._cross_check(scope, exact_offerings, base, state, pending_offer)
        if conflict is not None:
            return self._clarify(base, intent, conflict)

        if intent is RequestIntent.REVIEW_PENDING_CANDIDATES:
            offerings = scope.offerings if len(scope.offerings) == 1 else ()
            return self._resolved(base, intent, _Scope(scope.product, offerings), None)

        if intent is RequestIntent.START_MONITORING_RUN:
            if scope.product is None:
                return self._clarify(base, intent, self._family_options(language))
            if len(scope.offerings) > 1:
                return self._clarify(
                    base, intent, self._offering_options(scope.offerings, language)
                )
            return self._resolved(base, intent, scope, None)

        if intent is RequestIntent.GET_CURRENT_TARIFFS:
            return self._resolved(base, intent, scope, None)

        if intent is RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION and (
            shape is not None and shape.operation is QueryOperation.HISTORY
        ):
            intent = RequestIntent.GET_CHANGE_HISTORY
        if intent is RequestIntent.GET_CHANGE_HISTORY:
            history = QueryShape(
                operation=QueryOperation.HISTORY,
                fields=shape.fields if shape is not None else (),
            )
            return self._resolved(base, intent, scope, history)

        # An answer question: V2, V3.
        if scope.product is None:
            return self._clarify(base, intent, self._family_options(language))
        return self._answer(base, intent, interpretation, scope, shape)

    def shape_within(
        self,
        interpretation: RequestInterpretation,
        *,
        message: str,
        product: ProductType,
        offering_ids: tuple[OfferingId, ...] = (),
    ) -> QueryShape:
        """D9: the shape of a question whose scope the caller fixed (typed API).

        The interpreter's scope is discarded; only its shape is kept, bounded by
        the same rules as a chat question. A single value asked of a whole
        family has no answerable shape and raises.
        """
        forced = interpretation.model_copy(
            update={
                "product": product,
                "offering_ids": offering_ids,
                # Only a listing may read the whole family (V3); a single value
                # asked of a family abstains, as in chat.
                "family_wide": not offering_ids and interpretation.family_wide,
                "replies_to": ReplyKind.NONE,
                "clarification": interpretation.clarification.model_copy(
                    update={"needed": False, "option_ids": ()}
                ),
            }
        )
        history = interpretation.request_intent is RequestIntent.GET_CHANGE_HISTORY
        base = _Base(
            language=interpretation.language,
            normalized_query=message[:1000] or "-",
            question=message[:1000] or "-",
            replies_to=ReplyKind.NONE,
            accepts=None,
            replying=False,
        )
        if history:
            return QueryShape(
                operation=QueryOperation.HISTORY,
                fields=interpretation.query.fields if interpretation.query else (),
            )
        resolution = self._answer(
            base,
            RequestIntent.ANSWER_INDEXED_TARIFF_QUESTION,
            forced,
            _Scope(product, offering_ids),
            interpretation.query,
        )
        if resolution.needs_clarification or resolution.query is None:
            raise ValueError("the question needs one offering of the family")
        return resolution.query

    # --- answer questions ----------------------------------------------------------

    def _answer(
        self,
        base: _Base,
        intent: RequestIntent,
        interpretation: RequestInterpretation,
        scope: _Scope,
        shape: QueryShape | None,
    ) -> IntentResolution:
        assert scope.product is not None
        family = self._enabled[scope.product]
        offerings = scope.offerings
        operation = shape.operation if shape is not None else None
        fields = shape.fields if shape is not None else ()
        currency = shape.currency if shape is not None else None

        if operation is QueryOperation.FAMILY_RANK:
            rank_field = shape.rank_field if shape is not None else None
            if rank_field is None and len(fields) == 1:
                rank_field = fields[0]
            direction = shape.rank_direction if shape is not None else None
            ranked = offerings if len(offerings) >= 2 else family
            if rank_field in RANKABLE_PATHS and direction is not None:
                return self._resolved(
                    base,
                    intent,
                    _Scope(scope.product, ranked),
                    QueryShape(
                        operation=QueryOperation.FAMILY_RANK,
                        fields=(rank_field,),
                        rank_field=rank_field,
                        rank_direction=direction,
                        currency=currency,
                    ),
                )
            # Not rankable: list the values instead of guessing an order.
            operation = QueryOperation.OVERVIEW
            fields = (rank_field,) if rank_field is not None else fields
            offerings = ranked

        if operation is None:
            operation = (
                QueryOperation.SINGLE
                if len(offerings) == 1
                else QueryOperation.OVERVIEW
            )
        if operation is QueryOperation.SINGLE and len(offerings) > 1:
            operation = QueryOperation.OVERVIEW
        if operation in _MULTI and len(offerings) == 1:
            operation = QueryOperation.SINGLE

        family_wide = interpretation.family_wide and not base.pending_single_value
        if not offerings:
            # V3: a family-wide read only when the user asked about the family,
            # and never for a single value - also when the family comes in reply
            # to a question that asked for one value.
            if family_wide and operation in _MULTI:
                offerings = family
            elif family_wide and operation is QueryOperation.SINGLE:
                operation, offerings = QueryOperation.OVERVIEW, family
            else:
                return self._clarify(
                    base, intent, self._offering_options(family, base.language)
                )

        return self._resolved(
            base,
            intent,
            _Scope(scope.product, offerings),
            QueryShape(operation=operation, fields=fields, currency=currency),
        )

    # --- scope ----------------------------------------------------------------------

    def _scope(self, interpretation: RequestInterpretation) -> _Scope:
        offerings = interpretation.offering_ids
        for offering in offerings:
            if offering not in self._offering_labels:
                raise InterpretationRejected(f"{offering.value} is not enabled")
        products = {offering.product for offering in offerings}
        if len(products) > 1:
            return _Scope(None, (), cross_family=True)
        product = next(iter(products)) if products else interpretation.product
        # Offering IDs are the more specific statement; their family wins.
        return _Scope(product, offerings)

    def _cross_check(
        self,
        scope: _Scope,
        exact: tuple[OfferingId, ...],
        base: _Base,
        state: ConversationResolutionState,
        pending_offer: PendingOffer | None,
    ) -> tuple[ResolutionCandidate, ...] | None:
        if not exact or not scope.offerings or base.replying:
            return None
        if set(exact) & set(scope.offerings):
            return None
        explained = set(state.latest_offering_ids) | (
            {state.latest_offering_id} if state.latest_offering_id else set()
        )
        if pending_offer is not None and pending_offer.offering_id is not None:
            explained.add(pending_offer.offering_id)
        if set(scope.offerings) <= explained:
            return None
        union = tuple(dict.fromkeys((*exact, *scope.offerings)))
        if len({item.product for item in union}) > 1:
            return self._family_options(base.language)
        return self._offering_options(union, base.language)

    # --- clarification options (V10) --------------------------------------------------

    def _interpreter_options(
        self, interpretation: RequestInterpretation, language: RequestLanguage
    ) -> tuple[ResolutionCandidate, ...] | None:
        request = interpretation.clarification
        if not request.needed:
            return None
        families = [
            product for product in ProductType if product.value in request.option_ids
        ]
        offerings = [
            offering
            for offering in OfferingId
            if offering.value in request.option_ids
            and offering in self._offering_labels
        ]
        if len(offerings) >= 2:
            if len({item.product for item in offerings}) > 1:
                return self._family_options(language)
            return self._offering_options(tuple(offerings), language)
        if len(families) >= 2:
            return self._family_options(language)
        if len(families) == 1 and not offerings:
            return self._offering_options(self._enabled[families[0]], language)
        return None

    def _family_options(
        self, language: RequestLanguage
    ) -> tuple[ResolutionCandidate, ...]:
        label_language = _label_language(language)
        return tuple(
            ResolutionCandidate(
                candidate_id=family.product.value,
                label=self._family_labels[family.product][label_language],
                scope=ResolutionScope.FAMILY,
                product=family.product,
                score=1.0,
            )
            for family in self._catalog.families
        )

    def _offering_options(
        self, offerings: tuple[OfferingId, ...], language: RequestLanguage
    ) -> tuple[ResolutionCandidate, ...]:
        label_language = _label_language(language)
        chosen = set(offerings)
        product = offerings[0].product
        # Catalog order, so "3" means the same option every time.
        ordered = [item for item in self._enabled[product] if item in chosen]
        return tuple(
            ResolutionCandidate(
                candidate_id=offering.value,
                label=self._offering_labels[offering][label_language],
                scope=ResolutionScope.OFFERING,
                product=offering.product,
                offering_id=offering,
                score=1.0,
            )
            for offering in ordered
        )

    # --- results -------------------------------------------------------------------

    def _clarify(
        self,
        base: _Base,
        intent: RequestIntent,
        options: tuple[ResolutionCandidate, ...],
    ) -> IntentResolution:
        if len(options) < 2:
            options = self._family_options(base.language)
        replying = base.replying and intent is not RequestIntent.CLARIFICATION_RESPONSE
        return IntentResolution(
            intent=RequestIntent.CLARIFICATION_RESPONSE if replying else intent,
            continuation_intent=intent if replying else None,
            language=base.language,
            normalized_query=base.normalized_query,
            method=ResolutionMethod.CLARIFICATION,
            candidates=options,
            needs_clarification=True,
            expects_single_value=base.single_value or base.pending_single_value,
            standalone_question=base.question,
            replies_to=base.replies_to,
            accepts=base.accepts,
            route=None,
        )

    def _resolved(
        self,
        base: _Base,
        intent: RequestIntent,
        scope: _Scope,
        query: QueryShape | None,
    ) -> IntentResolution:
        offerings = scope.offerings
        replying = base.replying and intent is not RequestIntent.CLARIFICATION_RESPONSE
        label_language = _label_language(base.language)
        return IntentResolution(
            intent=RequestIntent.CLARIFICATION_RESPONSE if replying else intent,
            continuation_intent=intent if replying else None,
            language=base.language,
            normalized_query=base.normalized_query,
            method=ResolutionMethod.GEMINI,
            product=scope.product,
            offering_id=offerings[0] if len(offerings) == 1 else None,
            offering_ids=offerings if len(offerings) > 1 else (),
            candidates=tuple(
                ResolutionCandidate(
                    candidate_id=offering.value,
                    label=self._offering_labels[offering][label_language],
                    scope=ResolutionScope.OFFERING,
                    product=offering.product,
                    offering_id=offering,
                    score=1.0,
                )
                for offering in offerings
            ),
            expects_single_value=(
                query is not None and query.operation is QueryOperation.SINGLE
            ),
            standalone_question=base.question,
            query=query,
            replies_to=base.replies_to,
            accepts=base.accepts,
            route=route_for(intent),
        )

    # --- language (V6) -----------------------------------------------------------------

    @staticmethod
    def _language(
        interpretation: RequestInterpretation,
        message: str,
        detected: RequestLanguage,
        state: ConversationResolutionState,
    ) -> RequestLanguage:
        if not has_letters(message):
            return state.conversation_language or interpretation.language
        # The script decides between English and Armenian; the interpreter only
        # breaks the tie for mixed text.
        if detected is RequestLanguage.MIXED:
            return interpretation.language
        return detected


@dataclass(frozen=True)
class _Base:
    language: RequestLanguage
    normalized_query: str
    question: str
    replies_to: ReplyKind
    accepts: bool | None
    replying: bool
    # The question asks for one value (for a clarification: to remember it).
    single_value: bool = False
    # This is a reply to a clarification asked for one value.
    pending_single_value: bool = False


def _label_language(language: RequestLanguage) -> CatalogLanguage:
    return (
        CatalogLanguage.ARMENIAN
        if language is RequestLanguage.ARMENIAN
        else CatalogLanguage.ENGLISH
    )


def next_state(
    current: ConversationResolutionState,
    resolution: IntentResolution,
    *,
    message: str,
    now,
) -> ConversationResolutionState:
    """The conversation state after a resolved turn."""
    pending = None
    if resolution.needs_clarification:
        pending = PendingClarification(
            original_query=(resolution.standalone_question or message)[:1000],
            intent=resolution.continuation_intent or resolution.intent,
            language=resolution.language,
            options=tuple(_option(candidate) for candidate in resolution.candidates),
            created_at=now,
            expects_single_value=resolution.expects_single_value,
        )
    scoped = resolution.product is not None and not resolution.needs_clarification
    offerings = resolution.offering_ids or (
        (resolution.offering_id,) if resolution.offering_id else ()
    )
    effective = resolution.continuation_intent or resolution.intent
    asked = effective not in _SCOPELESS and resolution.standalone_question
    return current.model_copy(
        update={
            "introduction_shown": True,
            "pending_clarification": pending,
            "latest_product": resolution.product if scoped else current.latest_product,
            "latest_offering_id": (
                resolution.offering_id if scoped else current.latest_offering_id
            ),
            "latest_offering_ids": offerings if scoped else current.latest_offering_ids,
            "conversation_language": (
                resolution.language
                if has_letters(message)
                else current.conversation_language or resolution.language
            ),
            "last_question": (
                resolution.standalone_question if asked else current.last_question
            ),
        }
    )


def _option(candidate: ResolutionCandidate) -> ClarificationOption:
    return ClarificationOption(
        option_id=candidate.candidate_id,
        label=candidate.label,
        product=candidate.product,
        offering_id=candidate.offering_id,
    )
