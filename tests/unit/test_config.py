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

    settings = load_settings(_env_file=None)

    assert settings.http.allowed_source_hosts == (
        "ameriabank.am",
        "www.ameriabank.am",
    )
    assert settings.scheduler.hour == 7
    assert settings.observability.otel_to_cloud is True
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


def test_production_requires_api_key_and_masks_it() -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        load_settings(_env_file=None, environment=Environment.PRODUCTION)

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
