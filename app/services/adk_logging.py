from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from google.genai.errors import APIError

_ADK_EXCEPTION_LOGGERS = (
    "google.adk.workflow._node_runner",
    "google.adk.runners",
    "google_adk.google.adk.workflow._node_runner",
    "google_adk.google.adk.runners",
)
_HANDLED_MESSAGES = frozenset(
    {
        "Node execution failed with exception",
        "Root node %s failed.",
    }
)


class _HandledAdkExceptionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.msg not in _HANDLED_MESSAGES


class _ResourceExhaustionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.msg not in _HANDLED_MESSAGES or not record.exc_info:
            return True
        error = record.exc_info[1]
        return not isinstance(error, APIError) or error.status != "RESOURCE_EXHAUSTED"


@contextmanager
def suppress_resource_exhaustion_adk_logs() -> Iterator[None]:
    """Suppress ADK's duplicate traceback while the CLI handles Gemini quota errors."""
    log_filter = _ResourceExhaustionFilter()
    loggers = tuple(logging.getLogger(name) for name in _ADK_EXCEPTION_LOGGERS)
    for adk_logger in loggers:
        adk_logger.addFilter(log_filter)
    try:
        yield
    finally:
        for adk_logger in loggers:
            adk_logger.removeFilter(log_filter)


@contextmanager
def suppress_handled_adk_exception_logs() -> Iterator[None]:
    """Hide ADK tracebacks for exceptions handled by the application boundary."""
    log_filter = _HandledAdkExceptionFilter()
    loggers = tuple(logging.getLogger(name) for name in _ADK_EXCEPTION_LOGGERS)
    for adk_logger in loggers:
        adk_logger.addFilter(log_filter)
    try:
        yield
    finally:
        for adk_logger in loggers:
            adk_logger.removeFilter(log_filter)
