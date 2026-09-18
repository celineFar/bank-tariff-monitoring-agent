from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Protocol

from app.config import SourceDiscoverySettings
from app.domain.acquisition import SourceType
from app.domain.models import ProductType
from app.domain.normalization import NormalizedSourceBundle, SourceReference
from app.domain.source_discovery import (
    Authority,
    DecisionSource,
    DiscoveryBatch,
    DiscoveryBatchResponse,
    DiscoveryCandidate,
    DiscoveryPromptItem,
    DiscoveryScope,
    ExtractionContext,
    ExtractionContextItem,
    InformationRole,
    PriorAssessment,
    ProductAssociation,
    Relevance,
    SourceAssessment,
    SourceDiscoveryPlan,
    SourceDiscoveryResult,
    TemporalStatus,
)
from app.repositories.contracts import SourceDiscoveryRepository
from app.services.discovery_prefilter import build_discovery_candidates


class SourceDiscoveryClassifier(Protocol):
    async def classify(self, batch: DiscoveryBatch) -> DiscoveryBatchResponse: ...


class InMemorySourceDiscoveryRepository:
    """Small development/test cache with the same semantics as PostgreSQL."""

    def __init__(self) -> None:
        self._exact: dict[tuple[str, ...], SourceAssessment] = {}
        self._structural: dict[tuple[str, ...], SourceAssessment] = {}

    async def get_exact(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        content_fingerprints: Sequence[str],
    ) -> dict[str, SourceAssessment]:
        return {
            fingerprint: assessment
            for fingerprint in content_fingerprints
            if (
                assessment := self._exact.get(
                    (product.value, policy_version, prompt_version, model_name, fingerprint)
                )
            )
            is not None
        }

    async def get_structural_priors(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        structural_fingerprints: Sequence[str],
    ) -> dict[str, SourceAssessment]:
        return {
            fingerprint: assessment
            for fingerprint in structural_fingerprints
            if (
                assessment := self._structural.get(
                    (product.value, policy_version, prompt_version, model_name, fingerprint)
                )
            )
            is not None
        }

    async def save(
        self,
        *,
        product: ProductType,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        assessments: Sequence[SourceAssessment],
    ) -> None:
        for assessment in assessments:
            exact_key = (
                product.value,
                policy_version,
                prompt_version,
                model_name,
                assessment.input_fingerprint,
            )
            structural_key = (*exact_key[:-1], assessment.structural_fingerprint)
            self._exact[exact_key] = assessment
            self._structural[structural_key] = assessment


class SourceDiscoveryService:
    def __init__(
        self,
        classifier: SourceDiscoveryClassifier | None,
        repository: SourceDiscoveryRepository,
        settings: SourceDiscoverySettings,
        *,
        model_name: str,
    ) -> None:
        self._classifier = classifier
        self._repository = repository
        self._settings = settings
        self._model_name = model_name

    async def plan(
        self, bundle: NormalizedSourceBundle, product: ProductType
    ) -> SourceDiscoveryPlan:
        candidates = build_discovery_candidates(bundle)
        rule_assessments: list[SourceAssessment] = []
        unresolved: list[DiscoveryCandidate] = []
        for candidate in candidates:
            if assessment := _rule_assessment(candidate):
                rule_assessments.append(assessment)
            else:
                unresolved.append(candidate)

        exact = await self._repository.get_exact(
            product=product,
            policy_version=self._settings.policy_version,
            prompt_version=self._settings.prompt_version,
            model_name=self._model_name,
            content_fingerprints=[item.content_fingerprint for item in unresolved],
        )
        cache_hits: list[SourceAssessment] = []
        llm_candidates: list[DiscoveryCandidate] = []
        for candidate in unresolved:
            if cached := exact.get(candidate.content_fingerprint):
                cache_hits.append(
                    cached.model_copy(
                        update={
                            "source_id": candidate.source_id,
                            "document_id": candidate.document_id,
                            "scope": candidate.scope,
                            "decision_source": DecisionSource.CACHE,
                            "source_refs": candidate.source_refs,
                        }
                    )
                )
            else:
                llm_candidates.append(candidate)

        priors = await self._repository.get_structural_priors(
            product=product,
            policy_version=self._settings.policy_version,
            prompt_version=self._settings.prompt_version,
            model_name=self._model_name,
            structural_fingerprints=[
                item.structural_fingerprint for item in llm_candidates
            ],
        )
        batches = _build_batches(
            product,
            llm_candidates,
            priors,
            self._settings,
        )
        return SourceDiscoveryPlan(
            product=product,
            canonical_url=str(bundle.canonical_url),
            input_content_hash=bundle.acquisition_content_hash,
            policy_version=self._settings.policy_version,
            prompt_version=self._settings.prompt_version,
            model_name=self._model_name,
            deterministic_assessments=tuple(rule_assessments),
            cache_hits=tuple(cache_hits),
            llm_candidates=tuple(llm_candidates),
            batches=batches,
            inherited_item_count=sum(
                len(candidate.member_source_ids) for candidate in candidates
            ),
        )

    async def discover(
        self, bundle: NormalizedSourceBundle, product: ProductType
    ) -> SourceDiscoveryResult:
        plan = await self.plan(bundle, product)
        if plan.batches and self._classifier is None:
            raise RuntimeError("source discovery has LLM candidates but no classifier")

        candidate_by_id = {
            candidate.source_id: candidate for candidate in plan.llm_candidates
        }
        llm_assessments: list[SourceAssessment] = []
        for batch in plan.batches:
            assert self._classifier is not None
            response = await self._classifier.classify(batch)
            expected = {item.source_id for item in batch.items}
            received = {item.source_id for item in response.items}
            if received != expected or len(response.items) != len(expected):
                raise ValueError("classifier response IDs do not exactly match batch IDs")
            for item in response.items:
                candidate = candidate_by_id[item.source_id]
                llm_assessments.append(
                    SourceAssessment(
                        **item.model_dump(),
                        document_id=candidate.document_id,
                        scope=candidate.scope,
                        decision_source=DecisionSource.LLM,
                        input_fingerprint=candidate.content_fingerprint,
                        structural_fingerprint=candidate.structural_fingerprint,
                        source_refs=candidate.source_refs,
                    )
                )

        if llm_assessments:
            await self._repository.save(
                product=product,
                policy_version=plan.policy_version,
                prompt_version=plan.prompt_version,
                model_name=plan.model_name,
                assessments=llm_assessments,
            )

        direct = (
            *plan.deterministic_assessments,
            *plan.cache_hits,
            *llm_assessments,
        )
        all_candidates = build_discovery_candidates(bundle)
        candidates_by_id = {candidate.source_id: candidate for candidate in all_candidates}
        inherited = _inherited_assessments(direct, candidates_by_id, bundle)
        context = _build_extraction_context(product, direct, candidates_by_id)
        return SourceDiscoveryResult(
            product=product,
            input_content_hash=plan.input_content_hash,
            policy_version=plan.policy_version,
            prompt_version=plan.prompt_version,
            model_name=plan.model_name,
            assessments=(*direct, *inherited),
            extraction_context=context,
            llm_batch_count=len(plan.batches),
            reused_assessment_count=len(plan.cache_hits),
        )


def _rule_assessment(candidate: DiscoveryCandidate) -> SourceAssessment | None:
    values: tuple[
        ProductAssociation,
        InformationRole,
        Relevance,
        Authority,
        TemporalStatus,
        str,
    ] | None = None
    if candidate.scope is DiscoveryScope.DOCUMENT and candidate.source_type is SourceType.PAGE:
        values = (
            ProductAssociation.CURRENT_PRODUCT,
            InformationRole.PRODUCT_DESCRIPTION,
            Relevance.RELEVANT,
            Authority.OFFICIAL_PRODUCT_CONTENT,
            TemporalStatus.CURRENT,
            "Canonical product page identity is known from the requested product URL.",
        )
    elif candidate.all_members_hidden:
        values = (
            ProductAssociation.UNKNOWN,
            InformationRole.OTHER,
            Relevance.IRRELEVANT,
            Authority.UNKNOWN,
            TemporalStatus.UNKNOWN,
            "All members were marked hidden by browser acquisition.",
        )
    elif candidate.scope is DiscoveryScope.API_PAYLOAD and _is_template_payload(candidate):
        values = (
            ProductAssociation.GENERIC_BANK_INFORMATION,
            InformationRole.OTHER,
            Relevance.IRRELEVANT,
            Authority.UNKNOWN,
            TemporalStatus.UNKNOWN,
            "Payload is a reusable HTML presentation template, not product data.",
        )
    elif _is_navigation(candidate):
        values = (
            ProductAssociation.GLOBAL_NAVIGATION,
            InformationRole.NAVIGATION,
            Relevance.IRRELEVANT,
            Authority.UNKNOWN,
            TemporalStatus.UNKNOWN,
            "Unheaded content matches the repeated global navigation structure.",
        )
    if values is None:
        return None
    association, role, relevance, authority, temporal, reason = values
    return SourceAssessment(
        source_id=candidate.source_id,
        document_id=candidate.document_id,
        scope=candidate.scope,
        product_association=association,
        role=role,
        relevance=relevance,
        authority=authority,
        temporal_status=temporal,
        reason=reason,
        decision_source=DecisionSource.RULE,
        input_fingerprint=candidate.content_fingerprint,
        structural_fingerprint=candidate.structural_fingerprint,
        source_refs=candidate.source_refs,
    )


def _is_template_payload(candidate: DiscoveryCandidate) -> bool:
    value = candidate.title.casefold()
    return ".html" in value and any(
        token in value for token in ("/contentthemes/", "templates.view.html")
    )


def _is_navigation(candidate: DiscoveryCandidate) -> bool:
    if candidate.scope is not DiscoveryScope.SECTION or candidate.heading_path:
        return False
    text = candidate.context_text.casefold()
    markers = (
        "personal",
        "business",
        "investment",
        "about bank",
        "branches",
        "cards",
        "loans",
        "accounts",
        "contact center",
    )
    return sum(marker in text for marker in markers) >= 4


def _build_batches(
    product: ProductType,
    candidates: list[DiscoveryCandidate],
    priors: dict[str, SourceAssessment],
    settings: SourceDiscoverySettings,
) -> tuple[DiscoveryBatch, ...]:
    batches: list[DiscoveryBatch] = []
    current: list[DiscoveryPromptItem] = []
    current_chars = 0
    for candidate in candidates:
        content = candidate.context_text[: settings.max_chars_per_item]
        item = DiscoveryPromptItem(
            source_id=candidate.source_id,
            scope=candidate.scope,
            source_type=candidate.source_type,
            title=candidate.title,
            heading_path=candidate.heading_path,
            content=content,
            mime_type=candidate.mime_type,
            extraction_method=candidate.extraction_method,
            quality_score=candidate.quality_score,
            prior_assessment=_prior(priors.get(candidate.structural_fingerprint)),
        )
        if current and (
            len(current) >= settings.max_items_per_batch
            or current_chars + len(content) > settings.max_chars_per_batch
        ):
            batches.append(
                DiscoveryBatch(
                    id=f"batch_{len(batches):03d}", product=product, items=tuple(current)
                )
            )
            current = []
            current_chars = 0
        current.append(item)
        current_chars += len(content)
    if current:
        batches.append(
            DiscoveryBatch(
                id=f"batch_{len(batches):03d}", product=product, items=tuple(current)
            )
        )
    return tuple(batches)


def _prior(assessment: SourceAssessment | None) -> PriorAssessment | None:
    if assessment is None:
        return None
    return PriorAssessment(
        product_association=assessment.product_association,
        role=assessment.role,
        relevance=assessment.relevance,
        authority=assessment.authority,
        temporal_status=assessment.temporal_status,
        effective_periods=assessment.effective_periods,
        conditions=assessment.conditions,
        reason=assessment.reason,
    )


def _inherited_assessments(
    direct: tuple[SourceAssessment, ...],
    candidates: dict[str, DiscoveryCandidate],
    bundle: NormalizedSourceBundle,
) -> tuple[SourceAssessment, ...]:
    refs = _member_references(bundle)
    inherited: list[SourceAssessment] = []
    for assessment in direct:
        candidate = candidates[assessment.source_id]
        for member_id in candidate.member_source_ids:
            reference = refs.get(member_id)
            if reference is None:
                continue
            fingerprint = hashlib.sha256(
                f"{assessment.input_fingerprint}\x1f{member_id}".encode()
            ).hexdigest()
            inherited.append(
                assessment.model_copy(
                    update={
                        "source_id": member_id,
                        "scope": DiscoveryScope.BLOCK,
                        "decision_source": DecisionSource.INHERITED,
                        "inherited_from": assessment.source_id,
                        "input_fingerprint": fingerprint,
                        "source_refs": (reference,),
                    }
                )
            )
    return tuple(inherited)


def _member_references(
    bundle: NormalizedSourceBundle,
) -> dict[str, SourceReference]:
    values: dict[str, SourceReference] = {}
    for document in bundle.documents:
        for block in document.blocks:
            if block.source_refs:
                values[f"{document.id}::block::{block.id}"] = block.source_refs[0]
    return values


def _build_extraction_context(
    product: ProductType,
    direct: tuple[SourceAssessment, ...],
    candidates: dict[str, DiscoveryCandidate],
) -> ExtractionContext:
    items: list[ExtractionContextItem] = []
    for assessment in direct:
        if assessment.relevance is Relevance.IRRELEVANT:
            continue
        candidate = candidates[assessment.source_id]
        items.append(
            ExtractionContextItem(
                source_id=assessment.source_id,
                document_id=assessment.document_id,
                scope=assessment.scope,
                role=assessment.role,
                authority=assessment.authority,
                temporal_status=assessment.temporal_status,
                precedence=_precedence(assessment),
                text=candidate.context_text,
                conditions=assessment.conditions,
                effective_periods=assessment.effective_periods,
                source_refs=candidate.source_refs,
            )
        )
    items.sort(key=lambda item: (item.precedence, item.document_id, item.source_id))
    return ExtractionContext(product=product, items=tuple(items))


def _precedence(assessment: SourceAssessment) -> int:
    if assessment.authority is Authority.OFFICIAL_TERMS:
        return 1
    if assessment.scope is DiscoveryScope.TABLE and assessment.role in {
        InformationRole.PRODUCT_TERMS,
        InformationRole.PRICING,
        InformationRole.FEES,
    }:
        return 2
    if assessment.authority is Authority.OFFICIAL_PRODUCT_CONTENT:
        return 3
    if assessment.authority is Authority.OFFICIAL_FAQ:
        return 4
    if assessment.authority is Authority.OFFICIAL_CAMPAIGN_CONTENT:
        return 5
    return 6
