from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config.environment import EnvironmentSettings
from app.config.models import (
    AcquisitionSettings,
    ApplicationSettings,
    DatabaseSettings,
    HitlSettings,
    HttpSettings,
    IntentResolutionSettings,
    ModelSettings,
    ObservabilitySettings,
    OcrSettings,
    PdfExtractionSettings,
    RagSettings,
    SchedulerSettings,
    SemanticExtractionSettings,
    Settings,
    SourceDiscoverySettings,
    TariffQuerySettings,
)


def load_settings(
    *, _env_file: str | Path | None = ".env", **overrides: Any
) -> Settings:
    raw = EnvironmentSettings(_env_file=_env_file, **overrides)
    return Settings(
        application=ApplicationSettings(
            name=raw.app_name,
            environment=raw.environment,
            artifact_temp_dir=raw.artifact_temp_dir,
            pipeline_audit_enabled=raw.pipeline_audit_enabled,
            pipeline_audit_dir=raw.pipeline_audit_dir,
        ),
        models=ModelSettings(
            api_key=raw.gemini_api_key,
            generation_model=raw.model_name,
            embedding_model=raw.embedding_model_name,
        ),
        database=DatabaseSettings(
            url=raw.database_url,
            session_service_uri=raw.session_service_uri,
        ),
        http=HttpSettings(
            allowed_source_hosts=raw.allowed_source_hosts,
            allowed_download_mime_types=raw.allowed_download_mime_types,
            user_agent=raw.http_user_agent,
            timeout_seconds=raw.download_timeout_seconds,
            max_attempts=raw.http_max_attempts,
            backoff_base_seconds=raw.http_backoff_base_seconds,
            retry_jitter_ratio=raw.http_retry_jitter_ratio,
            max_retry_delay_seconds=raw.http_max_retry_delay_seconds,
            max_redirects=raw.max_redirects,
            max_download_bytes=raw.max_download_bytes,
            allow_origins=raw.allow_origins,
        ),
        acquisition=AcquisitionSettings(
            browser_enabled=raw.acquisition_browser_enabled,
            min_static_text_chars=raw.acquisition_min_static_text_chars,
            browser_navigation_timeout_seconds=(
                raw.acquisition_browser_navigation_timeout_seconds
            ),
            browser_settle_milliseconds=(raw.acquisition_browser_settle_milliseconds),
            max_interactions=raw.acquisition_max_interactions,
            max_network_payloads=raw.acquisition_max_network_payloads,
            max_network_payload_bytes=raw.acquisition_max_network_payload_bytes,
            max_linked_documents=raw.acquisition_max_linked_documents,
            freshness_hours=raw.acquisition_freshness_hours,
        ),
        pdf_extraction=PdfExtractionSettings(
            schema_version=raw.pdf_extraction_schema_version,
            prompt_version=raw.pdf_extraction_prompt_version,
            model_name=raw.pdf_extraction_model_name,
            fallback_model_names=raw.pdf_extraction_fallback_model_names,
            max_price_per_million_tokens_usd=(
                raw.pdf_extraction_max_price_per_million_tokens_usd
            ),
            max_attempts=raw.pdf_extraction_max_attempts,
            backoff_base_seconds=raw.pdf_extraction_backoff_base_seconds,
            max_backoff_seconds=raw.pdf_extraction_max_backoff_seconds,
            retry_jitter_ratio=raw.pdf_extraction_retry_jitter_ratio,
            probe_text_threshold=raw.pdf_extraction_probe_text_threshold,
            skip_historical=raw.pdf_extraction_skip_historical,
        ),
        ocr=OcrSettings(
            enabled=raw.ocr_enabled,
            languages=raw.ocr_languages,
            render_dpi=raw.ocr_render_dpi,
            max_pages=raw.ocr_max_pages,
            max_pixels_per_page=raw.ocr_max_pixels_per_page,
            min_confidence=raw.ocr_min_confidence,
            timeout_seconds=raw.ocr_timeout_seconds,
            tesseract_cmd=raw.ocr_tesseract_cmd,
        ),
        rag=RagSettings(
            chunk_size_chars=raw.chunk_size_chars,
            chunk_overlap_chars=raw.chunk_overlap_chars,
            retrieval_top_k=raw.retrieval_top_k,
            retrieval_min_score=raw.retrieval_min_score,
            embedding_max_attempts=raw.embedding_max_attempts,
            embedding_backoff_base_seconds=raw.embedding_backoff_base_seconds,
            embedding_quota_max_attempts=raw.embedding_quota_max_attempts,
            embedding_quota_backoff_base_seconds=(
                raw.embedding_quota_backoff_base_seconds
            ),
        ),
        intent_resolution=IntentResolutionSettings(
            fuzzy_min_score=raw.intent_fuzzy_min_score,
            fuzzy_min_gap=raw.intent_fuzzy_min_gap,
            max_candidates=raw.intent_max_candidates,
            classifier_max_attempts=raw.intent_classifier_max_attempts,
        ),
        tariff_queries=TariffQuerySettings(
            freshness_days=raw.tariff_freshness_days,
            recent_change_days=raw.tariff_recent_change_days,
            default_history_days=raw.tariff_default_history_days,
            max_history_results=raw.tariff_max_history_results,
            run_poll_seconds=raw.tariff_run_poll_seconds,
            answer_read_model=raw.tariff_answer_read_model,
            retrieval_trace_level=raw.retrieval_trace_level,
            retrieval_log_file=raw.retrieval_log_file,
        ),
        source_discovery=SourceDiscoverySettings(
            policy_version=raw.source_discovery_policy_version,
            prompt_version=raw.source_discovery_prompt_version,
            max_items_per_batch=raw.source_discovery_max_items_per_batch,
            max_chars_per_item=raw.source_discovery_max_chars_per_item,
            max_chars_per_batch=raw.source_discovery_max_chars_per_batch,
            estimated_chars_per_input_token=(
                raw.source_discovery_estimated_chars_per_input_token
            ),
            estimated_output_tokens_per_item=(
                raw.source_discovery_estimated_output_tokens_per_item
            ),
            classifier_max_attempts=raw.source_discovery_classifier_max_attempts,
            classifier_backoff_base_seconds=(
                raw.source_discovery_classifier_backoff_base_seconds
            ),
            classifier_max_backoff_seconds=(
                raw.source_discovery_classifier_max_backoff_seconds
            ),
            classifier_retry_jitter_ratio=(
                raw.source_discovery_classifier_retry_jitter_ratio
            ),
            model_name=raw.source_discovery_model_name,
            fallback_model_names=raw.source_discovery_fallback_model_names,
            max_price_per_million_tokens_usd=(
                raw.source_discovery_max_price_per_million_tokens_usd
            ),
        ),
        semantic_extraction=SemanticExtractionSettings(
            schema_version=raw.semantic_extraction_schema_version,
            prompt_version=raw.semantic_extraction_prompt_version,
            max_evidence_chars_per_item=(
                raw.semantic_extraction_max_evidence_chars_per_item
            ),
            max_chars_per_batch=raw.semantic_extraction_max_chars_per_batch,
            max_items_per_batch=raw.semantic_extraction_max_items_per_batch,
            thinking_budget=raw.semantic_extraction_thinking_budget,
            max_repairs_per_run=raw.semantic_extraction_max_repairs_per_run,
            fallback_model_names=raw.semantic_extraction_fallback_model_names,
        ),
        hitl=HitlSettings(
            document_rank_gap=raw.hitl_document_rank_gap,
            large_rate_change_percentage_points=raw.hitl_large_rate_change_percentage_points,
            review_admin_token=raw.review_admin_token,
        ),
        scheduler=SchedulerSettings(
            timezone=raw.schedule_timezone,
            hour=raw.schedule_hour,
            minute=raw.schedule_minute,
        ),
        observability=ObservabilitySettings(
            log_level=raw.log_level,
            log_file=raw.log_file,
            log_timezone=raw.log_timezone,
            log_max_bytes=raw.log_max_bytes,
            log_backup_count=raw.log_backup_count,
            otel_to_cloud=raw.otel_to_cloud,
            otel_enabled=raw.otel_enabled,
            otel_traces_endpoint=raw.otel_traces_endpoint,
            otel_service_name=raw.otel_service_name,
            otel_trace_content=raw.otel_trace_content,
            otel_export_timeout_seconds=raw.otel_export_timeout_seconds,
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return load_settings()
