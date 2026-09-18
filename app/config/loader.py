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
    ModelSettings,
    ObservabilitySettings,
    OcrSettings,
    RagSettings,
    SchedulerSettings,
    Settings,
    SourceDiscoverySettings,
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
        ),
        ocr=OcrSettings(
            languages=raw.ocr_languages,
            min_text_chars_per_page=raw.ocr_min_text_chars_per_page,
            dpi=raw.ocr_dpi,
            max_pages=raw.ocr_max_pages,
            timeout_seconds=raw.ocr_timeout_seconds,
        ),
        rag=RagSettings(
            chunk_size_chars=raw.chunk_size_chars,
            chunk_overlap_chars=raw.chunk_overlap_chars,
            retrieval_top_k=raw.retrieval_top_k,
            retrieval_min_score=raw.retrieval_min_score,
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
            fallback_model_names=raw.source_discovery_fallback_model_names,
            max_price_per_million_tokens_usd=(
                raw.source_discovery_max_price_per_million_tokens_usd
            ),
        ),
        hitl=HitlSettings(
            document_rank_gap=raw.hitl_document_rank_gap,
            large_rate_change_percentage_points=raw.hitl_large_rate_change_percentage_points,
        ),
        scheduler=SchedulerSettings(
            timezone=raw.schedule_timezone,
            hour=raw.schedule_hour,
            minute=raw.schedule_minute,
        ),
        observability=ObservabilitySettings(
            log_level=raw.log_level,
            otel_to_cloud=raw.otel_to_cloud,
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return load_settings()
