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
    ocr_languages: Annotated[tuple[str, ...], NoDecode] = ("hye", "eng")
    ocr_min_text_chars_per_page: int = 80
    ocr_dpi: int = 300
    ocr_max_pages: int = 50
    ocr_timeout_seconds: float = 60
    chunk_size_chars: int = 1500
    chunk_overlap_chars: int = 150
    retrieval_top_k: int = 8
    retrieval_min_score: float = 0.25
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
    source_discovery_fallback_model_names: Annotated[tuple[str, ...], NoDecode] = (
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    )
    source_discovery_max_price_per_million_tokens_usd: float = 4.0
    hitl_document_rank_gap: float = 0.05
    hitl_large_rate_change_percentage_points: float = 3
    schedule_timezone: str = "Asia/Yerevan"
    schedule_hour: int = 6
    schedule_minute: int = 0
    log_level: str = "INFO"
    otel_to_cloud: bool = False
    allow_origins: Annotated[tuple[str, ...], NoDecode] = ("http://localhost:3000",)

    @field_validator(
        "allowed_source_hosts",
        "allowed_download_mime_types",
        "ocr_languages",
        "allow_origins",
        "source_discovery_fallback_model_names",
        mode="before",
    )
    @classmethod
    def parse_csv_tuple(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return value
