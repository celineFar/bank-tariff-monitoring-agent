from typing import Literal


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


def start_tariff_monitoring(
    product: Literal["consumer_loan", "mortgage"],
) -> dict[str, str]:
    """Hand a canonical product to the deterministic monitoring pipeline."""
    return {
        "status": "SCAFFOLDED",
        "product": product,
        "next_step": "Invoke the application TariffPipeline implementation.",
    }
