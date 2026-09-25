"""Narrow ADK tools over the application services.

- `resolution`: `resolve_request`, the only tool that decides scope and issues
  the per-turn read and spend grants (plan §6.6).
- `reads`: business-data reads with no scope parameter.
- `monitoring`: the monitoring and review tools that run the monitoring node.
- `legacy`: the pre-redesign review protocol, removed in Phase 4.
"""

from app.tools._services import (
    configure_run_service,
    configure_services,
    services,
)
from app.tools.legacy import (
    _awaiting_cli_monitoring_result,
    _native_input,
    _switch_chat_run,
    answer_tariff_question,
    get_next_monitoring_review,
    start_tariff_monitoring,
    submit_monitoring_review_input,
    wait_for_monitoring_run,
)
from app.tools.monitoring import (
    get_monitoring_status,
    review_pending_candidates,
    run_tariff_monitoring,
)
from app.tools.reads import (
    answer_tariff_query,
    get_current_tariffs,
    get_tariff_history,
)
from app.tools.resolution import resolve_request

__all__ = [
    "_awaiting_cli_monitoring_result",
    "_native_input",
    "_switch_chat_run",
    "answer_tariff_query",
    "answer_tariff_question",
    "configure_run_service",
    "configure_services",
    "get_current_tariffs",
    "get_monitoring_status",
    "get_next_monitoring_review",
    "get_tariff_history",
    "resolve_request",
    "review_pending_candidates",
    "run_tariff_monitoring",
    "services",
    "start_tariff_monitoring",
    "submit_monitoring_review_input",
    "wait_for_monitoring_run",
]
