"""The application services the ADK tools call, bound once per process.

Tools reach PostgreSQL, the pipeline and the resolver only through these
services; the model never receives a repository, a session or a URL fetcher.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolServices:
    run_service: Any = None
    answer_service: Any = None
    structured_query_service: Any = None
    answer_router: Any = None
    request_resolver: Any = None
    current_tariff_service: Any = None
    tariff_history_service: Any = None
    # ADK-native runtime (plan Phase 3): the node the monitoring tools run, and
    # the read-only repositories the status tool summarises.
    monitoring_node: Any = None
    runs: Any = None
    reviews: Any = None


services = ToolServices()


def configure_run_service(service: Any) -> None:
    """Bind the application service without exposing repositories to the model."""
    services.run_service = service


def configure_services(
    run_service: Any,
    answer_service: Any,
    request_resolver: Any = None,
    current_tariff_service: Any = None,
    tariff_history_service: Any = None,
    structured_query_service: Any = None,
    answer_router: Any = None,
    *,
    monitoring_node: Any = None,
    runs: Any = None,
    reviews: Any = None,
) -> None:
    """Rebind every service; anything not passed is unbound."""
    configure_run_service(run_service)
    services.answer_service = answer_service
    services.structured_query_service = structured_query_service
    services.answer_router = answer_router
    services.request_resolver = request_resolver
    services.current_tariff_service = current_tariff_service
    services.tariff_history_service = tariff_history_service
    services.monitoring_node = monitoring_node
    services.runs = runs
    services.reviews = reviews
