from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
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
    download_timeout_seconds: float = Field(default=20, gt=0, le=120)
    http_max_attempts: int = Field(default=3, ge=1, le=5)
    http_backoff_base_seconds: float = Field(default=0.5, ge=0, le=10)
    max_redirects: int = Field(default=5, ge=0, le=10)
    max_download_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    ocr_languages: Annotated[tuple[str, ...], NoDecode] = ("hye", "eng")
    ocr_min_text_chars_per_page: int = Field(default=80, ge=0)
    ocr_dpi: int = Field(default=300, ge=150, le=600)
    ocr_max_pages: int = Field(default=50, ge=1, le=500)
    ocr_timeout_seconds: float = Field(default=60, gt=0, le=600)
    chunk_size_chars: int = Field(default=1500, ge=200, le=20_000)
    chunk_overlap_chars: int = Field(default=150, ge=0)
    retrieval_top_k: int = Field(default=8, ge=1, le=50)
    retrieval_min_score: float = Field(default=0.25, ge=0, le=1)
    hitl_document_rank_gap: float = Field(default=0.05, ge=0, le=1)
    hitl_large_rate_change_percentage_points: float = Field(default=3, gt=0)
    schedule_timezone: str = "Asia/Yerevan"
    schedule_hour: int = Field(default=6, ge=0, le=23)
    schedule_minute: int = Field(default=0, ge=0, le=59)
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

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def empty_secret_is_unset(cls, value: object) -> object:
        return None if value == "" else value
