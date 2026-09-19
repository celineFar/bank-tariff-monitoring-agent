from __future__ import annotations

from dataclasses import dataclass

import httpx
from google import genai
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.config import Settings, load_seed_catalog
from app.repositories.knowledge_store import PostgresKnowledgeStore
from app.repositories.monitoring import (
    PostgresOfferingPublicationRepository,
    PostgresRunRepository,
    PostgresSnapshotRepository,
)
from app.repositories.pdf_extraction import PostgresPdfExtractionRepository
from app.repositories.rag_retrieval import PostgresRagRetrievalRepository
from app.repositories.semantic_extraction import PostgresSemanticExtractionRepository
from app.repositories.source_discovery import PostgresSourceDiscoveryRepository
from app.services.acquisition import build_acquisition_service
from app.services.artifact_store import FileSystemArtifactStore
from app.services.discovery_classifier import AdkSourceDiscoveryClassifier
from app.services.knowledge_index import (
    GeminiEmbeddingProvider,
    GeminiQueryEmbeddingProvider,
    KnowledgeIndexer,
)
from app.services.knowledge_projection import KnowledgeProjectionService
from app.services.monitoring_pipeline import IndexingPipeline, TariffPipeline
from app.services.normalization import StructuralNormalizationService
from app.services.pdf_extraction import GeminiPdfExtractionService
from app.services.rag_answer import GeminiAnswerGenerator, RagAnswerService
from app.services.rag_retrieval import RagRetriever
from app.services.run_service import RunService
from app.services.semantic_extraction import (
    AdkSemanticExtractor,
    SemanticExtractionService,
)
from app.services.source_discovery import SourceDiscoveryService


@dataclass
class ApplicationContainer:
    engine: AsyncEngine
    http_client: httpx.AsyncClient
    runs: PostgresRunRepository
    run_service: RunService
    tariff_pipeline: TariffPipeline
    answer_service: RagAnswerService

    async def close(self) -> None:
        await self.http_client.aclose()
        await self.engine.dispose()


def build_application_container(settings: Settings) -> ApplicationContainer:
    engine = create_async_engine(settings.database.url.get_secret_value())
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    http_client = httpx.AsyncClient(
        timeout=settings.http.timeout_seconds,
        follow_redirects=False,
    )
    api_key = (
        settings.models.api_key.get_secret_value()
        if settings.models.api_key is not None
        else None
    )
    runs = PostgresRunRepository(sessions)
    artifacts = FileSystemArtifactStore(settings.application.artifact_temp_dir)
    normalization = StructuralNormalizationService(
        artifact_reader=artifacts,
        pdf_extractor=GeminiPdfExtractionService(
            settings.pdf_extraction,
            PostgresPdfExtractionRepository(sessions),
            api_key=api_key,
        ),
    )
    discovery = SourceDiscoveryService(
        AdkSourceDiscoveryClassifier(
            settings.models.generation_model,
            api_key=api_key,
            max_attempts=settings.source_discovery.classifier_max_attempts,
            backoff_base_seconds=(
                settings.source_discovery.classifier_backoff_base_seconds
            ),
            max_backoff_seconds=(
                settings.source_discovery.classifier_max_backoff_seconds
            ),
            retry_jitter_ratio=(
                settings.source_discovery.classifier_retry_jitter_ratio
            ),
        ),
        PostgresSourceDiscoveryRepository(sessions),
        settings.source_discovery,
        model_name=settings.models.generation_model,
    )
    extraction = SemanticExtractionService(
        AdkSemanticExtractor(
            settings.models.generation_model,
            api_key=api_key,
        ),
        PostgresSemanticExtractionRepository(sessions),
        settings.semantic_extraction,
        model_name=settings.models.generation_model,
    )
    embedding_client = genai.Client(api_key=api_key) if api_key else genai.Client()
    indexer = KnowledgeIndexer(
        GeminiEmbeddingProvider(
            embedding_client,
            settings.models.embedding_model,
        ),
        PostgresKnowledgeStore(sessions),
    )
    indexing = IndexingPipeline(
        acquisition=build_acquisition_service(http_client, settings),
        normalization=normalization,
        discovery=discovery,
        extraction=extraction,
        projection=KnowledgeProjectionService(
            max_chunk_chars=settings.rag.chunk_size_chars
        ),
        embedder=indexer,
        snapshots=PostgresSnapshotRepository(sessions),
        publications=PostgresOfferingPublicationRepository(sessions),
    )
    answer_service = RagAnswerService(
        RagRetriever(
            GeminiQueryEmbeddingProvider(
                embedding_client,
                settings.models.embedding_model,
            ),
            PostgresRagRetrievalRepository(sessions),
            settings.rag,
        ),
        GeminiAnswerGenerator(embedding_client, settings.models.generation_model),
    )
    return ApplicationContainer(
        engine=engine,
        http_client=http_client,
        runs=runs,
        run_service=RunService(runs),
        answer_service=answer_service,
        tariff_pipeline=TariffPipeline(
            catalog=load_seed_catalog(allowed_hosts=settings.http.allowed_source_hosts),
            indexing=indexing,
            runs=runs,
        ),
    )
