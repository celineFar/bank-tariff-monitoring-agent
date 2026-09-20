from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

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
from app.domain.review import ReviewStatus, ReviewTask
from app.domain.tariff_queries import CurrentTariffResult, TariffHistoryResult
from app.repositories.contracts import ReviewRepository
from app.services.rag_answer import RagAnswerService
from app.services.run_service import RunServicePort
from app.services.tariff_queries import CurrentTariffService, TariffHistoryService

router = APIRouter(prefix="/api/v1")


def _failure(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


class RunRequest(BaseModel):
    product: ProductType
    offering_id: OfferingId | None = None


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


def get_review_repository(request: Request) -> ReviewRepository:
    return request.app.state.review_repository


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
        raise _failure(422, "request.invalid_scope", str(exc)) from exc
    try:
        return await service.submit(command, idempotency_key=idempotency_key)
    except ValueError as exc:
        raise _failure(422, "request.invalid", str(exc)) from exc
    except Exception as exc:
        raise _failure(
            503,
            "run.persistence_failed",
            "The monitoring run could not be persisted.",
        ) from exc


@router.get("/runs/{run_id}", response_model=MonitoringRun, tags=["runs"])
async def get_run(
    run_id: UUID,
    service: Annotated[RunServicePort, Depends(get_run_service)],
) -> MonitoringRun:
    try:
        run = await service.get(run_id)
    except Exception as exc:
        raise _failure(
            503, "run.persistence_failed", "Run status is temporarily unavailable."
        ) from exc
    if run is None:
        raise _failure(404, "run.not_found", "Run not found")
    return run


@router.post("/questions", response_model=AnswerResult, tags=["questions"])
async def answer_question(
    command: QuestionCommand,
    service: Annotated[RagAnswerService, Depends(get_answer_service)],
) -> AnswerResult:
    try:
        return await service.answer(command)
    except Exception as exc:
        raise _failure(
            503,
            "answer.persistence_failed",
            "Tariff evidence is temporarily unavailable.",
        ) from exc


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
        raise _failure(422, "request.invalid_scope", str(exc)) from exc
    except Exception as exc:
        raise _failure(
            503,
            "snapshot.persistence_failed",
            "Current tariff data is temporarily unavailable.",
        ) from exc


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
        raise _failure(422, "request.invalid_history", str(exc)) from exc
    except Exception as exc:
        raise _failure(
            503,
            "history.persistence_failed",
            "Tariff history is temporarily unavailable.",
        ) from exc


@router.get("/reviews", response_model=list[ReviewTask], tags=["reviews"])
async def list_reviews(
    repository: Annotated[ReviewRepository, Depends(get_review_repository)],
    review_status: ReviewStatus | None = None,
    product: ProductType | None = None,
    offering_id: OfferingId | None = None,
    run_id: UUID | None = None,
    limit: int = 100,
) -> list[ReviewTask]:
    try:
        reviews = await repository.list(
            status=review_status,
            product=product,
            offering_id=offering_id,
            run_id=run_id,
            limit=limit,
        )
    except ValueError as exc:
        raise _failure(422, "request.invalid_review_filter", str(exc)) from exc
    except Exception as exc:
        raise _failure(
            503,
            "review.persistence_failed",
            "Review records are temporarily unavailable.",
        ) from exc
    return list(reviews)


@router.get("/reviews/{review_id}", response_model=ReviewTask, tags=["reviews"])
async def get_review(
    review_id: UUID,
    repository: Annotated[ReviewRepository, Depends(get_review_repository)],
) -> ReviewTask:
    try:
        review = await repository.get(review_id)
    except Exception as exc:
        raise _failure(
            503,
            "review.persistence_failed",
            "Review records are temporarily unavailable.",
        ) from exc
    if review is None:
        raise _failure(404, "review.not_found", "Review not found")
    return review
