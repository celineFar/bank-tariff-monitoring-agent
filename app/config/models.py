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


class RetrievalTraceLevel(StrEnum):
    """How much of one retrieval to write to the `tariff.retrieval` logger."""

    OFF = "off"
    SUMMARY = "summary"
    STEPS = "steps"
    VERBOSE = "verbose"


class AnswerReadModel(StrEnum):
    """Which read model answers ordinary tariff questions."""

    STRUCTURED = "structured"
    LEGACY = "legacy"


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
    pipeline_audit_enabled: bool = True
    pipeline_audit_dir: Path = Path("artifacts/pipeline-audit")

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


class AcquisitionSettings(SettingsGroup):
    browser_enabled: bool = True
    min_static_text_chars: int = Field(default=500, ge=0, le=100_000)
    browser_navigation_timeout_seconds: float = Field(default=30, gt=0, le=120)
    browser_settle_milliseconds: int = Field(default=750, ge=0, le=10_000)
    max_interactions: int = Field(default=100, ge=0, le=100)
    max_network_payloads: int = Field(default=25, ge=0, le=200)
    max_network_payload_bytes: int = Field(default=2 * 1024 * 1024, gt=0)
    max_linked_documents: int = Field(default=10, ge=0, le=50)
    # How long an acquisition stays usable. Within the window a run reuses the
    # stored page artifact instead of fetching the bank again; 0 disables reuse
    # and every run re-acquires. Only acquisition is skipped -- normalization
    # onward still execute, and hit their own content-addressed caches.
    freshness_hours: float = Field(default=1.0, ge=0, le=720)


class PdfExtractionSettings(SettingsGroup):
    schema_version: str = Field(default="2", min_length=1, max_length=50)
    prompt_version: str = Field(default="2", min_length=1, max_length=50)
    model_name: str = "gemini-3.1-flash-lite"
    fallback_model_names: tuple[str, ...] = ()
    max_price_per_million_tokens_usd: float = Field(default=1.5, gt=0, le=100)
    max_attempts: int = Field(default=3, ge=1, le=10)
    backoff_base_seconds: float = Field(default=5.0, ge=0, le=300)
    max_backoff_seconds: float = Field(default=60.0, ge=0, le=900)
    retry_jitter_ratio: float = Field(default=0.25, ge=0, le=1)
    probe_text_threshold: int = Field(default=20, ge=0, le=10_000)
    skip_historical: bool = True

    @field_validator("fallback_model_names")
    @classmethod
    def validate_fallback_models(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value if item.strip())
        if len(normalized) > 5 or len(set(normalized)) != len(normalized):
            raise ValueError("PDF fallback models must be unique and at most five")
        return normalized

    @model_validator(mode="after")
    def validate_retry_limits(self) -> PdfExtractionSettings:
        if self.backoff_base_seconds > self.max_backoff_seconds:
            raise ValueError("PDF extraction base backoff must not exceed maximum")
        return self


class OcrSettings(SettingsGroup):
    """Local OCR fallback for PDF pages that carry no text layer."""

    enabled: bool = True
    languages: str = "hye+eng"
    render_dpi: int = Field(default=200, ge=72, le=600)
    max_pages: int = Field(default=20, ge=1, le=500)
    max_pixels_per_page: int = Field(default=40_000_000, ge=10_000, le=500_000_000)
    min_confidence: float = Field(default=60.0, ge=0, le=100)
    timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    tesseract_cmd: str | None = None

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, value: str) -> str:
        """Accept `+`, `,`, or whitespace separators; emit tesseract's `+` form.

        Older local `.env` files wrote `hye,eng`, so both spellings are tolerated
        rather than failing startup on a separator.
        """
        parts = [part for part in re.split(r"[+,\s]+", value.strip()) if part]
        if not parts or len(parts) > 10:
            raise ValueError("OCR_LANGUAGES must name between one and ten codes")
        if any(not re.fullmatch(r"[a-z]{3}(_[A-Za-z]+)?", part) for part in parts):
            raise ValueError("OCR_LANGUAGES codes must be three-letter tesseract codes")
        return "+".join(parts)

    @field_validator("tesseract_cmd", mode="before")
    @classmethod
    def empty_command_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class RagSettings(SettingsGroup):
    chunk_size_chars: int = Field(default=1500, ge=200, le=20_000)
    chunk_overlap_chars: int = Field(default=150, ge=0)
    retrieval_top_k: int = Field(default=8, ge=1, le=50)
    retrieval_min_score: float = Field(default=0.25, ge=0, le=1)
    # Embedding retries are split by what the refusal means. A 5xx is transient
    # and clears in seconds; a 429 is a provider quota and clears on its own
    # schedule, so giving up on it after 30 seconds discards a whole run for a
    # blip. The quota wait stays in minutes all the same: a run must not hold a
    # worker and a waiting chat session for a daily quota window, which is what
    # deferring the index is for.
    embedding_max_attempts: int = Field(default=3, ge=1, le=10)
    embedding_backoff_base_seconds: float = Field(default=10.0, ge=0, le=300)
    embedding_quota_max_attempts: int = Field(default=4, ge=1, le=10)
    embedding_quota_backoff_base_seconds: float = Field(default=30.0, ge=0, le=600)

    @model_validator(mode="after")
    def validate_chunk_sizes(self) -> RagSettings:
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError(
                "CHUNK_OVERLAP_CHARS must be smaller than CHUNK_SIZE_CHARS"
            )
        return self


class IntentResolutionSettings(SettingsGroup):
    fuzzy_min_score: float = Field(default=0.82, ge=0, le=1)
    fuzzy_min_gap: float = Field(default=0.08, ge=0, le=1)
    max_candidates: int = Field(default=5, ge=2, le=20)
    classifier_max_attempts: int = Field(default=2, ge=1, le=5)


class TariffQuerySettings(SettingsGroup):
    freshness_days: int = Field(default=7, ge=1, le=365)
    recent_change_days: int = Field(default=60, ge=1, le=3650)
    default_history_days: int = Field(default=30, ge=1, le=3650)
    max_history_results: int = Field(default=100, ge=1, le=1000)
    run_poll_seconds: float = Field(default=0.5, gt=0, le=10)
    # Reversible cutover switch; `legacy` restores the old RAG answer path.
    answer_read_model: AnswerReadModel = AnswerReadModel.STRUCTURED
    # `verbose` writes text projected from source documents; keep it local.
    retrieval_trace_level: RetrievalTraceLevel = RetrievalTraceLevel.SUMMARY
    retrieval_log_file: Path | None = None


class SourceDiscoverySettings(SettingsGroup):
    policy_version: str = Field(default="1", min_length=1, max_length=50)
    prompt_version: str = Field(default="1", min_length=1, max_length=50)
    max_items_per_batch: int = Field(default=8, ge=1, le=50)
    max_chars_per_item: int = Field(default=3000, ge=500, le=12_000)
    max_chars_per_batch: int = Field(default=18_000, ge=1000, le=100_000)
    estimated_chars_per_input_token: float = Field(default=4.0, gt=0, le=20)
    estimated_output_tokens_per_item: int = Field(default=160, ge=0, le=10_000)
    classifier_max_attempts: int = Field(default=3, ge=1, le=10)
    classifier_backoff_base_seconds: float = Field(default=5.0, ge=0, le=300)
    classifier_max_backoff_seconds: float = Field(default=60.0, ge=0, le=900)
    classifier_retry_jitter_ratio: float = Field(default=0.25, ge=0, le=1)
    model_name: str | None = "gemini-3.1-flash-lite"
    fallback_model_names: tuple[str, ...] = ()
    max_price_per_million_tokens_usd: float = Field(default=1.5, gt=0, le=100)

    @field_validator("fallback_model_names")
    @classmethod
    def validate_fallback_models(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value if item.strip())
        if len(normalized) > 5:
            raise ValueError(
                "at most five source discovery fallback models are allowed"
            )
        if len(set(normalized)) != len(normalized):
            raise ValueError("source discovery fallback models must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_batch_limits(self) -> SourceDiscoverySettings:
        if self.max_chars_per_item > self.max_chars_per_batch:
            raise ValueError(
                "source discovery item character limit must not exceed batch limit"
            )
        if self.classifier_backoff_base_seconds > self.classifier_max_backoff_seconds:
            raise ValueError(
                "source discovery classifier base backoff must not exceed maximum"
            )
        return self


class SemanticExtractionSettings(SettingsGroup):
    # Empty by default: the successor to a retired extraction model is an
    # operational choice, so it is configured rather than assumed here.
    fallback_model_names: tuple[str, ...] = ()
    schema_version: str = Field(default="4", min_length=1, max_length=50)
    prompt_version: str = Field(default="4", min_length=1, max_length=50)
    max_evidence_chars_per_item: int = Field(default=5000, ge=500, le=20_000)
    max_chars_per_batch: int = Field(default=20_000, ge=1000, le=100_000)
    max_items_per_batch: int = Field(default=20, ge=1, le=100)
    thinking_budget: int = Field(default=0, ge=-1, le=24_576)
    max_repairs_per_run: int = Field(default=3, ge=0, le=50)

    @field_validator("fallback_model_names")
    @classmethod
    def validate_fallback_models(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value if item.strip())
        if len(normalized) > 5:
            raise ValueError(
                "at most five semantic extraction fallback models are allowed"
            )
        if len(set(normalized)) != len(normalized):
            raise ValueError("semantic extraction fallback models must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_batch_limits(self) -> SemanticExtractionSettings:
        if self.max_evidence_chars_per_item > self.max_chars_per_batch:
            raise ValueError(
                "semantic extraction item character limit must not exceed batch limit"
            )
        return self


class HitlSettings(SettingsGroup):
    document_rank_gap: float = Field(default=0.05, ge=0, le=1)
    large_rate_change_percentage_points: float = Field(default=3, gt=0)
    review_admin_token: SecretStr | None = None


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


class TraceContentMode(StrEnum):
    """How much model content a exported span may carry.

    `NONE` keeps prompts and responses out of exported spans entirely. `MAPPED`
    keeps them, but only after the exporter has rewritten ADK's vendor-specific
    attributes into the names a trace backend reads, so the content that leaves
    the process is exactly what the exporter chose to emit.
    """

    NONE = "none"
    MAPPED = "mapped"


class ObservabilitySettings(SettingsGroup):
    log_level: str = "INFO"
    log_file: Path | None = None
    log_timezone: str = "Asia/Yerevan"
    log_max_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    log_backup_count: int = Field(default=10, ge=1)
    otel_to_cloud: bool = False
    otel_enabled: bool = False
    otel_traces_endpoint: str | None = None
    otel_service_name: str = "tariff-monitor"
    otel_trace_content: TraceContentMode = TraceContentMode.NONE
    otel_export_timeout_seconds: float = Field(default=10.0, gt=0)

    @field_validator("otel_traces_endpoint")
    @classmethod
    def validate_traces_endpoint(cls, value: str | None) -> str | None:
        """Reject anything that is not an absolute http(s) OTLP URL.

        A malformed endpoint otherwise fails silently inside the batch
        exporter's background thread, which looks identical to "tracing is off".
        """
        if value is None:
            return None
        candidate = value.strip()
        if not candidate:
            return None
        parts = urlsplit(candidate)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError(
                f"otel_traces_endpoint must be an absolute http(s) URL: {value}"
            )
        return candidate

    @field_validator("log_timezone")
    @classmethod
    def validate_log_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown IANA timezone: {value}") from exc
        return value

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
    acquisition: AcquisitionSettings
    pdf_extraction: PdfExtractionSettings
    ocr: OcrSettings
    rag: RagSettings
    intent_resolution: IntentResolutionSettings
    tariff_queries: TariffQuerySettings
    source_discovery: SourceDiscoverySettings
    semantic_extraction: SemanticExtractionSettings
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
