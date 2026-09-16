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
    max_html_bytes: int = 5 * 1024 * 1024
    ocr_languages: Annotated[tuple[str, ...], NoDecode] = ("hye", "eng")
    ocr_min_text_chars_per_page: int = 80
    ocr_dpi: int = 300
    ocr_max_pages: int = 50
    ocr_timeout_seconds: float = 60
    chunk_size_chars: int = 1500
    chunk_overlap_chars: int = 150
    retrieval_top_k: int = 8
    retrieval_min_score: float = 0.25
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
        mode="before",
    )
    @classmethod
    def parse_csv_tuple(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return value
