from __future__ import annotations

import hashlib
import logging
from collections import Counter
from collections.abc import Sequence
from datetime import date
from typing import Protocol

from app.config import SourceDiscoverySettings
from app.domain.acquisition import SourceType
from app.domain.models import ProductType
from app.domain.normalization import NormalizedSourceBundle, SourceReference
from app.domain.pdf_extraction import (
    PdfAdmissionRelevance,
    PdfAdmissionRole,
    PdfTemporalStatus,
)
from app.domain.source_discovery import (
    Authority,
    CandidateLayout,
    DecisionSource,
    DiscoveryBatch,
    DiscoveryBatchResponse,
    DiscoveryCandidate,
    DiscoveryPromptItem,
    DiscoveryScope,
    EffectivePeriod,
    ExtractionContext,
    ExtractionContextItem,
    InformationRole,
    OfferingContext,
    PriorAssessment,
    ProductAssociation,
    Relevance,
    SourceAssessment,
    SourceDiscoveryPlan,
    SourceDiscoveryResult,
    TemporalStatus,
)
from app.repositories.contracts import SourceDiscoveryRepository
from app.services.discovery_classifier import is_model_fallback_error
from app.services.discovery_prefilter import build_discovery_candidates
from app.services.failure_mapping import describe_failure
from app.services.model_call_usage import (
    PostgresModelCallUsageRepository,
    record_model_cache_hit,
)

logger = logging.getLogger(__name__)


def offering_context_for(
    bundle: NormalizedSourceBundle, product: ProductType
) -> OfferingContext:
    """The catalog offering whose seed page this bundle is, for tools and demos.

    The pipeline builds the context from the catalog entry it runs; this is for
    callers that only hold a bundle. A page that is not in the catalog gets a
    context named after the page itself.
    """
    from app.config.seed_catalog import load_seed_catalog

    page = next(
        (
            document
            for document in bundle.documents
            if document.source_type is SourceType.PAGE
        ),
        bundle.documents[0],
    )
    wanted = str(bundle.canonical_url).rstrip("/")
    for entry in load_seed_catalog().offerings:
        if entry.product is product and str(entry.seed_url).rstrip("/") == wanted:
            return OfferingContext.from_catalog_entry(entry, page_title=page.name)
    return OfferingContext(
        offering_id="unlisted",
        product=product,
        display_name=page.name[:200],
        seed_url=bundle.canonical_url,
        page_title=page.name,
    )


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
        offering_id: str,
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
                    (
                        product.value,
                        offering_id,
                        policy_version,
                        prompt_version,
                        model_name,
                        fingerprint,
                    )
                )
            )
            is not None
        }

    async def get_structural_priors(
        self,
        *,
        product: ProductType,
        offering_id: str,
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
                    (
                        product.value,
                        offering_id,
                        policy_version,
                        prompt_version,
                        model_name,
                        fingerprint,
                    )
                )
            )
            is not None
        }

    async def save(
        self,
        *,
        product: ProductType,
        offering_id: str,
        policy_version: str,
        prompt_version: str,
        model_name: str,
        assessments: Sequence[SourceAssessment],
    ) -> None:
        for assessment in assessments:
            exact_key = (
                product.value,
                offering_id,
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
        usage_repository: PostgresModelCallUsageRepository | None = None,
    ) -> None:
        self._classifier = classifier
        self._repository = repository
        self._settings = settings
        self._model_name = model_name
        self._usage_repository = usage_repository

    @property
    def model_name(self) -> str:
        return self._model_name

    async def plan(
        self, bundle: NormalizedSourceBundle, offering: OfferingContext
    ) -> SourceDiscoveryPlan:
        plan, _ = await self._plan(bundle, offering)
        return plan

    async def _plan(
        self, bundle: NormalizedSourceBundle, offering: OfferingContext
    ) -> tuple[SourceDiscoveryPlan, tuple[DiscoveryCandidate, ...]]:
        product = offering.product
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
            offering_id=offering.offering_id,
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
            offering_id=offering.offering_id,
            policy_version=self._settings.policy_version,
            prompt_version=self._settings.prompt_version,
            model_name=self._model_name,
            structural_fingerprints=[
                item.structural_fingerprint for item in llm_candidates
            ],
        )
        # A prior is a hint about *this* section. When two sections on the
        # page share a structural fingerprint, the stored prior may belong to
        # the other one, so neither gets it.
        structural_counts = Counter(item.structural_fingerprint for item in candidates)
        priors = {
            fingerprint: prior
            for fingerprint, prior in priors.items()
            if structural_counts[fingerprint] == 1
        }
        batches = _build_batches(
            offering,
            llm_candidates,
            priors,
            self._settings,
        )
        plan = SourceDiscoveryPlan(
            product=product,
            offering_id=offering.offering_id,
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
        return plan, candidates

    async def discover(
        self,
        bundle: NormalizedSourceBundle,
        offering: OfferingContext,
        *,
        as_of: date | None = None,
    ) -> SourceDiscoveryResult:
        product = offering.product
        plan, all_candidates = await self._plan(bundle, offering)
        await record_model_cache_hit(
            self._usage_repository,
            stage="discovery.classification",
            operation="generate_content",
            model_id=self._model_name,
            input_count=len(plan.cache_hits),
        )
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
                raise ValueError(
                    "classifier response IDs do not exactly match batch IDs"
                )
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
                offering_id=offering.offering_id,
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
        candidates_by_id = {
            candidate.source_id: candidate for candidate in all_candidates
        }
        inherited = _inherited_assessments(direct, candidates_by_id, bundle)
        context = _build_extraction_context(product, direct, candidates_by_id)
        return SourceDiscoveryResult(
            product=product,
            offering_id=offering.offering_id,
            input_content_hash=plan.input_content_hash,
            policy_version=plan.policy_version,
            prompt_version=plan.prompt_version,
            model_name=plan.model_name,
            assessments=(*direct, *inherited),
            extraction_context=context,
            llm_batch_count=len(plan.batches),
            reused_assessment_count=len(plan.cache_hits),
        )


class FallbackSourceDiscoveryService:
    """Try each configured discovery model in turn before failing the offering.

    A retired model answers a permanent 404, which the classifier's retry loop
    cannot help with; without a chain that ends the whole offering as
    `source.model_failed`. Each model gets its own service so the assessment
    cache namespace and the persisted `model_name` stay the model that actually
    answered.
    """

    def __init__(self, services: Sequence[SourceDiscoveryService]) -> None:
        if not services:
            raise ValueError("source discovery needs at least one model")
        self._services = tuple(services)

    async def discover(
        self,
        bundle: NormalizedSourceBundle,
        offering: OfferingContext,
        *,
        as_of: date | None = None,
    ) -> SourceDiscoveryResult:
        last = len(self._services) - 1
        for index, service in enumerate(self._services):
            try:
                return await service.discover(bundle, offering, as_of=as_of)
            except Exception as exc:
                if index == last or not is_model_fallback_error(exc):
                    raise
                logger.warning(
                    "Source-discovery model %s failed (%s); falling back to %s",
                    service.model_name,
                    describe_failure(exc),
                    self._services[index + 1].model_name,
                )
        raise AssertionError("source-discovery model sequence exhausted")


def _rule_assessment(candidate: DiscoveryCandidate) -> SourceAssessment | None:
    values: (
        tuple[
            ProductAssociation,
            InformationRole,
            Relevance,
            Authority,
            TemporalStatus,
            str,
        ]
        | None
    ) = None
    if (
        candidate.scope is DiscoveryScope.DOCUMENT
        and candidate.source_type is not SourceType.PAGE
        and not candidate.member_source_ids
    ):
        # A linked document with no content: skipped before transcription, or
        # its transcription failed. There is nothing for a model to read, and
        # nothing for extraction to use; the normalization warning reports why.
        values = _no_content_values(candidate)
    elif (
        candidate.scope is DiscoveryScope.DOCUMENT
        and candidate.source_type is SourceType.PDF
        and candidate.pdf_admission is not None
        and candidate.pdf_admission.relevance is PdfAdmissionRelevance.RELEVANT
    ):
        admission = candidate.pdf_admission
        role = {
            PdfAdmissionRole.PRODUCT_TERMS: InformationRole.PRODUCT_TERMS,
            PdfAdmissionRole.FEES: InformationRole.FEES,
            PdfAdmissionRole.LEGAL_DISCLOSURE: InformationRole.LEGAL_DISCLOSURE,
            PdfAdmissionRole.OTHER: InformationRole.OTHER,
        }[admission.role]
        temporal = {
            PdfTemporalStatus.CURRENT: TemporalStatus.CURRENT,
            PdfTemporalStatus.HISTORICAL: TemporalStatus.POSSIBLY_STALE,
            PdfTemporalStatus.FUTURE: TemporalStatus.FUTURE,
            PdfTemporalStatus.TIME_BOUNDED: TemporalStatus.TIME_BOUNDED,
            PdfTemporalStatus.UNKNOWN: TemporalStatus.UNKNOWN,
        }[admission.temporal_status]
        association = {
            PdfTemporalStatus.HISTORICAL: ProductAssociation.HISTORICAL_VERSION,
            PdfTemporalStatus.FUTURE: ProductAssociation.FUTURE_VERSION,
        }.get(admission.temporal_status, ProductAssociation.CURRENT_PRODUCT)
        return SourceAssessment(
            source_id=candidate.source_id,
            document_id=candidate.document_id,
            scope=candidate.scope,
            product_association=association,
            role=role,
            relevance=Relevance.RELEVANT,
            authority=Authority.OFFICIAL_TERMS,
            temporal_status=temporal,
            effective_periods=tuple(
                EffectivePeriod(raw=item.raw, start=item.start, end=item.end)
                for item in admission.effective_periods
            ),
            reason=admission.reason,
            decision_source=DecisionSource.RULE,
            input_fingerprint=candidate.content_fingerprint,
            structural_fingerprint=candidate.structural_fingerprint,
            source_refs=candidate.source_refs,
        )
    elif (
        candidate.scope is DiscoveryScope.DOCUMENT
        and candidate.source_type is SourceType.PAGE
    ):
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
    elif candidate.layout is CandidateLayout.SITE_CHROME:
        values = (
            ProductAssociation.GLOBAL_NAVIGATION,
            InformationRole.NAVIGATION,
            Relevance.IRRELEVANT,
            Authority.UNKNOWN,
            TemporalStatus.UNKNOWN,
            "Blocks sit in the site's navigation, banner or footer.",
        )
    elif candidate.layout is CandidateLayout.PAGE_HEADER:
        values = (
            ProductAssociation.GLOBAL_NAVIGATION,
            InformationRole.NAVIGATION,
            Relevance.IRRELEVANT,
            Authority.UNKNOWN,
            TemporalStatus.UNKNOWN,
            "Unheaded blocks above the page's first heading are the site header.",
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


def _no_content_values(
    candidate: DiscoveryCandidate,
) -> tuple[
    ProductAssociation, InformationRole, Relevance, Authority, TemporalStatus, str
]:
    admission = candidate.pdf_admission
    if (
        admission is not None
        and admission.temporal_status is PdfTemporalStatus.HISTORICAL
    ):
        return (
            ProductAssociation.HISTORICAL_VERSION,
            InformationRole.OTHER,
            Relevance.IRRELEVANT,
            Authority.UNKNOWN,
            TemporalStatus.POSSIBLY_STALE,
            "Superseded edition, skipped before transcription; it has no content.",
        )
    if (
        admission is not None
        and admission.relevance is PdfAdmissionRelevance.IRRELEVANT
    ):
        return (
            ProductAssociation.UNKNOWN,
            InformationRole.OTHER,
            Relevance.IRRELEVANT,
            Authority.UNKNOWN,
            TemporalStatus.UNKNOWN,
            "Off-topic link metadata, skipped before transcription; it has no content.",
        )
    return (
        ProductAssociation.UNKNOWN,
        InformationRole.OTHER,
        Relevance.IRRELEVANT,
        Authority.UNKNOWN,
        TemporalStatus.UNKNOWN,
        f"Linked document has no extracted content ({candidate.extraction_method}).",
    )


def _build_batches(
    offering: OfferingContext,
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
                    id=f"batch_{len(batches):03d}",
                    product=offering.product,
                    offering=offering,
                    items=tuple(current),
                )
            )
            current = []
            current_chars = 0
        current.append(item)
        current_chars += len(content)
    if current:
        batches.append(
            DiscoveryBatch(
                id=f"batch_{len(batches):03d}",
                product=offering.product,
                offering=offering,
                items=tuple(current),
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
                        "scope": (
                            DiscoveryScope.TABLE
                            if "::table::" in member_id
                            else DiscoveryScope.BLOCK
                        ),
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
        for table in document.tables:
            if table.source_refs:
                values[f"{document.id}::table::{table.id}"] = table.source_refs[0]
    return values


def _build_extraction_context(
    product: ProductType,
    direct: tuple[SourceAssessment, ...],
    candidates: dict[str, DiscoveryCandidate],
) -> ExtractionContext:
    items: list[ExtractionContextItem] = []
    for assessment in direct:
        if (
            assessment.relevance is Relevance.IRRELEVANT
            or assessment.temporal_status
            in {
                TemporalStatus.POSSIBLY_STALE,
                TemporalStatus.FUTURE,
            }
        ):
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
