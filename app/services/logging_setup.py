from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from zoneinfo import ZoneInfo

from app.config.models import ObservabilitySettings


class ZonedFormatter(logging.Formatter):
    def __init__(self, timezone: str) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s: %(message)s")
        self._timezone = ZoneInfo(timezone)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return datetime.fromtimestamp(record.created, self._timezone).isoformat(
            timespec="milliseconds"
        )


def configure_application_logging(
    settings: ObservabilitySettings, *, include_uvicorn: bool = False
) -> None:
    """Keep console logs and archive bounded, timezone-aware files when configured."""
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    logging.captureWarnings(True)
    formatter = ZonedFormatter(settings.log_timezone)
    if not root.handlers:
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
