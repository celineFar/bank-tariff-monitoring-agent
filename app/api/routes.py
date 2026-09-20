from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.domain.intent import HistoryQuery, HistoryRequestKind
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    AnswerResult,
    MonitoringRun,
    QuestionCommand,
    RunCommand,
    RunSubmissionResult,
    RunTrigger,
)
from app.domain.tariff_queries import CurrentTariffResult, TariffHistoryResult
from app.services.rag_answer import RagAnswerService
from app.services.run_service import RunServicePort
from app.services.tariff_queries import CurrentTariffService, TariffHistoryService

router = APIRouter(prefix="/api/v1")


class RunRequest(BaseModel):
    product: ProductType
    offering_id: OfferingId | None = None


class ReviewDecision(BaseModel):
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=200)
    comment: str | None = Field(default=None, max_length=2000)


@router.get("/healthz", tags=["operations"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


def get_run_service(request: Request) -> RunServicePort:
    return request.app.state.run_service


def get_answer_service(request: Request) -> RagAnswerService:
    return request.app.state.answer_service


def get_current_tariff_service(request: Request) -> CurrentTariffService:
    return request.app.state.current_tariff_service


def get_tariff_history_service(request: Request) -> TariffHistoryService:
    return request.app.state.tariff_history_service


@router.post(
    "/runs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RunSubmissionResult,
    tags=["runs"],
)
async def create_run(
    request: RunRequest,
    service: Annotated[RunServicePort, Depends(get_run_service)],
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        max_length=200,
    ),
) -> RunSubmissionResult:
    try:
        command = RunCommand(
            product=request.product,
            offering_id=request.offering_id,
            trigger=RunTrigger.API,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await service.submit(command, idempotency_key=idempotency_key)


@router.get("/runs/{run_id}", response_model=MonitoringRun, tags=["runs"])
async def get_run(
    run_id: UUID,
    service: Annotated[RunServicePort, Depends(get_run_service)],
) -> MonitoringRun:
    run = await service.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/questions", response_model=AnswerResult, tags=["questions"])
async def answer_question(
    command: QuestionCommand,
    service: Annotated[RagAnswerService, Depends(get_answer_service)],
) -> AnswerResult:
    return await service.answer(command)


@router.get(
    "/tariffs/current",
    response_model=CurrentTariffResult,
    tags=["tariffs"],
)
async def get_current_tariffs(
    service: Annotated[CurrentTariffService, Depends(get_current_tariff_service)],
    product: ProductType | None = None,
    offering_id: OfferingId | None = None,
) -> CurrentTariffResult:
    try:
        return await service.get_current(product=product, offering_id=offering_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/tariffs/history",
    response_model=TariffHistoryResult,
    tags=["tariffs"],
)
async def get_tariff_history(
    service: Annotated[TariffHistoryService, Depends(get_tariff_history_service)],
    kind: HistoryRequestKind,
    product: ProductType | None = None,
    offering_id: OfferingId | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    limit: int = 20,
) -> TariffHistoryResult:
    try:
        return await service.query(
            HistoryQuery(
                kind=kind,
                product=product,
                offering_id=offering_id,
                start_at=start_at,
                end_at=end_at,
                limit=limit,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/reviews", status_code=501, tags=["reviews"])
async def list_reviews() -> None:
    raise HTTPException(status_code=501, detail="ReviewRepository is not implemented.")


@router.post("/reviews/{review_id}/decision", status_code=501, tags=["reviews"])
async def decide_review(review_id: UUID, decision: ReviewDecision) -> None:
    raise HTTPException(status_code=501, detail="ReviewRepository is not implemented.")
