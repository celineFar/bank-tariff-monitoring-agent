from typing import Protocol
from uuid import UUID

from app.domain.models import ProductType, TariffSnapshot


class SnapshotRepository(Protocol):
    async def get_latest(self, product: ProductType) -> TariffSnapshot | None: ...
    async def save(self, snapshot: TariffSnapshot) -> UUID: ...


class ReviewRepository(Protocol):
    async def create(self, run_id: UUID, reason: str, evidence: dict) -> UUID: ...
    async def decide(
        self, review_id: UUID, decision: str, reviewer: str, comment: str | None
    ) -> None: ...
