"""Pure projection of final accepted snapshots into structured RAG read records."""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from typing import Any

from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.domain.monitoring import SnapshotAttempt, SnapshotStatus
from app.domain.semantic_extraction import (
    AbsoluteMoneyRange,
    AgeRange,
    ConditionalValue,
    EvidenceCitation,
    ExtractedValue,
    ExtractionField,
    ExtractionStatus,
    LoanProduct,
    MoneyRange,
    OtherAmountFormula,
    PropertyValuePercentage,
    Rate,
    RequirementPolicy,
    SalaryMultiple,
    SemanticExtractionResult,
    TermRange,
)
from app.domain.source_discovery import Authority
from app.domain.structured_tariffs import (
    SOURCE_FIELD_PATHS,
    FactEvidence,
    FieldPath,
    OfferingProfile,
    RetrievalUnit,
    RetrievalUnitKind,
    StructuredProjection,
    TariffFact,
    fee_field_path,
)
from app.services.snapshot_lifecycle import canonical_tariff_payload

_OFFICIAL = {
    Authority.OFFICIAL_TERMS,
    Authority.OFFICIAL_PRODUCT_CONTENT,
    Authority.OFFICIAL_FAQ,
    Authority.OFFICIAL_CAMPAIGN_CONTENT,
}
RENDERER_VERSION = 1
_SALARY_WORD = re.compile(r"(?i)\b(?:salary|payroll)\b|աշխատավարձ")
_MARKDOWN_LINK = re.compile(r"\[([^]]+)\]\((?:<[^>]+>|[^)]+)\)")


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))


def _stable(value: Any) -> str:
    return json.dumps(
        _json_value(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def _hash(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _currency_condition(conditions: tuple[Any, ...]) -> str | None:
    currencies = {
        str(item.value).upper()
        for item in conditions
        if getattr(item, "dimension", None) == "currency"
    }
    return next(iter(currencies)) if len(currencies) == 1 else None


def _clean(value: str) -> str:
    plain = BeautifulSoup(_MARKDOWN_LINK.sub(r"\1", value), "html.parser").get_text(
        " ", strip=True
    )
    return " ".join(plain.split())


class StructuredTariffProjector:
    """Fail closed when accepted facts cannot be tied to captured official evidence."""

    def project(
        self,
        snapshot: SnapshotAttempt,
        *,
        display_name: str,
        aliases: tuple[str, ...] = (),
        language: str = "en",
    ) -> StructuredProjection:
        if (
            snapshot.status is not SnapshotStatus.ACCEPTED
            or snapshot.accepted_at is None
        ):
            raise ValueError("only final accepted snapshots can be projected")
        extraction = SemanticExtractionResult.model_validate(
            snapshot.semantic_extraction
        )
        product = extraction.loan_product
        if product is None:
            raise ValueError("accepted snapshot lacks complete semantic extraction")
        if canonical_tariff_payload(product) != snapshot.normalized_tariff:
            raise ValueError("accepted snapshot and final semantic extraction disagree")
        catalog = {item.evidence_id: item for item in extraction.evidence_catalog}
        facts: list[TariffFact] = []

        def emit(
            path: FieldPath,
            value: Any,
            extracted: ExtractedValue,
            *,
            conditions: tuple[Any, ...] = (),
            number: Decimal | int | None = None,
            unit: str | None = None,
            currency: str | None = None,
            rate_basis=None,
            fee_scope: str | None = None,
            suffix: str = "",
            group: str | None = None,
        ) -> None:
            condition_values = tuple(_json_value(item) for item in conditions)
            encoded = _json_value(value)
            variant_key = _hash(
                group or path.value,
                _stable(encoded) if group is None else "",
                _stable(condition_values),
                suffix,
            )[:24]
            evidence = (
                self._evidence(extracted.evidence, catalog)
                if extracted.status is ExtractionStatus.FOUND
                else ()
            )
            facts.append(
                TariffFact(
                    fact_id=_hash(str(snapshot.id), path.value, variant_key),
                    snapshot_id=snapshot.id,
                    offering_id=snapshot.offering_id,
                    field_path=path,
                    variant_key=variant_key,
                    status=extracted.status,
                    value=encoded,
                    number=Decimal(str(number)) if number is not None else None,
                    unit=unit,
                    currency=currency,
                    rate_basis=rate_basis,
                    fee_scope=fee_scope,
                    conditions=condition_values,
                    evidence=evidence,
                )
            )

        fields = self._extracted_fields(product)
        for field, extracted in fields:
            paths = SOURCE_FIELD_PATHS[field]
            if field is ExtractionField.CATEGORY:
                continue  # An enum inferred from scope is routing metadata, not source evidence.
            if extracted.status is not ExtractionStatus.FOUND:
                for path in paths:
                    emit(path, None, extracted, suffix="missing")
                continue
            if field in {ExtractionField.LOAN_AMOUNT, ExtractionField.CREDIT_LIMIT}:
                self._amounts(field, extracted, emit)
            elif field in {
                ExtractionField.INTEREST_RATE,
                ExtractionField.EFFECTIVE_RATE,
            }:
                self._rates(field, extracted, emit)
            elif field is ExtractionField.TERM:
                self._terms(extracted, emit)
            elif field is ExtractionField.FEES:
                for fee in extracted.value:
                    emit(
                        fee_field_path(fee.description),
                        fee,
                        extracted,
                        conditions=fee.conditions,
                        number=fee.amount if fee.amount is not None else fee.rate_pct,
                        unit="money"
                        if fee.amount is not None
                        else "percent"
                        if fee.rate_pct is not None
                        else None,
                        currency=fee.currency,
                        fee_scope=fee.scope.value,
                    )
            elif field in {ExtractionField.DOWN_PAYMENT_PCT, ExtractionField.LTV_PCT}:
                low, high = paths
                for item in extracted.value:
                    emit(
                        low,
                        item.value,
                        extracted,
                        conditions=item.conditions,
                        group=_stable(item),
                        number=item.value,
                        unit="percent",
                    )
                    emit(
                        high,
                        item.value,
                        extracted,
                        conditions=item.conditions,
                        group=_stable(item),
                        number=item.value,
                        unit="percent",
                    )
            elif field is ExtractionField.AGE_REQUIREMENTS:
                for item in extracted.value:
                    age: AgeRange = item.value
                    if age.min_age is not None:
                        emit(
                            paths[0],
                            age.min_age,
                            extracted,
                            conditions=item.conditions,
                            group=_stable(item),
                            number=age.min_age,
                            unit="years",
                        )
                    if age.max_age is not None:
                        emit(
                            paths[1],
                            age.max_age,
                            extracted,
                            conditions=item.conditions,
                            group=_stable(item),
                            number=age.max_age,
                            unit="years",
                        )
            elif field is ExtractionField.SPECIAL_CONDITIONS:
                for item in extracted.value:
                    value = item.value if isinstance(item, ConditionalValue) else item
                    conditions = (
                        item.conditions if isinstance(item, ConditionalValue) else ()
                    )
                    emit(
                        FieldPath.SPECIAL_CONDITION,
                        value,
                        extracted,
                        conditions=conditions,
                    )
                    if isinstance(value, str) and _SALARY_WORD.search(value):
                        emit(
                            FieldPath.SALARY_PRIVILEGE,
                            value,
                            extracted,
                            conditions=conditions,
                        )
            elif field is ExtractionField.VARIANTS:
                for item in extracted.value:
                    emit(
                        FieldPath.VARIANT_NAME,
                        item.name,
                        extracted,
                        suffix=item.variant_id,
                    )
                    if item.purpose:
                        emit(
                            FieldPath.VARIANT_PURPOSE,
                            item.purpose,
                            extracted,
                            suffix=item.variant_id,
                        )
            elif isinstance(extracted.value, RequirementPolicy):
                policy = extracted.value
                if policy.default_required is not None:
                    emit(paths[0], policy.default_required, extracted, suffix="default")
                for item in policy.exceptions:
                    emit(paths[0], item.value, extracted, conditions=item.conditions)
            else:
                values = (
                    extracted.value
                    if isinstance(extracted.value, (tuple, list))
                    else (extracted.value,)
                )
                for item in values:
                    if isinstance(item, ConditionalValue):
                        emit(
                            paths[0], item.value, extracted, conditions=item.conditions
                        )
                    else:
                        emit(paths[0], item, extracted)

        profile = self._profile(snapshot, product, display_name, aliases)
        units = self._units(snapshot, profile, facts, language)
        return StructuredProjection(profile=profile, facts=tuple(facts), units=units)

    @staticmethod
    def _evidence(
        citations: tuple[EvidenceCitation, ...], catalog: dict
    ) -> tuple[FactEvidence, ...]:
        verified: list[FactEvidence] = []
        for citation in citations:
            item = catalog.get(citation.evidence_id)
            if item is None or citation.quote not in item.content:
                raise ValueError("fact citation is missing from captured evidence")
            if (
                citation.source_item_id != item.source_item_id
                or citation.locator != item.locator
            ):
                raise ValueError(
                    "fact citation locator disagrees with captured evidence"
                )
            if (
                citation.source_url != citation.locator.source_url
                or citation.source_type != citation.locator.source_type
            ):
                raise ValueError("fact citation URL/type disagrees with locator")
            if citation.authority != item.authority:
                raise ValueError(
                    "fact citation authority disagrees with captured evidence"
                )
            if citation.authority not in _OFFICIAL or item.authority not in _OFFICIAL:
                raise ValueError("fact citation is not an official source")
            verified.append(
                FactEvidence(
                    evidence_id=citation.evidence_id,
                    quote=citation.quote,
                    source_url=citation.source_url,
                    source_item_id=citation.source_item_id,
                    source_document_key=item.document_id,
                    authority=citation.authority.value,
                    locator=citation.locator.model_dump(mode="json", exclude_none=True),
                )
            )
        if not verified:
            raise ValueError("found fact has no official source evidence")
        return tuple(verified)

    @staticmethod
    def _extracted_fields(
        product: LoanProduct,
    ) -> tuple[tuple[ExtractionField, ExtractedValue], ...]:
        result = []
        for name, value in product:
            if isinstance(value, ExtractedValue):
                result.append((ExtractionField(name), value))
        for name, value in product.details:
            if isinstance(value, ExtractedValue):
                result.append((ExtractionField(name), value))
        return tuple(result)

    @staticmethod
    def _amounts(field: ExtractionField, extracted: ExtractedValue, emit) -> None:
        paths = SOURCE_FIELD_PATHS[field]
        for item in extracted.value:
            group = _stable(item)
            # Loan amounts arrive wrapped in conditions; credit limits do not.
            conditional = isinstance(item, ConditionalValue)
            amount = item.value if conditional else item
            conditions = item.conditions if conditional else ()
            if isinstance(amount, AbsoluteMoneyRange):
                bounds: MoneyRange = amount.range
                if bounds.min is not None:
                    emit(
                        paths[0],
                        bounds.min,
                        extracted,
                        conditions=conditions,
                        group=group,
                        number=bounds.min,
                        unit="money",
                        currency=bounds.currency,
                    )
                if bounds.max is not None:
                    emit(
                        paths[1],
                        bounds.max,
                        extracted,
                        conditions=conditions,
                        group=group,
                        number=bounds.max,
                        unit="money",
                        currency=bounds.currency,
                    )
            elif isinstance(amount, SalaryMultiple):
                if amount.min_multiple is not None:
                    emit(
                        paths[2],
                        amount.min_multiple,
                        extracted,
                        conditions=conditions,
                        group=group,
                        number=amount.min_multiple,
                        unit="salary_multiple",
                    )
                if amount.max_multiple is not None:
                    emit(
                        paths[3],
                        amount.max_multiple,
                        extracted,
                        conditions=conditions,
                        group=group,
                        number=amount.max_multiple,
                        unit="salary_multiple",
                    )
            elif isinstance(amount, PropertyValuePercentage):
                if amount.min_pct is not None:
                    emit(
                        paths[4],
                        amount.min_pct,
                        extracted,
                        conditions=conditions,
                        group=group,
                        number=amount.min_pct,
                        unit="percent",
                    )
                if amount.max_pct is not None:
                    emit(
                        paths[5],
                        amount.max_pct,
                        extracted,
                        conditions=conditions,
                        group=group,
                        number=amount.max_pct,
                        unit="percent",
                    )
            elif isinstance(amount, OtherAmountFormula):
                emit(
                    paths[6],
                    amount.expression,
                    extracted,
                    conditions=conditions,
                    group=group,
                    unit="formula",
                )
            else:
                raise ValueError(f"unsupported amount shape: {type(amount).__name__}")

    @staticmethod
    def _rates(field: ExtractionField, extracted: ExtractedValue, emit) -> None:
        paths = SOURCE_FIELD_PATHS[field]
        for item in extracted.value:
            group = _stable(item)
            rate: Rate = item.value
            if rate.min is not None:
                emit(
                    paths[0],
                    rate.min,
                    extracted,
                    conditions=item.conditions,
                    group=group,
                    number=rate.min,
                    unit="percent",
                    rate_basis=rate.basis,
                    currency=_currency_condition(item.conditions),
                )
            if rate.max is not None:
                emit(
                    paths[1],
                    rate.max,
                    extracted,
                    conditions=item.conditions,
                    group=group,
                    number=rate.max,
                    unit="percent",
                    rate_basis=rate.basis,
                    currency=_currency_condition(item.conditions),
                )
            if rate.formula is not None:
                emit(
                    paths[2],
                    rate.formula,
                    extracted,
                    conditions=item.conditions,
                    group=group,
                    unit="formula",
                    rate_basis=rate.basis,
                    currency=_currency_condition(item.conditions),
                )

    @staticmethod
    def _terms(extracted: ExtractedValue, emit) -> None:
        for item in extracted.value:
            group = _stable(item)
            term: TermRange = item.value
            if term.min_months is not None:
                emit(
                    FieldPath.TERM_MINIMUM_MONTHS,
                    term.min_months,
                    extracted,
                    conditions=item.conditions,
                    group=group,
                    number=term.min_months,
                    unit="months",
                )
            if term.max_months is not None:
                emit(
                    FieldPath.TERM_MAXIMUM_MONTHS,
                    term.max_months,
                    extracted,
                    conditions=item.conditions,
                    group=group,
                    number=term.max_months,
                    unit="months",
                )
            if term.indefinite:
                emit(
                    FieldPath.TERM_INDEFINITE,
                    True,
                    extracted,
                    conditions=item.conditions,
                    group=group,
                )
            if term.end_condition:
                emit(
                    FieldPath.TERM_END_CONDITION,
                    term.end_condition,
                    extracted,
                    conditions=item.conditions,
                    group=group,
                )

    @staticmethod
    def _profile(
        snapshot: SnapshotAttempt,
        product: LoanProduct,
        display_name: str,
        aliases: tuple[str, ...],
    ) -> OfferingProfile:
        def values(extracted: ExtractedValue) -> tuple[Any, ...]:
            return (
                tuple(extracted.value or ())
                if extracted.status is ExtractionStatus.FOUND
                else ()
            )

        property_market = getattr(product.details, "property_market", None)
        return OfferingProfile(
            snapshot_id=snapshot.id,
            bank=snapshot.bank,
            product=snapshot.product,
            offering_id=snapshot.offering_id,
            display_name=display_name,
            extracted_name=product.product_name.value
            if product.product_name.status is ExtractionStatus.FOUND
            else None,
            formal_names=values(product.formal_terms_names),
            aliases=aliases,
            category=product.category.value,
            purposes=values(product.purpose),
            variants=tuple(_json_value(item) for item in values(product.variants)),
            property_market=property_market.value.value
            if property_market and property_market.status is ExtractionStatus.FOUND
            else None,
            accepted_at=snapshot.accepted_at,
        )

    @staticmethod
    def _units(
        snapshot: SnapshotAttempt,
        profile: OfferingProfile,
        facts: list[TariffFact],
        language: str,
    ) -> tuple[RetrievalUnit, ...]:
        units: list[RetrievalUnit] = []
        supported = [
            fact
            for fact in facts
            if fact.status is ExtractionStatus.FOUND and fact.evidence
        ]
        profile_facts = [
            fact for fact in supported if fact.field_path.value.startswith("identity.")
        ]
        if profile_facts:
            content = _clean(
                ". ".join(
                    [profile.display_name, *[str(fact.value) for fact in profile_facts]]
                )
            )
            units.append(
                StructuredTariffProjector._unit(
                    snapshot,
                    RetrievalUnitKind.PROFILE,
                    profile_facts,
                    content,
                    language,
                    profile.display_name,
                    " ".join(profile.aliases),
                    "",
                )
            )
        for fact in supported:
            conditions = "; ".join(_stable(item) for item in fact.conditions)
            detail = f"{fact.field_path.value}: {fact.value}"
            if fact.currency:
                detail += f" {fact.currency}"
            if fact.unit:
                detail += f" ({fact.unit})"
            if conditions:
                detail += f". Conditions: {conditions}"
            content = _clean(f"{profile.display_name}. {detail}")
            units.append(
                StructuredTariffProjector._unit(
                    snapshot,
                    RetrievalUnitKind.FIELD_DETAIL,
                    [fact],
                    content,
                    language,
                    profile.display_name,
                    " ".join(profile.aliases),
                    _clean(detail),
                )
            )
        return tuple(units)

    @staticmethod
    def _unit(
        snapshot: SnapshotAttempt,
        kind: RetrievalUnitKind,
        facts: list[TariffFact],
        content: str,
        language: str,
        identity: str,
        aliases: str,
        detail: str,
    ) -> RetrievalUnit:
        fact_ids = tuple(fact.fact_id for fact in facts if fact.fact_id)
        evidence_ids = tuple(
            dict.fromkeys(item.evidence_id for fact in facts for item in fact.evidence)
        )
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return RetrievalUnit(
            unit_id=_hash(str(snapshot.id), kind.value, *fact_ids),
            snapshot_id=snapshot.id,
            offering_id=snapshot.offering_id,
            kind=kind,
            field_paths=tuple(dict.fromkeys(fact.field_path for fact in facts)),
            fact_ids=fact_ids,
            evidence_ids=evidence_ids,
            language=language,
            identity_text=_clean(identity),
            alias_purpose_text=_clean(aliases),
            detail_text=detail,
            content=content,
            content_sha256=content_hash,
            renderer_version=RENDERER_VERSION,
        )
