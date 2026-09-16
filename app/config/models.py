from __future__ import annotations

import ipaddress
import logging
import re
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from sqlalchemy.engine import make_url

_HOST_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_LOG_LEVELS = frozenset(logging.getLevelNamesMapping())


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class SettingsGroup(BaseModel):
    model_config = ConfigDict(frozen=True)


class ApplicationSettings(SettingsGroup):
    name: str = "ameria-tariff-monitor"
    environment: Environment = Environment.DEVELOPMENT
    artifact_temp_dir: Path = Path("data/artifacts")

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("application name must not be empty")
        return value


class ModelSettings(SettingsGroup):
    api_key: SecretStr | None = None
    generation_model: str = "gemini-3.7-flash"
    embedding_model: str = "gemini-embedding-001"

    @field_validator("api_key", mode="before")
    @classmethod
    def empty_secret_is_unset(cls, value: object) -> object:
        if isinstance(value, SecretStr):
            return value if value.get_secret_value() else None
        return None if value == "" else value

    @field_validator("generation_model", "embedding_model")
    @classmethod
    def require_model_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("model name must not be empty")
        return value


class DatabaseSettings(SettingsGroup):
    url: SecretStr = SecretStr(
        "postgresql+asyncpg://tariff:tariff@localhost:5432/tariff_monitor"
    )
    session_service_uri: SecretStr = SecretStr(
        "postgresql+asyncpg://tariff:tariff@localhost:5432/tariff_monitor"
    )

    @field_validator("url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        url = make_url(value.get_secret_value())
        if url.get_backend_name() != "postgresql":
            raise ValueError("DATABASE_URL must use PostgreSQL")
        if not url.database:
            raise ValueError("DATABASE_URL must include a database name")
        return value

    @field_validator("session_service_uri")
    @classmethod
    def validate_session_uri(cls, value: SecretStr) -> SecretStr:
        raw_value = value.get_secret_value()
        if raw_value.startswith("shared://"):
            return value
        url = make_url(raw_value)
        if url.get_backend_name() != "postgresql" or not url.database:
            raise ValueError("SESSION_SERVICE_URI must use PostgreSQL or shared://")
        return value


class HttpSettings(SettingsGroup):
    allowed_source_hosts: tuple[str, ...] = ("ameriabank.am", "www.ameriabank.am")
    allowed_download_mime_types: tuple[str, ...] = ("application/pdf", "text/html")
    user_agent: str = "ameria-tariff-monitor/0.1"
    timeout_seconds: float = Field(default=20, gt=0, le=120)
    max_attempts: int = Field(default=3, ge=1, le=5)
    backoff_base_seconds: float = Field(default=0.5, ge=0, le=10)
    retry_jitter_ratio: float = Field(default=0.25, ge=0, le=1)
    max_retry_delay_seconds: float = Field(default=120, gt=0, le=3600)
    max_redirects: int = Field(default=5, ge=0, le=10)
    max_download_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    max_html_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    allow_origins: tuple[str, ...] = ("http://localhost:3000",)

    @field_validator("user_agent")
    @classmethod
    def require_user_agent(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("HTTP user agent must not be empty")
        return value

    @field_validator("allowed_source_hosts")
    @classmethod
    def validate_source_hosts(cls, hosts: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for raw_host in hosts:
            host = raw_host.strip().lower().rstrip(".")
            if not host or "://" in host or any(c in host for c in "/@*?#:"):
                raise ValueError(f"invalid allowlisted hostname: {raw_host!r}")
            try:
                ipaddress.ip_address(host)
            except ValueError:
                pass
            else:
                raise ValueError("IP-literal hosts are not allowed")
            if len(host) > 253 or not all(
                _HOST_LABEL.fullmatch(label) for label in host.split(".")
            ):
                raise ValueError(f"invalid allowlisted hostname: {raw_host!r}")
            if host not in normalized:
                normalized.append(host)
        if not normalized:
            raise ValueError("at least one source host is required")
        return tuple(normalized)

    @field_validator("allowed_download_mime_types")
    @classmethod
    def validate_mime_types(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(value.lower() for value in values))
        if not normalized or any(
            value.count("/") != 1 or any(c.isspace() for c in value)
            for value in normalized
        ):
            raise ValueError("download MIME types must use type/subtype syntax")
        return normalized

    @field_validator("allow_origins")
    @classmethod
    def validate_cors_origins(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for value in values:
            parsed = urlsplit(value)
            if (
                value == "*"
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(f"invalid CORS origin: {value!r}")
            origin = f"{parsed.scheme}://{parsed.netloc.lower()}"
            if origin not in normalized:
                normalized.append(origin)
        return tuple(normalized)


class OcrSettings(SettingsGroup):
    languages: tuple[str, ...] = ("hye", "eng")
    min_text_chars_per_page: int = Field(default=80, ge=0)
    dpi: int = Field(default=300, ge=150, le=600)
    max_pages: int = Field(default=50, ge=1, le=500)
    timeout_seconds: float = Field(default=60, gt=0, le=600)

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(value.lower() for value in values))
        if not normalized:
            raise ValueError("at least one OCR language is required")
        return normalized


class RagSettings(SettingsGroup):
    chunk_size_chars: int = Field(default=1500, ge=200, le=20_000)
    chunk_overlap_chars: int = Field(default=150, ge=0)
    retrieval_top_k: int = Field(default=8, ge=1, le=50)
    retrieval_min_score: float = Field(default=0.25, ge=0, le=1)

    @model_validator(mode="after")
    def validate_chunk_sizes(self) -> RagSettings:
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError(
                "CHUNK_OVERLAP_CHARS must be smaller than CHUNK_SIZE_CHARS"
            )
        return self


class HitlSettings(SettingsGroup):
    document_rank_gap: float = Field(default=0.05, ge=0, le=1)
    large_rate_change_percentage_points: float = Field(default=3, gt=0)


class SchedulerSettings(SettingsGroup):
    timezone: str = "Asia/Yerevan"
    hour: int = Field(default=6, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown IANA timezone: {value}") from exc
        return value


class ObservabilitySettings(SettingsGroup):
    log_level: str = "INFO"
    otel_to_cloud: bool = False

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in _LOG_LEVELS:
            raise ValueError(f"unsupported log level: {value}")
        return normalized


class Settings(SettingsGroup):
    application: ApplicationSettings
    models: ModelSettings
    database: DatabaseSettings
    http: HttpSettings
    ocr: OcrSettings
    rag: RagSettings
    hitl: HitlSettings
    scheduler: SchedulerSettings
    observability: ObservabilitySettings

    @model_validator(mode="after")
    def require_production_secret(self) -> Settings:
        if (
            self.application.environment is Environment.PRODUCTION
            and self.models.api_key is None
        ):
            raise ValueError("GEMINI_API_KEY is required in production")
        return self
