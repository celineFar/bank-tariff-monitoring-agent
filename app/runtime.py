from __future__ import annotations

import os
import socket
from dataclasses import dataclass

import httpx
from google import genai
from google.adk.workflow import FunctionNode
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.config import Settings, load_seed_catalog
from app.repositories.acquisition_baselines import (
    PostgresAcquisitionBaselineRepository,
)
from app.repositories.acquisition_snapshots import (
    PostgresAcquisitionSnapshotRepository,
)
from app.repositories.embedding_cache import PostgresEmbeddingCache
from app.repositories.knowledge_store import PostgresKnowledgeStore
from app.repositories.monitoring import (
    PostgresOfferingPublicationRepository,
    PostgresRunRepository,
    PostgresSnapshotRepository,
)
from app.repositories.pdf_extraction import PostgresPdfExtractionRepository
from app.repositories.rag_retrieval import PostgresRagRetrievalRepository
from app.repositories.reviews import PostgresReviewRepository
from app.repositories.semantic_extraction import PostgresSemanticExtractionRepository
from app.repositories.source_discovery import PostgresSourceDiscoveryRepository
from app.repositories.structured_tariff_query import (
    PostgresStructuredTariffQueryRepository,
    PostgresStructuredUnitEmbeddingRepository,
)
from app.services.acquisition import build_acquisition_service
from app.services.acquisition_completeness import (
    CompletenessGatedAcquisitionService,
)
from app.services.acquisition_freshness import FreshnessGatedAcquisitionService
from app.services.answer_read_model import TariffAnswerRouter
from app.services.artifact_store import FileSystemArtifactStore
from app.services.discovery_classifier import AdkSourceDiscoveryClassifier
from app.services.intent_resolution import AdkIntentClassifier, RequestResolver
from app.services.knowledge_index import (
    GeminiEmbeddingProvider,
    GeminiQueryEmbeddingProvider,
    KnowledgeIndexer,
)
from app.services.knowledge_projection import KnowledgeProjectionService
from app.services.model_call_usage import (
    PostgresModelCallUsageRepository,
    configure_default_model_usage_repository,
)
from app.services.model_pricing import enforce_model_price_cap, model_sequence
from app.services.monitoring_node import build_monitoring_node
from app.services.monitoring_pipeline import IndexingPipeline, TariffPipeline
from app.services.normalization import StructuralNormalizationService
from app.services.normalization_baseline import load_normalization_baseline
from app.services.ocr_transcriber import TesseractOcrTranscriber
from app.services.pdf_extraction import GeminiPdfExtractionService
from app.services.pdf_rasterizer import PdfiumPageRasterizer
from app.services.pipeline_audit_archive import FileSystemPipelineAuditArchive
from app.services.rag_answer import GeminiAnswerGenerator, RagAnswerService
from app.services.rag_retrieval import RagRetriever
from app.services.review_decisions import ReviewDecisionService
from app.services.review_resolution import ReviewResolutionService
from app.services.run_service import RunService
from app.services.semantic_extraction import (
    AdkSemanticExtractor,
    FallbackSemanticExtractionService,
    SemanticExtractionService,
)
from app.services.source_discovery import (
    FallbackSourceDiscoveryService,
    SourceDiscoveryService,
)
from app.services.structured_tariff_query import StructuredTariffQueryService
from app.services.structured_unit_embeddings import StructuredUnitEmbeddingService
from app.services.tariff_queries import (
    CurrentTariffService,
    TariffHistoryService,
)


@dataclass
class ApplicationContainer:
    engine: AsyncEngine
    http_client: httpx.AsyncClient
    runs: PostgresRunRepository
    reviews: PostgresReviewRepository
    run_service: RunService
    tariff_pipeline: TariffPipeline
    review_resolution: ReviewResolutionService
    # The ADK-native monitoring node (plan Phase 3); `monitoring_owner` is the
    # `claimed_by` value this process writes when it executes a chat run.
    monitoring_node: FunctionNode
    monitoring_owner: str
    answer_service: RagAnswerService
    structured_query_service: StructuredTariffQueryService
    answer_router: TariffAnswerRouter
    request_resolver: RequestResolver
    current_tariff_service: CurrentTariffService
    tariff_history_service: TariffHistoryService

    async def close(self) -> None:
        await self.http_client.aclose()
        await self.engine.dispose()


def process_owner(prefix: str) -> str:
    """`<prefix>:<host>:<pid>` — the `claimed_by` of runs this process executes."""
    return f"{prefix}:{socket.gethostname()}:{os.getpid()}"


def build_application_container(
    settings: Settings,
    *,
    monitoring_owner: str | None = None,
) -> ApplicationContainer:
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
    model_usage = PostgresModelCallUsageRepository(sessions)
    configure_default_model_usage_repository(model_usage)
    run_service = RunService(runs)
    catalog = load_seed_catalog(allowed_hosts=settings.http.allowed_source_hosts)
    request_resolver = RequestResolver(
        catalog,
        settings.intent_resolution,
        classifier=AdkIntentClassifier(
            settings.models.generation_model,
            api_key=api_key,
            max_attempts=settings.intent_resolution.classifier_max_attempts,
            usage_repository=model_usage,
        ),
    )
    artifacts = FileSystemArtifactStore(settings.application.artifact_temp_dir)
    snapshots = PostgresSnapshotRepository(sessions)
    normalization = StructuralNormalizationService(
        baseline=load_normalization_baseline(),
        artifact_reader=artifacts,
        pdf_extractor=GeminiPdfExtractionService(
            settings.pdf_extraction,
            PostgresPdfExtractionRepository(sessions),
            api_key=api_key,
            usage_repository=model_usage,
            ocr_settings=settings.ocr,
            ocr_transcriber=TesseractOcrTranscriber(settings.ocr),
            rasterizer=PdfiumPageRasterizer(),
        ),
    )
    discovery_models = model_sequence(
        settings.source_discovery.model_name or settings.models.generation_model,
        settings.source_discovery.fallback_model_names,
    )
    enforce_model_price_cap(
        discovery_models,
        max_price_per_million_tokens_usd=(
            settings.source_discovery.max_price_per_million_tokens_usd
        ),
    )
    discovery_repository = PostgresSourceDiscoveryRepository(sessions)
    discovery = FallbackSourceDiscoveryService(
        tuple(
            SourceDiscoveryService(
                AdkSourceDiscoveryClassifier(
                    discovery_model,
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
                    usage_repository=model_usage,
                ),
                discovery_repository,
                settings.source_discovery,
                model_name=discovery_model,
                usage_repository=model_usage,
            )
            for discovery_model in discovery_models
        )
    )
    extraction_models = model_sequence(
        settings.models.generation_model,
        settings.semantic_extraction.fallback_model_names,
    )
    extraction_repository = PostgresSemanticExtractionRepository(sessions)
    extraction = FallbackSemanticExtractionService(
        tuple(
            SemanticExtractionService(
                AdkSemanticExtractor(
                    extraction_model,
                    api_key=api_key,
                    thinking_budget=settings.semantic_extraction.thinking_budget,
                    usage_repository=model_usage,
                ),
                extraction_repository,
                settings.semantic_extraction,
                model_name=extraction_model,
                usage_repository=model_usage,
            )
            for extraction_model in extraction_models
        )
    )
    embedding_client = genai.Client(api_key=api_key) if api_key else genai.Client()
    indexer = KnowledgeIndexer(
        GeminiEmbeddingProvider(
            embedding_client,
            settings.models.embedding_model,
            usage_repository=model_usage,
            max_attempts=settings.rag.embedding_max_attempts,
            backoff_base_seconds=settings.rag.embedding_backoff_base_seconds,
            quota_max_attempts=settings.rag.embedding_quota_max_attempts,
            quota_backoff_base_seconds=(
                settings.rag.embedding_quota_backoff_base_seconds
            ),
        ),
        PostgresKnowledgeStore(sessions),
        PostgresEmbeddingCache(sessions),
        usage_repository=model_usage,
    )
    audit_archive = (
        FileSystemPipelineAuditArchive(settings.application.pipeline_audit_dir)
        if settings.application.pipeline_audit_enabled
        else None
    )
    indexing = IndexingPipeline(
        # Freshness outside, completeness inside: a reused acquisition already
        # passed the gate when it was fetched, and one that fails the gate is
        # never stored for reuse.
        acquisition=FreshnessGatedAcquisitionService(
            CompletenessGatedAcquisitionService(
                build_acquisition_service(http_client, settings),
                PostgresAcquisitionBaselineRepository(sessions),
                settings.acquisition,
            ),
            PostgresAcquisitionSnapshotRepository(sessions),
            freshness_hours=settings.acquisition.freshness_hours,
            artifact_reader=artifacts,
        ),
        normalization=normalization,
        discovery=discovery,
        extraction=extraction,
        projection=KnowledgeProjectionService(
            max_chunk_chars=settings.rag.chunk_size_chars
        ),
        embedder=indexer,
        snapshots=snapshots,
        publications=PostgresOfferingPublicationRepository(sessions),
        runs=runs,
        audit_archive=audit_archive,
        large_rate_change_percentage_points=(
            settings.hitl.large_rate_change_percentage_points
        ),
    )
    answer_service = RagAnswerService(
        RagRetriever(
            GeminiQueryEmbeddingProvider(
                embedding_client,
                settings.models.embedding_model,
                usage_repository=model_usage,
            ),
            PostgresRagRetrievalRepository(sessions),
            settings.rag,
        ),
        GeminiAnswerGenerator(
            embedding_client,
            settings.models.generation_model,
            usage_repository=model_usage,
        ),
    )
    structured_query_service = StructuredTariffQueryService(
        PostgresStructuredTariffQueryRepository(sessions),
        StructuredUnitEmbeddingService(
            PostgresStructuredUnitEmbeddingRepository(sessions),
            PostgresEmbeddingCache(sessions),
            GeminiEmbeddingProvider(
                embedding_client,
                settings.models.embedding_model,
                usage_repository=model_usage,
                max_attempts=settings.rag.embedding_max_attempts,
                backoff_base_seconds=settings.rag.embedding_backoff_base_seconds,
                quota_max_attempts=settings.rag.embedding_quota_max_attempts,
                quota_backoff_base_seconds=(
                    settings.rag.embedding_quota_backoff_base_seconds
                ),
            ),
            GeminiQueryEmbeddingProvider(
                embedding_client,
                settings.models.embedding_model,
                usage_repository=model_usage,
            ),
            usage_repository=model_usage,
        ),
    )
    answer_router = TariffAnswerRouter(
        structured_query_service,
        answer_service,
        settings.tariff_queries.answer_read_model,
    )
    reviews = PostgresReviewRepository(sessions)
    tariff_pipeline = TariffPipeline(
        catalog=catalog,
        indexing=indexing,
        runs=runs,
        reviews=reviews,
    )
    review_resolution = ReviewResolutionService(
        runs=runs,
        reviews=reviews,
        decisions=ReviewDecisionService(reviews, snapshots),
    )
    owner = monitoring_owner or process_owner("api")
    monitoring_node = build_monitoring_node(
        runs=runs,
        run_service=run_service,
        pipeline=tariff_pipeline,
        resolution=review_resolution,
        answer_router=answer_router,
        owner=owner,
        poll_seconds=settings.tariff_queries.run_poll_seconds,
    )

    return ApplicationContainer(
        engine=engine,
        http_client=http_client,
        runs=runs,
        reviews=reviews,
        run_service=run_service,
        answer_service=answer_service,
        structured_query_service=structured_query_service,
        answer_router=answer_router,
        request_resolver=request_resolver,
        current_tariff_service=CurrentTariffService(
            catalog,
            snapshots,
            settings.tariff_queries,
        ),
        tariff_history_service=TariffHistoryService(
            snapshots,
            settings.tariff_queries,
        ),
        review_resolution=review_resolution,
        monitoring_node=monitoring_node,
        monitoring_owner=owner,
        tariff_pipeline=tariff_pipeline,
    )
