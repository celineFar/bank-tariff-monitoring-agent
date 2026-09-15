from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ameria-tariff-monitor"
    model_name: str = "gemini-3.7-flash"
    embedding_model_name: str = "gemini-embedding-001"
    database_url: str = (
        "postgresql+asyncpg://tariff:tariff@localhost:5432/tariff_monitor"
    )
    allowed_source_hosts: Annotated[tuple[str, ...], NoDecode] = (
        "ameriabank.am",
        "www.ameriabank.am",
    )
    schedule_timezone: str = "Asia/Yerevan"
    schedule_hour: int = Field(default=6, ge=0, le=23)
    schedule_minute: int = Field(default=0, ge=0, le=59)
    download_timeout_seconds: float = Field(default=20, gt=0, le=120)
    max_download_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    ocr_min_text_chars_per_page: int = Field(default=80, ge=0)
    hitl_large_rate_change_percentage_points: float = Field(default=3, gt=0)
    log_level: str = "INFO"

    @field_validator("allowed_source_hosts", mode="before")
    @classmethod
    def parse_hosts(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(host.strip().lower().rstrip(".") for host in value.split(","))
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
