from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1")


class RunRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)


class ReviewDecision(BaseModel):
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=200)
    comment: str | None = Field(default=None, max_length=2000)


@router.get("/healthz", tags=["operations"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/runs", status_code=status.HTTP_501_NOT_IMPLEMENTED, tags=["runs"])
async def create_run(request: RunRequest) -> None:
    raise HTTPException(status_code=501, detail="TariffPipeline is not implemented.")


@router.get("/runs/{run_id}", status_code=501, tags=["runs"])
async def get_run(run_id: UUID) -> None:
    raise HTTPException(status_code=501, detail="RunRepository is not implemented.")


@router.get("/reviews", status_code=501, tags=["reviews"])
async def list_reviews() -> None:
    raise HTTPException(status_code=501, detail="ReviewRepository is not implemented.")


@router.post("/reviews/{review_id}/decision", status_code=501, tags=["reviews"])
async def decide_review(review_id: UUID, decision: ReviewDecision) -> None:
    raise HTTPException(status_code=501, detail="ReviewRepository is not implemented.")
