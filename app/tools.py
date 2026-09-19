from typing import Literal

from app.domain.models import ProductType
from app.domain.monitoring import RunCommand, RunTrigger
from app.services.run_service import RunServicePort

_run_service: RunServicePort | None = None


def configure_run_service(service: RunServicePort | None) -> None:
    """Bind the application service without exposing repositories to the model."""
    global _run_service
    _run_service = service


def resolve_product(query: str) -> dict[str, object]:
    """Resolve a request to one supported Ameria loan family."""
    query_lower = query.casefold()
    mortgage = any(term in query_lower for term in ("mortgage", "հիփոթեք", "բնակարան"))
    consumer = any(
        term in query_lower for term in ("consumer", "սպառողական", "personal loan")
    )
    if mortgage == consumer:
        return {"status": "AMBIGUOUS", "product": None}
    return {
        "status": "RESOLVED",
        "product": "mortgage" if mortgage else "consumer_loan",
    }


async def start_tariff_monitoring(
    product: Literal["consumer_loan", "mortgage"],
) -> dict[str, object]:
    """Hand a canonical product to the deterministic monitoring pipeline."""
    if _run_service is None:
        return {
            "status": "UNAVAILABLE",
            "product": product,
            "reason_code": "run.service_unavailable",
        }
    result = await _run_service.submit(
        RunCommand(product=ProductType(product), trigger=RunTrigger.ADK)
    )
    return {
        "status": result.run.status.value,
        "run_id": str(result.run.id),
        "product": result.run.command.product.value,
        "created": result.created,
        "reused_reason": (
            result.reused_reason.value if result.reused_reason is not None else None
        ),
    }
