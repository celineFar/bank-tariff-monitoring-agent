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
    assert settings.database.url.get_secret_value().startswith("postgresql+asyncpg://")


def test_csv_configuration_is_normalized_and_deduplicated() -> None:
    settings = load_settings(
        _env_file=None,
        allowed_source_hosts="AMERIABANK.AM., www.ameriabank.am, ameriabank.am",
        allowed_download_mime_types="application/pdf, text/html,application/pdf",
        ocr_languages="HYE,eng,hye",
        allow_origins="http://localhost:3000, https://review.example",
    )

    assert settings.http.allowed_source_hosts == (
        "ameriabank.am",
        "www.ameriabank.am",
    )
    assert settings.http.allowed_download_mime_types == (
        "application/pdf",
        "text/html",
    )
    assert settings.ocr.languages == ("hye", "eng")
    assert settings.http.allow_origins == (
        "http://localhost:3000",
        "https://review.example",
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
        ("ocr_min_text_chars_per_page", -1),
        ("ocr_dpi", 149),
        ("ocr_max_pages", 0),
        ("ocr_timeout_seconds", 601),
        ("chunk_size_chars", 199),
        ("chunk_overlap_chars", -1),
        ("retrieval_top_k", 0),
        ("retrieval_min_score", 1.1),
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
