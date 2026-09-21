import logging
from datetime import UTC, datetime

from app.config.models import ObservabilitySettings
from app.services.logging_setup import ZonedFormatter, configure_application_logging


def test_zoned_formatter_emits_explicit_yerevan_offset() -> None:
    record = logging.makeLogRecord(
        {
            "name": "tariff.test",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "example",
            "args": (),
            "created": datetime(2026, 9, 21, 6, 0, tzinfo=UTC).timestamp(),
        }
    )
    assert (
        ZonedFormatter("Asia/Yerevan")
        .format(record)
        .startswith("2026-09-21T10:00:00.000+04:00")
    )


def test_file_archive_rotates_and_includes_uvicorn_logs(tmp_path) -> None:
    root = logging.getLogger()
    access = logging.getLogger("uvicorn.access")
    uvicorn = logging.getLogger("uvicorn")
    previous_root_handlers = root.handlers[:]
    previous_uvicorn_handlers = uvicorn.handlers[:]
    previous_access_handlers = access.handlers[:]
    previous_root_level = root.level
    previous_access_level = access.level
    log_file = tmp_path / "api.log"
    try:
        configure_application_logging(
            ObservabilitySettings(
                log_file=log_file,
                log_timezone="Asia/Yerevan",
                log_max_bytes=220,
                log_backup_count=2,
            ),
            include_uvicorn=True,
        )
        root.info("application marker")
        access.setLevel(logging.INFO)
        access.info("access marker")
        for index in range(8):
            root.info("archive rotation marker %s", index)
        assert log_file.exists()
        assert (tmp_path / "api.log.1").exists()
        assert "+04:00" in log_file.read_text()
        assert "archive rotation marker 7" in log_file.read_text()
    finally:
        for logger, previous_handlers in (
            (root, previous_root_handlers),
            (uvicorn, previous_uvicorn_handlers),
            (access, previous_access_handlers),
        ):
            for handler in logger.handlers[:]:
                if handler not in previous_handlers:
                    logger.removeHandler(handler)
                    handler.close()
        root.setLevel(previous_root_level)
        access.setLevel(previous_access_level)


def test_cli_logging_writes_file_without_console_noise(tmp_path, capsys) -> None:
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    try:
        root.handlers.clear()
        log_file = tmp_path / "cli.log"
        configure_application_logging(
            ObservabilitySettings(log_file=log_file), console_output=False
        )
        root.warning("answer.invalid_citation question_hash=123456789abc")
        assert "answer.invalid_citation" in log_file.read_text()
        assert capsys.readouterr().out == ""
    finally:
        for handler in root.handlers[:]:
            if handler not in previous_handlers:
                root.removeHandler(handler)
                handler.close()
        root.handlers = previous_handlers
        root.setLevel(previous_level)
