"""Print the production RAG answer path for one scoped question.

Run with: uv run python -m scripts.trace_rag_answer "What is the nominal rate?" \
    --product consumer_loan --offering-id consumer_standard
"""

from __future__ import annotations

import argparse
import asyncio

from google import genai
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import load_settings
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import QuestionCommand
from app.domain.retrieval import RetrievalRequest, RetrievalResult
from app.repositories.rag_retrieval import PostgresRagRetrievalRepository
from app.services.knowledge_index import GeminiQueryEmbeddingProvider
from app.services.rag_answer import (
    AnswerDraft,
    GeminiAnswerGenerator,
    RagAnswerService,
)
from app.services.rag_retrieval import RagRetriever


class TracedEmbeddingProvider:
    def __init__(self, provider: GeminiQueryEmbeddingProvider) -> None:
        self.provider = provider
        self.dimensions = provider.dimensions

    async def embed_query(self, content: str):
        print("\n[1] Query embedding (RETRIEVAL_QUERY)", flush=True)
        print(f"Model: {self.provider._model_name}\nInput: {content}", flush=True)
        embedding = await self.provider.embed_query(content)
        print(f"Output: {len(embedding)} dimensions", flush=True)
        return embedding


class TracedRepository:
    def __init__(self, repository: PostgresRagRetrievalRepository) -> None:
        self.repository = repository

    async def search_candidates(self, **kwargs):
        print("\n[2] PostgreSQL hybrid candidate search", flush=True)
        print(
            "Table: knowledge_chunks JOIN knowledge_documents\n"
            f"Scope: bank={kwargs['bank']} product={kwargs['product'].value} "
            f"offering={kwargs['offering_id'].value if kwargs['offering_id'] else '*'} "
            f"kinds={[kind.value for kind in kwargs['document_kinds']]}\n"
            f"Lexical query: {kwargs['lexical_query']}\n"
            f"Limit per lexical/vector branch: {kwargs['limit']}",
            flush=True,
        )
        candidates = await self.repository.search_candidates(**kwargs)
        print(f"Candidate count: {len(candidates)}", flush=True)
        for candidate in candidates:
            print(
                f"  {candidate.chunk_id} kind={candidate.document_kind.value} "
                f"lexical={candidate.lexical_score:.3f} "
                f"(rank {candidate.lexical_rank}) "
                f"vector={candidate.vector_score:.3f} "
                f"(rank {candidate.vector_rank})",
                flush=True,
            )
        return candidates


class TracedRetriever:
    def __init__(self, retriever: RagRetriever, *, top_k: int, min_score: float) -> None:
        self.retriever = retriever
        self.top_k = top_k
        self.min_score = min_score

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        result = await self.retriever.retrieve(request)
        print("\n[3] Ranked and selected evidence", flush=True)
        print(
            f"Status: {result.status.value}; candidates considered: "
            f"{result.candidates_considered}; minimum score: {self.min_score:.3f}; "
            f"top_k: {self.top_k}",
            flush=True,
        )
        if result.reason:
            print(f"Reason: {result.reason}", flush=True)
        for rank, hit in enumerate(result.hits, 1):
            print(
                f"\n  #{rank} chunk={hit.chunk_id} kind={hit.document_kind.value} "
                f"final={hit.final_score:.3f} lexical={hit.lexical_score:.3f} "
                f"vector={hit.vector_score:.3f}\n"
                f"  document={hit.document_name} page={hit.page_start or '-'} "
                f"section={hit.section or '-'}\n"
                f"  source={hit.source_url}\n"
                f"  content:\n{hit.content}",
                flush=True,
            )
        return result


class TracedGenerator:
    def __init__(self, generator: GeminiAnswerGenerator) -> None:
        self.generator = generator
        self.attempt = 0

    async def generate(self, prompt: str) -> AnswerDraft:
        self.attempt += 1
        print(f"\n[4] Generation attempt {self.attempt}", flush=True)
        print(f"Model: {self.generator._model_name}\nEvidence prompt:\n{prompt}", flush=True)
        draft = await self.generator.generate(prompt)
        print(f"Structured draft:\n{draft.model_dump_json(indent=2)}", flush=True)
        return draft


async def trace(query: str, product: ProductType, offering_id: OfferingId | None) -> None:
    settings = load_settings()
    command = QuestionCommand(query=query, product=product, offering_id=offering_id)
    print(
        f"Question: {command.query}\nProduct: {product.value}\n"
        f"Offering: {offering_id.value if offering_id else '*'}",
        flush=True,
    )
    engine = create_async_engine(settings.database.url.get_secret_value())
    try:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        api_key = (
            settings.models.api_key.get_secret_value()
            if settings.models.api_key is not None
            else None
        )
        client = genai.Client(api_key=api_key) if api_key else genai.Client()
        retriever = TracedRetriever(
            RagRetriever(
                TracedEmbeddingProvider(
                    GeminiQueryEmbeddingProvider(client, settings.models.embedding_model)
                ),
                TracedRepository(PostgresRagRetrievalRepository(sessions)),
                settings.rag,
            ),
            top_k=settings.rag.retrieval_top_k,
            min_score=settings.rag.retrieval_min_score,
        )
        service = RagAnswerService(
            retriever,
            TracedGenerator(GeminiAnswerGenerator(client, settings.models.generation_model)),
        )
        result = await service.answer(command)
        print("\n[5] Citation validation and final answer", flush=True)
        print(result.model_dump_json(indent=2), flush=True)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Question to answer from active RAG chunks")
    parser.add_argument("--product", required=True, choices=[p.value for p in ProductType])
    parser.add_argument("--offering-id", choices=[o.value for o in OfferingId])
    args = parser.parse_args()
    asyncio.run(
        trace(
            args.query,
            ProductType(args.product),
            OfferingId(args.offering_id) if args.offering_id else None,
        )
    )


if __name__ == "__main__":
    main()
