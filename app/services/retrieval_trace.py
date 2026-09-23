"""Step-by-step trace of one structured retrieval, on its own logger.

Every stage of an answer writes one line to the `tariff.retrieval` logger,
correlated by a per-call trace ID, so the order of calls and what each stage
received and returned can be read back without a debugger. The logger is
separate from the application root, so it can be routed to its own file and
level without touching the rest of the logs.

Levels, set by `RETRIEVAL_TRACE_LEVEL`:

- `off`      nothing is emitted;
- `summary`  one line per answer (default);
- `steps`    one line per stage, identifiers, counts, and scores only;
- `verbose`  also the derived search terms and the rendered unit text.

`verbose` prints text projected from bank source documents, so it is opt-in and
intended for local debugging, not for a shared or production log.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from enum import StrEnum
from uuid import uuid4

RETRIEVAL_LOGGER_NAME = "tariff.retrieval"


def _correlation_id() -> str:
    """Prefer the active OTel trace id so a log line and a trace share one key.

    Falls back to a random id when nothing is recording, which keeps the trace
    readable with tracing disabled.
    """
    from app.services.telemetry import current_trace_id

    return current_trace_id() or uuid4().hex[:12]


logger = logging.getLogger(RETRIEVAL_LOGGER_NAME)


class RetrievalTraceLevel(StrEnum):
    OFF = "off"
    SUMMARY = "summary"
    STEPS = "steps"
    VERBOSE = "verbose"


_ORDER = {
    RetrievalTraceLevel.OFF: 0,
    RetrievalTraceLevel.SUMMARY: 1,
    RetrievalTraceLevel.STEPS: 2,
    RetrievalTraceLevel.VERBOSE: 3,
}

_level = RetrievalTraceLevel.SUMMARY
_trace_id: ContextVar[str | None] = ContextVar("retrieval_trace_id", default=None)
_outcome: ContextVar[dict[str, object] | None] = ContextVar(
    "retrieval_trace_outcome", default=None
)
_step: ContextVar[int] = ContextVar("retrieval_trace_step", default=0)


def configure_retrieval_trace(level: RetrievalTraceLevel) -> None:
    """Set the detail level; the application does this once from settings."""
    global _level
    _level = level


def current_level() -> RetrievalTraceLevel:
    return _level


def _enabled(minimum: RetrievalTraceLevel) -> bool:
    return _ORDER[_level] >= _ORDER[minimum]


def _format(stage: str, fields: dict[str, object]) -> str:
    rendered = " ".join(f"{key}={value}" for key, value in fields.items())
    return f"trace={_trace_id.get()} step={_step.get()} stage={stage} {rendered}"


def record(stage: str, /, **fields: object) -> None:
    """Emit one stage line. Identifiers, counts, and scores only."""
    if _trace_id.get() is None or not _enabled(RetrievalTraceLevel.STEPS):
        return
    _step.set(_step.get() + 1)
    logger.info(_format(stage, fields))


def record_text(stage: str, /, **fields: object) -> None:
    """Emit a stage line that includes source-derived text. `verbose` only."""
    if _trace_id.get() is None or not _enabled(RetrievalTraceLevel.VERBOSE):
        return
    _step.set(_step.get() + 1)
    logger.info(_format(stage, fields))


@contextmanager
def retrieval_trace(**opening: object) -> Iterator[str | None]:
    """Correlate every stage of one answer and always close with a summary."""
    if not _enabled(RetrievalTraceLevel.SUMMARY):
        yield None
        return
    trace_id = _correlation_id()
    id_token = _trace_id.set(trace_id)
    step_token = _step.set(0)
    started = time.perf_counter()
    summary: dict[str, object] = {}
    try:
        record("begin", **opening)
        yield trace_id
    except Exception as exc:
        summary["outcome"] = "error"
        summary["error_type"] = type(exc).__name__
        raise
    finally:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "trace=%s steps=%s elapsed_ms=%s %s",
            trace_id,
            _step.get(),
            elapsed_ms,
            " ".join(
                f"{key}={value}"
                for key, value in {
                    **opening,
                    **(_outcome.get() or {}),
                    **summary,
                }.items()
            ),
        )
        _trace_id.reset(id_token)
        _step.reset(step_token)
        _outcome.set(None)


def set_outcome(**fields: object) -> None:
    """Attach fields to the closing summary line of the current trace."""
    if _trace_id.get() is None:
        return
    _outcome.set({**(_outcome.get() or {}), **fields})
