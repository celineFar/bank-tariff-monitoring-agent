from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import ProductType
from app.domain.retrieval import RetrievalCandidate

HYBRID_SEARCH_SQL = """
WITH search_input AS (
    SELECT
        websearch_to_tsquery('simple', :lexical_query) AS text_query,
        CAST(:query_embedding AS vector) AS query_embedding
),
lexical_candidates AS (
    SELECT
        c.id,
        row_number() OVER (
            ORDER BY ts_rank_cd(c.search_vector, i.text_query) DESC, c.id
        ) AS lexical_rank,
        LEAST(
            1.0,
            ts_rank_cd(c.search_vector, i.text_query)
            / (ts_rank_cd(c.search_vector, i.text_query) + 1.0)
        ) AS lexical_score
    FROM knowledge_chunks AS c
    JOIN knowledge_documents AS d ON d.id = c.document_id
    CROSS JOIN search_input AS i
    WHERE d.bank = :bank
      AND d.product = :product
      AND d.is_active IS TRUE
      AND c.is_active IS TRUE
      AND c.search_vector @@ i.text_query
    ORDER BY lexical_score DESC, c.id
    LIMIT :candidate_limit
),
vector_candidates AS (
    SELECT
        c.id,
        row_number() OVER (
            ORDER BY c.embedding <=> i.query_embedding, c.id
        ) AS vector_rank,
        GREATEST(
            0.0,
            LEAST(1.0, 1.0 - (c.embedding <=> i.query_embedding))
        ) AS vector_score
    FROM knowledge_chunks AS c
    JOIN knowledge_documents AS d ON d.id = c.document_id
    CROSS JOIN search_input AS i
    WHERE d.bank = :bank
      AND d.product = :product
      AND d.is_active IS TRUE
      AND c.is_active IS TRUE
    ORDER BY c.embedding <=> i.query_embedding, c.id
    LIMIT :candidate_limit
),
candidate_ids AS (
    SELECT id FROM lexical_candidates
    UNION
    SELECT id FROM vector_candidates
)
SELECT
    c.id AS chunk_id,
    c.content,
    COALESCE(l.lexical_score, 0.0) AS lexical_score,
    COALESCE(v.vector_score, 0.0) AS vector_score,
    l.lexical_rank,
    v.vector_rank,
    d.id AS document_id,
    d.content_sha256 AS document_checksum,
    d.document_name,
    d.source_url,
    d.final_url,
    c.page_start,
    c.page_end,
    c.section,
    c.language,
    d.retrieved_at,
    c.extraction_method,
    COALESCE(c.quality_score, d.quality_score) AS quality_score
FROM candidate_ids AS ids
JOIN knowledge_chunks AS c ON c.id = ids.id
JOIN knowledge_documents AS d ON d.id = c.document_id
LEFT JOIN lexical_candidates AS l ON l.id = c.id
LEFT JOIN vector_candidates AS v ON v.id = c.id
WHERE d.bank = :bank
  AND d.product = :product
  AND d.is_active IS TRUE
  AND c.is_active IS TRUE
"""


class PostgresRagRetrievalRepository:
    """Filtered hybrid candidate search; ranking policy stays in the service."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def search_candidates(
        self,
        *,
        bank: str,
        product: ProductType,
        lexical_query: str,
        query_embedding: Sequence[float],
        limit: int,
    ) -> tuple[RetrievalCandidate, ...]:
        embedding_literal = (
            "[" + ",".join(str(value) for value in query_embedding) + "]"
        )
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    text(HYBRID_SEARCH_SQL),
                    {
                        "bank": bank.lower(),
                        "product": product.value,
                        "lexical_query": lexical_query,
                        "query_embedding": embedding_literal,
                        "candidate_limit": limit,
                    },
                )
            ).mappings()
            return tuple(RetrievalCandidate.model_validate(row) for row in rows)
