from pathlib import Path
from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.config.models import Environment


class EnvironmentSettings(BaseSettings):
    """Flat environment compatibility layer; application code uses grouped settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ameria-tariff-monitor"
    environment: Environment = Environment.DEVELOPMENT
    artifact_temp_dir: Path = Path("data/artifacts")
    pipeline_audit_enabled: bool = True
    pipeline_audit_dir: Path = Path("artifacts/pipeline-audit")
    gemini_api_key: SecretStr | None = None
    model_name: str = "gemini-3.7-flash"
    embedding_model_name: str = "gemini-embedding-001"
    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://tariff:tariff@localhost:5432/tariff_monitor"
    )
    session_service_uri: SecretStr = SecretStr(
        "postgresql+asyncpg://tariff:tariff@localhost:5432/tariff_monitor"
    )
    allowed_source_hosts: Annotated[tuple[str, ...], NoDecode] = (
        "ameriabank.am",
        "www.ameriabank.am",
    )
    allowed_download_mime_types: Annotated[tuple[str, ...], NoDecode] = (
        "application/pdf",
        "text/html",
    )
    http_user_agent: str = "ameria-tariff-monitor/0.1"
    download_timeout_seconds: float = 20
    http_max_attempts: int = 3
    http_backoff_base_seconds: float = 0.5
    http_retry_jitter_ratio: float = 0.25
    http_max_retry_delay_seconds: float = 120
    max_redirects: int = 5
    max_download_bytes: int = 25 * 1024 * 1024
    acquisition_browser_enabled: bool = True
    acquisition_min_static_text_chars: int = 500
    acquisition_browser_navigation_timeout_seconds: float = 30
    acquisition_browser_settle_milliseconds: int = 750
    acquisition_max_interactions: int = 100
    acquisition_max_network_payloads: int = 25
    acquisition_max_network_payload_bytes: int = 2 * 1024 * 1024
    acquisition_max_linked_documents: int = 10
    acquisition_freshness_hours: float = 1.0
    pdf_extraction_schema_version: str = "2"
    pdf_extraction_prompt_version: str = "2"
    pdf_extraction_model_name: str = "gemini-3.1-flash-lite"
    pdf_extraction_fallback_model_names: Annotated[tuple[str, ...], NoDecode] = ()
    pdf_extraction_max_price_per_million_tokens_usd: float = 1.5
    pdf_extraction_max_attempts: int = 3
    pdf_extraction_backoff_base_seconds: float = 5.0
    pdf_extraction_max_backoff_seconds: float = 60.0
    pdf_extraction_retry_jitter_ratio: float = 0.25
    pdf_extraction_probe_text_threshold: int = 20
    pdf_extraction_skip_historical: bool = True
    ocr_enabled: bool = True
    ocr_languages: str = "hye+eng"
    ocr_render_dpi: int = 200
    ocr_max_pages: int = 20
    ocr_max_pixels_per_page: int = 40_000_000
    ocr_min_confidence: float = 60.0
    ocr_timeout_seconds: float = 60.0
    ocr_tesseract_cmd: str | None = None
    chunk_size_chars: int = 1500
    chunk_overlap_chars: int = 150
    retrieval_top_k: int = 8
    embedding_max_attempts: int = 3
    embedding_backoff_base_seconds: float = 10.0
    embedding_quota_max_attempts: int = 4
    embedding_quota_backoff_base_seconds: float = 30.0
    retrieval_min_score: float = 0.25
    intent_fuzzy_min_score: float = 0.82
    intent_fuzzy_min_gap: float = 0.08
    intent_max_candidates: int = 5
    intent_classifier_max_attempts: int = 2
    tariff_freshness_days: int = 7
    tariff_recent_change_days: int = 60
    tariff_default_history_days: int = 30
    tariff_max_history_results: int = 100
    tariff_run_wait_seconds: float = 120
    tariff_run_poll_seconds: float = 0.5
    tariff_answer_read_model: str = "structured"
    retrieval_trace_level: str = "summary"
    retrieval_log_file: Path | None = None
    source_discovery_policy_version: str = "1"
    source_discovery_prompt_version: str = "1"
    source_discovery_max_items_per_batch: int = 8
    source_discovery_max_chars_per_item: int = 3000
    source_discovery_max_chars_per_batch: int = 18_000
    source_discovery_estimated_chars_per_input_token: float = 4.0
    source_discovery_estimated_output_tokens_per_item: int = 160
    source_discovery_classifier_max_attempts: int = 3
    source_discovery_classifier_backoff_base_seconds: float = 5.0
    source_discovery_classifier_max_backoff_seconds: float = 60.0
    source_discovery_classifier_retry_jitter_ratio: float = 0.25
    source_discovery_model_name: str | None = "gemini-3.1-flash-lite"
    source_discovery_fallback_model_names: Annotated[
        tuple[str, ...], NoDecode
    ] = ()
    source_discovery_max_price_per_million_tokens_usd: float = 1.5
    semantic_extraction_schema_version: str = "5"
    semantic_extraction_prompt_version: str = "5"
    semantic_extraction_max_evidence_chars_per_item: int = 5000
    semantic_extraction_max_chars_per_batch: int = 20_000
    semantic_extraction_max_items_per_batch: int = 20
    semantic_extraction_thinking_budget: int = 0
    semantic_extraction_max_repairs_per_run: int = 3
    semantic_extraction_fallback_model_names: Annotated[tuple[str, ...], NoDecode] = ()
    hitl_document_rank_gap: float = 0.05
    hitl_large_rate_change_percentage_points: float = 3
    review_admin_token: SecretStr | None = None
    schedule_timezone: str = "Asia/Yerevan"
    schedule_hour: int = 6
    schedule_minute: int = 0
    log_level: str = "INFO"
    log_file: Path | None = None
    log_timezone: str = "Asia/Yerevan"
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 10
    otel_to_cloud: bool = False
    otel_enabled: bool = False
    otel_traces_endpoint: str | None = None
    otel_service_name: str = "tariff-monitor"
    otel_trace_content: str = "none"
    otel_export_timeout_seconds: float = 10.0
    allow_origins: Annotated[tuple[str, ...], NoDecode] = ("http://localhost:3000",)

    @field_validator(
        "allowed_source_hosts",
        "allowed_download_mime_types",
        "allow_origins",
        "source_discovery_fallback_model_names",
        "pdf_extraction_fallback_model_names",
        "semantic_extraction_fallback_model_names",
        mode="before",
    )
    @classmethod
    def parse_csv_tuple(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return value
