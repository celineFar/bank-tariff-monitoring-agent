from typing import Protocol

from app.domain.models import ProductType


class TariffPipeline(Protocol):
    async def run(
        self, product: ProductType, trigger: str, query: str | None
    ) -> str: ...
