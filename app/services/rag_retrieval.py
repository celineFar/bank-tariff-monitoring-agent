from __future__ import annotations

import math
import re
from collections.abc import Iterable

from app.config.models import RagSettings
from app.domain.retrieval import (
    RankExplanation,
    RetrievalCandidate,
    RetrievalHit,
    RetrievalRequest,
    RetrievalResult,
    RetrievalStatus,
    TariffField,
)
from app.repositories.contracts import HybridRetrievalRepository
from app.services.knowledge_index import QueryEmbeddingProvider

_LEXICAL_WEIGHT = 0.45
_VECTOR_WEIGHT = 0.55
_RRF_K = 60
_RELEVANCE_WEIGHT = 0.70
_RRF_WEIGHT = 0.30
_CANDIDATE_MULTIPLIER = 4
_MIN_CANDIDATE_POOL = 20
_MAX_CANDIDATE_POOL = 200
_OVERLAP_THRESHOLD = 0.85
_TOKEN = re.compile(r"\w+", re.UNICODE)

_FIELD_TERMS: dict[TariffField, tuple[str, ...]] = {
    TariffField.AMOUNT: ("loan amount", "amount", "վարկի գումար", "գումար"),
    TariffField.TERM: ("loan term", "term", "ժամկետ"),
    TariffField.NOMINAL_RATE: (
        "nominal interest rate",
        "nominal rate",
        "անվանական տոկոսադրույք",
    ),
    TariffField.EFFECTIVE_RATE: (
        "effective interest rate",
        "effective rate",
        "փաստացի տոկոսադրույք",
    ),
    TariffField.APPLICATION_FEE: (
        "application fee",
        "հայտի վճար",
        "դիմումի վճար",
    ),
    TariffField.DISBURSEMENT_FEE: (
        "disbursement fee",
        "տրամադրման վճար",
    ),
    TariffField.SERVICE_FEE: ("service fee", "սպասարկման վճար"),
    TariffField.COLLATERAL: (
        "collateral",
        "security",
        "գրավ",
        "ապահովվածություն",
    ),
    TariffField.SALARY_PRIVILEGES: (
        "salary customer privileges",
        "salary customer",
        "աշխատավարձային հաճախորդ",
        "արտոնություն",
    ),
}


class RagRetriever:
    def __init__(
        self,
        embedding_provider: QueryEmbeddingProvider,
        repository: HybridRetrievalRepository,
        settings: RagSettings,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._repository = repository
        self._settings = settings

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        lexical_query = _expanded_query(request)
        embedding = tuple(
            float(value)
            for value in await self._embedding_provider.embed_query(
                _semantic_query(request)
            )
        )
        if len(embedding) != self._embedding_provider.dimensions:
            raise ValueError("query embedding dimensions do not match the index schema")
        if not all(math.isfinite(value) for value in embedding):
            raise ValueError("query embedding contains a non-finite value")

        candidate_limit = min(
            _MAX_CANDIDATE_POOL,
            max(
                _MIN_CANDIDATE_POOL,
                self._settings.retrieval_top_k * _CANDIDATE_MULTIPLIER,
            ),
        )
        candidates = tuple(
            await self._repository.search_candidates(
                bank=request.bank,
                product=request.product,
                lexical_query=lexical_query,
                query_embedding=embedding,
                limit=candidate_limit,
            )
        )
        ranked = sorted(
            (_to_hit(candidate) for candidate in candidates),
            key=lambda hit: (
                -hit.final_score,
                -hit.vector_score,
                -hit.lexical_score,
                hit.chunk_id,
            ),
        )
        relevant = (
            hit
            for hit in ranked
            if hit.final_score >= self._settings.retrieval_min_score
        )
        hits = tuple(_deduplicate_overlaps(relevant, self._settings.retrieval_top_k))
        if not hits:
            return RetrievalResult(
                status=RetrievalStatus.INSUFFICIENT_EVIDENCE,
                hits=(),
                reason=(
                    "No active chunk for the requested bank and product met "
                    "the minimum relevance score of "
                    f"{self._settings.retrieval_min_score:.3f}."
                ),
                candidates_considered=len(candidates),
            )
        return RetrievalResult(
            status=RetrievalStatus.FOUND,
            hits=hits,
            candidates_considered=len(candidates),
        )


def _expanded_query(request: RetrievalRequest) -> str:
    terms = [request.query]
    for field in request.fields:
        terms.extend(_FIELD_TERMS[field])
    unique_terms = tuple(dict.fromkeys(term.strip() for term in terms if term.strip()))
    return " OR ".join(_quote_websearch_term(term) for term in unique_terms)


def _semantic_query(request: RetrievalRequest) -> str:
    field_names = ", ".join(field.value.replace("_", " ") for field in request.fields)
    return f"{request.query}\nTariff fields: {field_names}"


def _quote_websearch_term(term: str) -> str:
    escaped = term.replace('"', " ").strip()
    return f'"{escaped}"' if " " in escaped else escaped


def _to_hit(candidate: RetrievalCandidate) -> RetrievalHit:
    lexical_rrf = (
        _LEXICAL_WEIGHT / (_RRF_K + candidate.lexical_rank)
        if candidate.lexical_rank is not None
        else 0.0
    )
    vector_rrf = (
        _VECTOR_WEIGHT / (_RRF_K + candidate.vector_rank)
        if candidate.vector_rank is not None
        else 0.0
    )
    best_possible_rrf = (_LEXICAL_WEIGHT + _VECTOR_WEIGHT) / (_RRF_K + 1)
    rrf_score = min(1.0, (lexical_rrf + vector_rrf) / best_possible_rrf)
    relevance_score = (
        _LEXICAL_WEIGHT * candidate.lexical_score
        + _VECTOR_WEIGHT * candidate.vector_score
    )
    final_score = min(
        1.0,
        _RELEVANCE_WEIGHT * relevance_score + _RRF_WEIGHT * rrf_score,
    )
    explanation = RankExplanation(
        lexical_rank=candidate.lexical_rank,
        vector_rank=candidate.vector_rank,
        lexical_weight=_LEXICAL_WEIGHT,
        vector_weight=_VECTOR_WEIGHT,
        rrf_k=_RRF_K,
        rrf_score=rrf_score,
        relevance_score=relevance_score,
        formula="0.70 * weighted_relevance + 0.30 * normalized_weighted_rrf",
    )
    return RetrievalHit(
        **candidate.model_dump(exclude={"lexical_rank", "vector_rank"}),
        final_score=final_score,
        rank_explanation=explanation,
    )


def _deduplicate_overlaps(
    ranked_hits: Iterable[RetrievalHit], top_k: int
) -> list[RetrievalHit]:
    selected: list[RetrievalHit] = []
    for hit in ranked_hits:
        if any(_is_overlapping(hit, existing) for existing in selected):
            continue
        selected.append(hit)
        if len(selected) == top_k:
            break
    return selected


def _is_overlapping(left: RetrievalHit, right: RetrievalHit) -> bool:
    if left.document_id != right.document_id:
        return False
    left_tokens = set(_TOKEN.findall(left.content.casefold()))
    right_tokens = set(_TOKEN.findall(right.content.casefold()))
    if not left_tokens or not right_tokens:
        return left.content.strip().casefold() == right.content.strip().casefold()
    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
    return overlap >= _OVERLAP_THRESHOLD
