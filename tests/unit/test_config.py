from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.config import Environment, get_settings, load_settings


def test_defaults_match_the_approved_architecture() -> None:
    settings = load_settings(_env_file=None)

    assert settings.models.generation_model == "gemini-3.7-flash"
    assert settings.http.allowed_source_hosts == (
        "ameriabank.am",
        "www.ameriabank.am",
    )
    assert settings.scheduler.timezone == "Asia/Yerevan"
    assert (settings.scheduler.hour, settings.scheduler.minute) == (6, 0)
    assert settings.http.retry_jitter_ratio == 0.25
    assert settings.http.max_retry_delay_seconds == 120
    assert settings.acquisition.browser_enabled is True
    assert settings.acquisition.max_interactions == 100
    assert settings.pdf_extraction.model_name == "gemini-3.1-flash-lite"
    assert settings.pdf_extraction.fallback_model_names == (
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
    )
    assert settings.pdf_extraction.max_price_per_million_tokens_usd == 4.0
    assert settings.source_discovery.max_items_per_batch == 8
    assert settings.source_discovery.max_chars_per_item == 3000
    assert settings.source_discovery.max_chars_per_batch == 18_000
    assert settings.source_discovery.classifier_max_attempts == 3
    assert settings.source_discovery.classifier_backoff_base_seconds == 5.0
    assert settings.source_discovery.fallback_model_names == (
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    )
    assert settings.source_discovery.max_price_per_million_tokens_usd == 4.0
    assert settings.intent_resolution.fuzzy_min_score == 0.82
    assert settings.intent_resolution.fuzzy_min_gap == 0.08
    assert settings.intent_resolution.max_candidates == 5
    assert settings.intent_resolution.classifier_max_attempts == 2
    assert settings.tariff_queries.freshness_days == 7
    assert settings.tariff_queries.recent_change_days == 60
    assert settings.tariff_queries.default_history_days == 30
    assert settings.tariff_queries.run_wait_seconds == 120
    assert settings.database.url.get_secret_value().startswith("postgresql+asyncpg://")


def test_csv_configuration_is_normalized_and_deduplicated() -> None:
    settings = load_settings(
        _env_file=None,
        allowed_source_hosts="AMERIABANK.AM., www.ameriabank.am, ameriabank.am",
        allowed_download_mime_types="application/pdf, text/html,application/pdf",
        pdf_extraction_fallback_model_names=(
            "gemini-3.5-flash-lite,gemini-3.6-flash"
        ),
        allow_origins="http://localhost:3000, https://review.example",
        source_discovery_fallback_model_names="gemini-3.5-flash-lite,gemini-3.1-flash-lite",
    )

    assert settings.http.allowed_source_hosts == (
        "ameriabank.am",
        "www.ameriabank.am",
    )
    assert settings.http.allowed_download_mime_types == (
        "application/pdf",
        "text/html",
    )
    assert settings.pdf_extraction.fallback_model_names == (
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
    )
    assert settings.http.allow_origins == (
        "http://localhost:3000",
        "https://review.example",
    )
    assert settings.source_discovery.fallback_model_names == (
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    )


def test_settings_load_from_deployment_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOWED_SOURCE_HOSTS", "ameriabank.am,www.ameriabank.am")
    monkeypatch.setenv("SCHEDULE_HOUR", "7")
    monkeypatch.setenv("OTEL_TO_CLOUD", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "runtime-secret")
    monkeypatch.setenv("HTTP_RETRY_JITTER_RATIO", "0.5")
    monkeypatch.setenv("HTTP_MAX_RETRY_DELAY_SECONDS", "30")

    settings = load_settings(_env_file=None)

    assert settings.http.allowed_source_hosts == (
        "ameriabank.am",
        "www.ameriabank.am",
    )
    assert settings.scheduler.hour == 7
    assert settings.observability.otel_to_cloud is True
    assert settings.http.retry_jitter_ratio == 0.5
    assert settings.http.max_retry_delay_seconds == 30
    assert settings.models.api_key is not None
    assert settings.models.api_key.get_secret_value() == "runtime-secret"


@pytest.mark.parametrize(
    "hostname",
    [
        "https://ameriabank.am",
        "ameriabank.am/path",
        "*.ameriabank.am",
        "127.0.0.1",
        "bad_label.ameriabank.am",
        "",
    ],
)
def test_invalid_allowlisted_hostname_fails_startup(hostname: str) -> None:
    with pytest.raises(ValidationError):
        load_settings(_env_file=None, allowed_source_hosts=hostname)


def test_non_postgresql_database_fails_startup() -> None:
    with pytest.raises(ValidationError, match="must use PostgreSQL"):
        load_settings(_env_file=None, database_url="sqlite:///local.db")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("allowed_download_mime_types", "pdf"),
        ("allowed_download_mime_types", "application /pdf"),
        ("allow_origins", "*"),
        ("allow_origins", "https://review.example/path"),
        ("allow_origins", "javascript://review.example"),
    ],
)
def test_invalid_list_configuration_fails_startup(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        load_settings(_env_file=None, **{field: value})


def test_invalid_timezone_fails_startup() -> None:
    with pytest.raises(ValidationError, match="unknown IANA timezone"):
        load_settings(_env_file=None, schedule_timezone="Mars/Olympus")


def test_chunk_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValidationError, match="CHUNK_OVERLAP_CHARS"):
        load_settings(_env_file=None, chunk_size_chars=500, chunk_overlap_chars=500)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("download_timeout_seconds", 0),
        ("http_max_attempts", 6),
        ("http_backoff_base_seconds", -1),
        ("http_retry_jitter_ratio", 1.1),
        ("http_max_retry_delay_seconds", 0),
        ("max_redirects", 11),
        ("max_download_bytes", 0),
        ("acquisition_min_static_text_chars", -1),
        ("acquisition_browser_navigation_timeout_seconds", 0),
        ("acquisition_browser_settle_milliseconds", 10_001),
        ("acquisition_max_interactions", 101),
        ("acquisition_max_network_payloads", 201),
        ("acquisition_max_network_payload_bytes", 0),
        ("acquisition_max_linked_documents", 51),
        ("pdf_extraction_probe_text_threshold", -1),
        ("pdf_extraction_max_attempts", 0),
        ("pdf_extraction_backoff_base_seconds", -1),
        ("pdf_extraction_max_price_per_million_tokens_usd", 0),
        ("chunk_size_chars", 199),
        ("chunk_overlap_chars", -1),
        ("retrieval_top_k", 0),
        ("retrieval_min_score", 1.1),
        ("intent_fuzzy_min_score", 1.1),
        ("intent_fuzzy_min_gap", 1.1),
        ("intent_max_candidates", 1),
        ("intent_classifier_max_attempts", 0),
        ("source_discovery_max_items_per_batch", 0),
        ("source_discovery_max_chars_per_item", 499),
        ("source_discovery_max_chars_per_batch", 999),
        ("source_discovery_classifier_max_attempts", 0),
        ("source_discovery_classifier_retry_jitter_ratio", 1.1),
        ("hitl_document_rank_gap", 1.1),
        ("hitl_large_rate_change_percentage_points", 0),
        ("schedule_hour", 24),
        ("schedule_minute", 60),
    ],
)
def test_domain_models_reject_out_of_range_environment_values(
    field: str, value: int | float
) -> None:
    with pytest.raises(ValidationError):
        load_settings(_env_file=None, **{field: value})


def test_production_requires_api_key_and_masks_it() -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        load_settings(_env_file=None, environment=Environment.PRODUCTION)

    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        load_settings(
            _env_file=None,
            environment=Environment.PRODUCTION,
            gemini_api_key="",
        )

    settings = load_settings(
        _env_file=None,
        environment=Environment.PRODUCTION,
        gemini_api_key="super-secret-value",
    )
    assert isinstance(settings.models.api_key, SecretStr)
    assert "super-secret-value" not in repr(settings)


def test_source_discovery_item_limit_cannot_exceed_batch_limit() -> None:
    with pytest.raises(ValidationError, match="item character limit"):
        load_settings(
            _env_file=None,
            source_discovery_max_chars_per_item=2000,
            source_discovery_max_chars_per_batch=1000,
        )


def test_settings_factory_is_process_cached() -> None:
    get_settings.cache_clear()
    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()


def test_settings_groups_are_immutable() -> None:
    settings = load_settings(_env_file=None)

    with pytest.raises(ValidationError, match="frozen"):
        settings.http.max_attempts = 4


def test_example_environment_contains_no_api_key() -> None:
    lines = Path(".env.example").read_text(encoding="utf-8").splitlines()
    api_key_line = next(line for line in lines if line.startswith("GEMINI_API_KEY="))
    assert api_key_line == "GEMINI_API_KEY="
