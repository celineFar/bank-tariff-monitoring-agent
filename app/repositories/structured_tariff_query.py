"""Scoped reads of active, accepted structured tariff projections."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import SnapshotChangeSet
from app.domain.structured_tariffs import (
    FactEvidence,
    FieldPath,
    OfferingDataState,
    OfferingProfile,
    RetrievalUnit,
    TariffFact,
)
from app.services.retrieval_trace import record, record_text


def _decoded(value):
    return json.loads(value) if isinstance(value, str) else value


def _without_none(value):
    if isinstance(value, dict):
        return {
            key: _without_none(item) for key, item in value.items() if item is not None
        }
    if isinstance(value, list):
        return [_without_none(item) for item in value]
    return value


# Checked-in bilingual function words. The `simple` text-search configuration
# has no stopword list and no stemming: terms are ORed, and a term of four or
# more characters matches as a prefix, so "fees" finds "fee"-led words and an
# inflected Armenian word finds its stem's forms (D11).
LEXICAL_QUERY_VERSION = "simple-prefix-v2"
_PREFIX_MIN_CHARS = 4
# A prefix only matches forward, so a query term is trimmed to its stem first:
# "fees" -> "fee:*" finds "fee" and "fees"; Armenian drops its article and case
# endings the same way. Longest first.
_ARMENIAN_ENDINGS = (
    "ները",
    "ների",
    "երը",
    "երի",
    "ներ",
    "ից",
    "ով",
    "ում",
    "ին",
    "ը",
    "ն",
    "ի",
)
_ARMENIAN = re.compile(r"[\u0531-\u0586]")
_STOPWORDS = frozenset(
    {
        "a",
        "allow",
        "allows",
        "am",
        "an",
        "and",
        "any",
        "apply",
        "applies",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "cover",
        "covers",
        "do",
        "does",
        "for",
        "from",
        "get",
        "gets",
        "give",
        "gives",
        "has",
        "have",
        "how",
        "i",
        "in",
        "is",
        "it",
        "its",
        "many",
        "me",
        "much",
        "my",
        "of",
        "offer",
        "offers",
        "on",
        "or",
        "reach",
        "require",
        "requires",
        "that",
        "the",
        "their",
        "there",
        "these",
        "they",
        "this",
        "to",
        "under",
        "was",
        "we",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whose",
        "will",
        "with",
        "would",
        "you",
        "your",
        "և",
        "է",
        "եմ",
        "են",
        "ես",
        "եք",
        "ինչ",
        "ինչպես",
        "ինչու",
        "որ",
        "որը",
        "որն",
        "որքան",
        "ու",
        "ունի",
        "ունեմ",
        "կա",
        "կան",
        "այս",
        "այդ",
        "այն",
        "մեջ",
        "համար",
        "հետ",
        "ից",
        "ի",
    }
)
_MAX_LEXICAL_TERMS = 12
_TERM_SPLIT = re.compile(r"[^0-9\w]+", re.UNICODE)
# Armenian question, exclamation, and emphasis marks sit inside a word, so they
# are removed rather than treated as separators.
_INTRA_WORD_MARKS = str.maketrans("", "", "\u055a\u055b\u055c\u055d\u055e\u055f")


def _terms(text: str) -> list[str]:
    normalized = text.casefold().translate(_INTRA_WORD_MARKS)
    return [
        token
        for token in _TERM_SPLIT.split(normalized)
        if len(token) > 1 and token not in _STOPWORDS
    ]


def lexical_search_terms(query: str, exclude: Sequence[str] = ()) -> str | None:
    """Turn one question into a deterministic `to_tsquery` of OR'ed terms.

    `exclude` holds names whose words carry no signal inside the scope (the
    offering's own name matches every one of its units).
    """
    excluded = {token for text in exclude for token in _terms(text)}
    unique = list(
        dict.fromkeys(token for token in _terms(query) if token not in excluded)
    )[:_MAX_LEXICAL_TERMS]
    if not unique:
        return None
    # Tokens are word characters only (split on everything else), so they
    # need no quoting in to_tsquery; stripping stray underscores keeps it so.
    parts: list[str] = []
    for token in unique:
        token = token.strip("_")
        if not token:
            continue
        if len(token) >= _PREFIX_MIN_CHARS:
            stem = _stem(token)
            part = f"{stem}:*"
        else:
            part = token
        if part not in parts:
            parts.append(part)
    return " | ".join(parts) or None


def _stem(token: str) -> str:
    if _ARMENIAN.search(token):
        for ending in _ARMENIAN_ENDINGS:
            if token.endswith(ending) and len(token) - len(ending) >= 3:
                return token[: -len(ending)]
        return token
    if token.endswith("s") and not token.endswith("ss") and len(token) >= 4:
        return token[:-1]
    return token


@dataclass(frozen=True)
class RankedUnit:
    unit: RetrievalUnit
    score: float
    source: str


class PostgresStructuredTariffQueryRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def offering_states(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
    ) -> dict[OfferingId, OfferingDataState]:
        """Why each offering has no published data: pending reviews, the latest
        execution's failure, or no execution at all (F1, F4)."""
        if not offering_ids:
            return {}
        ids = [item.value for item in offering_ids]
        async with self._sessions() as session:
            pending = {
                row["offering_id"]: int(row["pending"])
                for row in (
                    await session.execute(
                        text(
                            """SELECT offering_id, count(*) AS pending
                            FROM human_reviews
                            WHERE product = :product AND status = 'pending'
                              AND offering_id = ANY(:ids)
                            GROUP BY offering_id"""
                        ),
                        {"product": product.value, "ids": ids},
                    )
                )
                .mappings()
                .all()
            }
            latest = {
                row["offering_id"]: row
                for row in (
                    await session.execute(
                        text(
                            """SELECT DISTINCT ON (offering_id)
                                   offering_id, status, failure_code
                            FROM offering_executions
                            WHERE product = :product AND offering_id = ANY(:ids)
                            ORDER BY offering_id, created_at DESC"""
                        ),
                        {"product": product.value, "ids": ids},
                    )
                )
                .mappings()
                .all()
            }
        states: dict[OfferingId, OfferingDataState] = {}
        for offering in offering_ids:
            execution = latest.get(offering.value)
            if pending.get(offering.value):
                state = OfferingDataState(
                    state="awaiting_review", pending_reviews=pending[offering.value]
                )
            elif execution is None:
                state = OfferingDataState(state="never_monitored")
            elif execution["status"] == "failed":
                state = OfferingDataState(
                    state="run_failed", failure_code=execution["failure_code"]
                )
            else:
                state = OfferingDataState(state="no_accepted_data")
            states[offering] = state
        return states

    async def active_profiles(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
    ) -> tuple[OfferingProfile, ...]:
        if not offering_ids:
            return ()
        if any(item.product is not product for item in offering_ids):
            raise ValueError("offering outside requested product family")
        async with self._sessions() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            """SELECT p.* FROM offering_profiles AS p
                        JOIN tariff_snapshots AS s ON s.id = p.snapshot_id
                        WHERE p.bank = :bank AND p.product = :product
                          AND p.offering_id = ANY(:offering_ids)
                          AND p.is_active AND s.status = 'accepted'
                        ORDER BY p.offering_id, p.accepted_at DESC"""
                        ),
                        {
                            "bank": bank.lower(),
                            "product": product.value,
                            "offering_ids": [item.value for item in offering_ids],
                        },
                    )
                )
                .mappings()
                .all()
            )
        found: dict[str, OfferingProfile] = {}
        for row in rows:
            found.setdefault(
                row["offering_id"],
                OfferingProfile(
                    snapshot_id=row["snapshot_id"],
                    bank=row["bank"],
                    product=row["product"],
                    offering_id=row["offering_id"],
                    display_name=row["display_name"],
                    extracted_name=row["extracted_name"],
                    formal_names=tuple(_decoded(row["formal_names"])),
                    aliases=tuple(_decoded(row["aliases"])),
                    category=row["category"],
                    purposes=tuple(_decoded(row["purposes"])),
                    variants=tuple(_decoded(row["variants"])),
                    property_market=row["property_market"],
                    attributes=_decoded(row["attributes"]),
                    accepted_at=row["accepted_at"],
                    schema_version=row["schema_version"],
                ),
            )
        return tuple(found[item.value] for item in offering_ids if item.value in found)

    async def facts(
        self,
        *,
        snapshots: Sequence[UUID],
        fields: Sequence[FieldPath],
        include_inactive: bool = False,
    ) -> tuple[TariffFact, ...]:
        if not snapshots or not fields:
            return ()
        async with self._sessions() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            """SELECT f.*, f.value_json::text AS value_json_text
                        FROM tariff_facts AS f
                        JOIN offering_profiles AS p ON p.snapshot_id = f.snapshot_id
                        JOIN tariff_snapshots AS s ON s.id = f.snapshot_id
                        WHERE f.snapshot_id = ANY(:snapshots)
                          AND f.field_path = ANY(:fields)
                          AND (:include_inactive OR (f.is_active AND p.is_active))
                          AND s.status = 'accepted'
                        ORDER BY f.offering_id, f.field_path, f.variant_key"""
                        ),
                        {
                            "snapshots": list(snapshots),
                            "fields": [item.value for item in fields],
                            "include_inactive": include_inactive,
                        },
                    )
                )
                .mappings()
                .all()
            )
            if not rows:
                return ()
            ids = [row["id"] for row in rows]
            evidence_rows = (
                (
                    await session.execute(
                        text(
                            """SELECT e.*, f.snapshot_id,
                            d.content_sha256 AS verified_checksum,
                            d.document_key AS verified_document_key
                        FROM fact_evidence AS e
                        JOIN tariff_facts AS f ON f.id = e.fact_id
                        LEFT JOIN knowledge_documents AS d ON d.id = e.source_document_id
                        WHERE e.fact_id = ANY(:ids)
                        ORDER BY e.fact_id, e.evidence_id"""
                        ),
                        {"ids": ids},
                    )
                )
                .mappings()
                .all()
            )
            snapshot_rows = (
                (
                    await session.execute(
                        text(
                            """SELECT id, semantic_extraction
                        FROM tariff_snapshots WHERE id = ANY(:snapshots)
                          AND status = 'accepted'"""
                        ),
                        {"snapshots": list(snapshots)},
                    )
                )
                .mappings()
                .all()
            )
        catalogs = {
            row["id"]: {
                item["evidence_id"]: item
                for item in _decoded(row["semantic_extraction"]).get(
                    "evidence_catalog", []
                )
            }
            for row in snapshot_rows
        }
        by_fact: dict[str, list[FactEvidence]] = {}
        for row in evidence_rows:
            captured = catalogs.get(row["snapshot_id"], {}).get(row["evidence_id"])
            locator = _decoded(row["locator"])
            # `section` is added at projection from the captured item (F16); the
            # rest of the locator must be the captured one exactly.
            section = locator.get("section")
            if (
                captured is None
                or row["quote"] not in captured.get("content", "")
                or {key: value for key, value in locator.items() if key != "section"}
                != _without_none(captured.get("locator"))
                or (section is not None and section != captured.get("section"))
                or row["authority"] != captured.get("authority")
                or row["source_item_id"] != captured.get("source_item_id")
                or row["source_document_key"] != captured.get("document_id")
                or str(row["source_url"]) != locator.get("source_url")
                or (
                    row["source_document_id"] is not None
                    and (
                        row["source_checksum"] != row["verified_checksum"]
                        or row["source_document_key"] != row["verified_document_key"]
                    )
                )
            ):
                raise ValueError("stored fact evidence differs from accepted capture")
            by_fact.setdefault(row["fact_id"], []).append(
                FactEvidence(
                    evidence_id=row["evidence_id"],
                    quote=row["quote"],
                    source_url=row["source_url"],
                    source_item_id=row["source_item_id"],
                    source_document_key=row["source_document_key"],
                    document_id=row["source_document_id"],
                    document_checksum=row["source_checksum"],
                    locator=locator,
                    authority=row["authority"],
                )
            )
        return tuple(
            TariffFact(
                fact_id=row["id"],
                snapshot_id=row["snapshot_id"],
                offering_id=row["offering_id"],
                field_path=row["field_path"],
                variant_key=row["variant_key"],
                status=row["status"],
                value=_decoded(row["value_json_text"]),
                number=row["number_value"],
                unit=row["unit"],
                currency=row["currency"],
                rate_basis=row["rate_basis"],
                fee_scope=row["fee_scope"],
                conditions=tuple(_decoded(row["conditions"])),
                evidence=tuple(by_fact.get(row["id"], ())),
                taxonomy_version=row["taxonomy_version"],
            )
            for row in rows
        )

    async def lexical_units(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
        query: str,
        limit: int = 8,
        exclude_terms: Sequence[str] = (),
    ) -> tuple[RankedUnit, ...]:
        self._validate_search(product, offering_ids, limit)
        terms = lexical_search_terms(query, exclude_terms) if offering_ids else None
        record(
            "lexical.query",
            version=LEXICAL_QUERY_VERSION,
            offerings=[item.value for item in offering_ids],
            terms=0 if terms is None else len(terms.split(" | ")),
            limit=limit,
        )
        record_text("lexical.terms", tsquery=repr(terms))
        if terms is None:
            return ()
        return await self._search(
            """WITH q AS (SELECT to_tsquery('simple', :query) AS terms)
            SELECT u.*, ts_rank_cd(u.search_vector, q.terms) AS score
            FROM retrieval_units AS u
            JOIN offering_profiles AS p ON p.snapshot_id = u.snapshot_id
            JOIN tariff_snapshots AS s ON s.id = u.snapshot_id
            CROSS JOIN q
            WHERE p.bank = :bank AND p.product = :product
              AND u.offering_id = ANY(:offering_ids)
              AND u.is_active AND p.is_active AND s.status = 'accepted'
              AND u.search_vector @@ q.terms
            ORDER BY score DESC, u.id LIMIT :limit""",
            bank=bank,
            product=product,
            offering_ids=offering_ids,
            limit=limit,
            query=terms,
            source="lexical",
        )

    async def vector_units(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
        embedding: Sequence[float],
        model_id: str,
        limit: int = 8,
    ) -> tuple[RankedUnit, ...]:
        self._validate_search(product, offering_ids, limit)
        if not offering_ids:
            return ()
        if len(embedding) != 768 or not all(
            math.isfinite(value) for value in embedding
        ):
            raise ValueError("query embedding must contain 768 finite dimensions")
        record(
            "vector.query",
            model=model_id,
            dimensions=len(embedding),
            offerings=[item.value for item in offering_ids],
            limit=limit,
        )
        vector = "[" + ",".join(str(value) for value in embedding) + "]"
        return await self._search(
            """SELECT u.*, 1 - (u.embedding <=> CAST(:vector AS vector)) AS score
            FROM retrieval_units AS u
            JOIN offering_profiles AS p ON p.snapshot_id = u.snapshot_id
            JOIN tariff_snapshots AS s ON s.id = u.snapshot_id
            WHERE p.bank = :bank AND p.product = :product
              AND u.offering_id = ANY(:offering_ids)
              AND u.is_active AND p.is_active AND s.status = 'accepted'
              AND u.embedding IS NOT NULL
              AND u.embedding_model = :model_id
              AND u.embedding_dimensions = 768
            ORDER BY u.embedding <=> CAST(:vector AS vector), u.id LIMIT :limit""",
            bank=bank,
            product=product,
            offering_ids=offering_ids,
            limit=limit,
            vector=vector,
            model_id=model_id,
            source="vector",
        )

    async def _search(
        self,
        sql: str,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
        limit: int,
        source: str,
        **params,
    ) -> tuple[RankedUnit, ...]:
        async with self._sessions() as session:
            rows = (
                (
                    await session.execute(
                        text(sql),
                        {
                            "bank": bank.lower(),
                            "product": product.value,
                            "offering_ids": [item.value for item in offering_ids],
                            "limit": limit,
                            **params,
                        },
                    )
                )
                .mappings()
                .all()
            )
        for row in rows:
            if (
                hashlib.sha256(row["content"].encode("utf-8")).hexdigest()
                != row["content_sha256"]
            ):
                raise ValueError("stored retrieval text differs from published hash")
        return tuple(
            RankedUnit(
                unit=RetrievalUnit(
                    unit_id=row["id"],
                    snapshot_id=row["snapshot_id"],
                    offering_id=row["offering_id"],
                    kind=row["kind"],
                    field_paths=tuple(row["field_paths"]),
                    fact_ids=tuple(row["fact_ids"]),
                    evidence_ids=tuple(row["evidence_ids"]),
                    language=row["language"],
                    identity_text=row["identity_text"],
                    alias_purpose_text=row["alias_purpose_text"],
                    detail_text=row["detail_text"],
                    content=row["content"],
                    content_sha256=row["content_sha256"],
                    renderer_version=row["renderer_version"],
                ),
                score=float(row["score"]),
                source=source,
            )
            for row in rows
        )

    async def accepted_changes(
        self,
        *,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
        limit: int = 50,
    ) -> tuple[SnapshotChangeSet, ...]:
        if not 1 <= limit <= 200:
            raise ValueError("history limit must be 1..200")
        if any(item.product is not product for item in offering_ids):
            raise ValueError("offering outside requested product family")
        if not offering_ids:
            return ()
        async with self._sessions() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            """SELECT c.* FROM tariff_changes AS c
                        JOIN tariff_snapshots AS s ON s.id = c.current_snapshot_id
                        WHERE c.product = :product
                          AND c.offering_id = ANY(:offering_ids)
                          AND s.status = 'accepted'
                        ORDER BY c.created_at DESC, c.id LIMIT :limit"""
                        ),
                        {
                            "product": product.value,
                            "offering_ids": [item.value for item in offering_ids],
                            "limit": limit,
                        },
                    )
                )
                .mappings()
                .all()
            )
        return tuple(
            SnapshotChangeSet(
                id=row["id"],
                run_id=row["run_id"],
                product=row["product"],
                offering_id=row["offering_id"],
                previous_snapshot_id=row["previous_snapshot_id"],
                current_snapshot_id=row["current_snapshot_id"],
                changes=tuple(_decoded(row["changes"])),
                created_at=row["created_at"],
            )
            for row in rows
        )

    @staticmethod
    def _validate_search(
        product: ProductType, offering_ids: Sequence[OfferingId], limit: int
    ) -> None:
        if not 1 <= limit <= 20:
            raise ValueError("retrieval limit must be 1..20")
        if any(item.product is not product for item in offering_ids):
            raise ValueError("offering outside requested product family")


@dataclass(frozen=True)
class UnitEmbeddingInput:
    unit_id: str
    content: str
    content_sha256: str


class PostgresStructuredUnitEmbeddingRepository:
    """Fill vectors only for active accepted units with matching content hashes."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def missing(
        self,
        *,
        bank: str,
        product: ProductType,
        offering_ids: Sequence[OfferingId],
        model_id: str,
        limit: int = 100,
    ) -> tuple[UnitEmbeddingInput, ...]:
        if not 1 <= limit <= 500:
            raise ValueError("embedding batch limit must be 1..500")
        if any(item.product is not product for item in offering_ids):
            raise ValueError("offering outside requested product family")
        if not offering_ids:
            return ()
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    text(
                        """SELECT u.id, u.content, u.content_sha256
                        FROM retrieval_units AS u
                        JOIN offering_profiles AS p ON p.snapshot_id = u.snapshot_id
                        JOIN tariff_snapshots AS s ON s.id = u.snapshot_id
                        WHERE p.bank = :bank AND p.product = :product
                          AND u.offering_id = ANY(:offering_ids)
                          AND u.is_active AND p.is_active AND s.status = 'accepted'
                          AND (u.embedding IS NULL OR u.embedding_model IS DISTINCT FROM :model_id)
                        ORDER BY u.kind, u.id LIMIT :limit"""
                    ),
                    {
                        "bank": bank.lower(),
                        "product": product.value,
                        "offering_ids": [item.value for item in offering_ids],
                        "model_id": model_id,
                        "limit": limit,
                    },
                )
            ).all()
        return tuple(
            UnitEmbeddingInput(row.id, row.content, row.content_sha256) for row in rows
        )

    async def save(
        self,
        *,
        model_id: str,
        vectors: Sequence[tuple[UnitEmbeddingInput, Sequence[float]]],
    ) -> int:
        if not vectors:
            return 0
        updated = 0
        async with self._sessions() as session, session.begin():
            for unit, vector in vectors:
                if len(vector) != 768 or not all(
                    math.isfinite(value) for value in vector
                ):
                    raise ValueError(
                        "retrieval vector must contain 768 finite dimensions"
                    )
                result = await session.execute(
                    text(
                        """UPDATE retrieval_units AS u
                        SET embedding = CAST(:vector AS vector),
                            embedding_model = :model_id,
                            embedding_dimensions = 768
                        WHERE u.id = :unit_id
                          AND u.content_sha256 = :content_sha256
                          AND u.is_active
                          AND EXISTS (
                              SELECT 1 FROM offering_profiles AS p
                              JOIN tariff_snapshots AS s ON s.id = p.snapshot_id
                              WHERE p.snapshot_id = u.snapshot_id
                                AND p.is_active AND s.status = 'accepted'
                          )"""
                    ),
                    {
                        "vector": "[" + ",".join(str(value) for value in vector) + "]",
                        "model_id": model_id,
                        "unit_id": unit.unit_id,
                        "content_sha256": unit.content_sha256,
                    },
                )
                updated += result.rowcount or 0
        return updated
