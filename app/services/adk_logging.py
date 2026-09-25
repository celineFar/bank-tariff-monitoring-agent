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


class _MessageFilter(logging.Filter):
    def __init__(self, messages: frozenset[str]) -> None:
        super().__init__()
        self._messages = messages

    def filter(self, record: logging.LogRecord) -> bool:
        return record.msg not in self._messages


# Known-cosmetic messages of the in-process monitoring runtime (plan §5, E14):
# the node's events are authored by "monitoring", which is not an agent, and
# cancelling a turn unwinds OpenTelemetry contexts out of order.
_COSMETIC_MESSAGES = {
    "google_adk.google.adk.agents._agent_router": frozenset(
        {"Event from an unknown agent: %s, event id: %s"}
    ),
    "opentelemetry.context": frozenset({"Failed to detach context"}),
}


def install_runtime_log_filters() -> None:
    """Drop the two cosmetic runtime messages; safe to call more than once."""
    for name, messages in _COSMETIC_MESSAGES.items():
        target = logging.getLogger(name)
        if not any(
            isinstance(item, _MessageFilter) and item._messages == messages
            for item in target.filters
        ):
            target.addFilter(_MessageFilter(messages))


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
