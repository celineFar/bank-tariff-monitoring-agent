from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config.models import ObservabilitySettings
from app.services.model_call_usage import MODEL_USAGE_LOGGER_NAME
from app.services.retrieval_trace import RETRIEVAL_LOGGER_NAME


class ZonedFormatter(logging.Formatter):
    def __init__(self, timezone: str) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s: %(message)s")
        self._timezone = ZoneInfo(timezone)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return datetime.fromtimestamp(record.created, self._timezone).isoformat(
            timespec="milliseconds"
        )


def configure_application_logging(
    settings: ObservabilitySettings,
    *,
    include_uvicorn: bool = False,
    console_output: bool = True,
) -> None:
    """Keep console logs and archive bounded, timezone-aware files when configured."""
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    logging.captureWarnings(True)
    formatter = ZonedFormatter(settings.log_timezone)
    if not root.handlers and console_output:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        root.addHandler(console)

    if settings.log_file is None:
        return
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    file_path = str(settings.log_file.resolve())
    archive = next(
        (
            handler
            for handler in root.handlers
            if isinstance(handler, RotatingFileHandler)
            and handler.baseFilename == file_path
        ),
        None,
    )
    if archive is None:
        archive = RotatingFileHandler(
            file_path,
            maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
        )
        archive.setFormatter(formatter)
        root.addHandler(archive)
    if include_uvicorn:
        for logger in (
            logging.getLogger("uvicorn"),
            logging.getLogger("uvicorn.access"),
        ):
            if archive not in logger.handlers:
                logger.addHandler(archive)

    # Model usage gets its own file beside the application log. It answers "what
    # has this cost, and which model is running out" without reading a whole
    # run's log, and it is derived rather than configured so it is never off by
    # accident -- the question it answers only gets asked once spending has
    # already happened.
    configure_model_usage_logging(
        settings.log_file.parent / "model_usage.log",
        timezone=settings.log_timezone,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )


def configure_retrieval_logging(
    log_file: Path | None, *, timezone: str, max_bytes: int, backup_count: int
) -> None:
    """Give the retrieval trace its own rotating file, separate from the app log.

    The `tariff.retrieval` logger keeps propagating to the root handlers, so the
    trace still reaches the console; the extra file simply isolates it for
    replay. Calling this twice with the same path adds no second handler.
    """
    retrieval = logging.getLogger(RETRIEVAL_LOGGER_NAME)
    retrieval.setLevel(logging.INFO)
    if log_file is None:
        return
    log_file.parent.mkdir(parents=True, exist_ok=True)
    resolved = str(log_file.resolve())
    if any(
        isinstance(handler, RotatingFileHandler) and handler.baseFilename == resolved
        for handler in retrieval.handlers
    ):
        return
    handler = RotatingFileHandler(
        resolved, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler.setFormatter(ZonedFormatter(timezone))
    retrieval.addHandler(handler)


def configure_model_usage_logging(
    log_file: Path | None, *, timezone: str, max_bytes: int, backup_count: int
) -> None:
    """Give model calls their own rotating file, separate from the app log.

    The `tariff.model_usage` logger keeps propagating to the root handlers, so
    each call still reaches the console and the application log; the extra file
    simply isolates the ledger for auditing spend and quota. Calling this twice
    with the same path adds no second handler.
    """
    usage = logging.getLogger(MODEL_USAGE_LOGGER_NAME)
    usage.setLevel(logging.INFO)
    if log_file is None:
        return
    log_file.parent.mkdir(parents=True, exist_ok=True)
    resolved = str(log_file.resolve())
    if any(
        isinstance(handler, RotatingFileHandler) and handler.baseFilename == resolved
        for handler in usage.handlers
    ):
        return
    handler = RotatingFileHandler(
        resolved, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler.setFormatter(ZonedFormatter(timezone))
    usage.addHandler(handler)
