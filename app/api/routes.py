from datetime import datetime
from hmac import compare_digest
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

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
from app.domain.structured_tariffs import TariffQueryResult
from app.domain.tariff_queries import (
    CurrentTariffResult,
    TariffHistoryResult,
)
from app.repositories.contracts import ReviewRepository
from app.services.answer_read_model import TariffAnswerRouter
from app.services.intent_resolution import RequestResolver
from app.services.rag_answer import RagAnswerService
from app.services.review_resolution import ReviewResolutionService
from app.services.run_service import RunServicePort, run_covers_command
from app.services.structured_query_planning import issue_resolution_plan
from app.services.structured_tariff_query import StructuredTariffQueryService
from app.services.tariff_queries import (
    CurrentTariffService,
    TariffHistoryService,
)

router = APIRouter(prefix="/api/v1")


def _failure(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


class StructuredQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=1000)


class RunRequest(BaseModel):
    product: ProductType
    offering_id: OfferingId | None = None


class RunSubmissionResponse(RunSubmissionResult):
    status_url: str
    # Read-only diagnostics; review decisions are taken in the chat CLI.
    reviews_url: str
    request_satisfied: bool


@router.get("/healthz", tags=["operations"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


def get_run_service(request: Request) -> RunServicePort:
    return request.app.state.run_service


def get_answer_service(request: Request) -> RagAnswerService:
    return request.app.state.answer_service


def get_answer_router(request: Request) -> TariffAnswerRouter:
    return request.app.state.answer_router


def get_structured_query_service(request: Request) -> StructuredTariffQueryService:
    return request.app.state.structured_query_service


def get_request_resolver(request: Request) -> RequestResolver:
    return request.app.state.request_resolver


def get_current_tariff_service(request: Request) -> CurrentTariffService:
    return request.app.state.current_tariff_service


def get_tariff_history_service(request: Request) -> TariffHistoryService:
    return request.app.state.tariff_history_service


def get_review_repository(request: Request) -> ReviewRepository:
    return request.app.state.review_repository


@router.post(
    "/runs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RunSubmissionResponse,
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
) -> RunSubmissionResponse:
    try:
        command = RunCommand(
            product=request.product,
            offering_id=request.offering_id,
            trigger=RunTrigger.API,
        )
    except ValueError as exc:
        raise _failure(422, "request.invalid_scope", str(exc)) from exc
    try:
        result = await service.submit(command, idempotency_key=idempotency_key)
    except ValueError as exc:
        raise _failure(422, "request.invalid", str(exc)) from exc
    except Exception as exc:
        raise _failure(
            503,
            "run.persistence_failed",
            "The monitoring run could not be persisted.",
        ) from exc
    if not run_covers_command(result.run, command):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "run.active_scope_conflict",
                "message": "An active run for a different offering blocks this request.",
                "blocking_run_id": str(result.run.id),
                "blocking_offering_id": (
                    result.run.command.offering_id.value
                    if result.run.command.offering_id is not None
                    else None
                ),
            },
        )
    return RunSubmissionResponse(
        run=result.run,
        created=result.created,
        reused_reason=result.reused_reason,
        status_url=f"/api/v1/runs/{result.run.id}",
        reviews_url=f"/api/v1/reviews?run_id={result.run.id}",
        request_satisfied=True,
    )


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
    router_service: Annotated[TariffAnswerRouter, Depends(get_answer_router)],
) -> AnswerResult:
    """Answer through whichever read model the cutover switch selects."""
    try:
        return await router_service.answer_question(command)
    except Exception as exc:
        raise _failure(
            503,
            "answer.persistence_failed",
            "Tariff evidence is temporarily unavailable.",
        ) from exc


@router.post("/tariffs/query", response_model=TariffQueryResult, tags=["tariffs"])
async def query_structured_tariffs(
    command: StructuredQueryRequest,
    service: Annotated[
        StructuredTariffQueryService, Depends(get_structured_query_service)
    ],
    resolver: Annotated[RequestResolver, Depends(get_request_resolver)],
) -> TariffQueryResult:
    """Resolve and answer one bounded query without triggering acquisition."""
    try:
        resolution = (await resolver.resolve_turn(command.query)).resolution
        plan = issue_resolution_plan(
            command.query,
            resolution,
            session_id=f"api-{uuid4()}",
            turn_id=str(uuid4()),
        )
    except ValueError as exc:
        raise _failure(422, "query.unresolved_scope", str(exc)) from exc
    try:
        return await service.answer(plan, command.query)
    except ValueError as exc:
        raise _failure(422, "query.invalid_scope", str(exc)) from exc
    except Exception as exc:
        raise _failure(
            503,
            "query.persistence_failed",
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


@router.post("/reviews/abort-pending", tags=["reviews"])
async def abort_pending_reviews(
    request: Request,
    admin_token: Annotated[str | None, Header(alias="X-Review-Admin-Token")] = None,
) -> dict[str, object]:
    configured = request.app.state.settings.hitl.review_admin_token
    if configured is None or not configured.get_secret_value():
        raise _failure(
            503, "review.abort_not_configured", "Review abort is not configured"
        )
    if admin_token is None or not compare_digest(
        admin_token, configured.get_secret_value()
    ):
        raise _failure(403, "review.admin_required", "Admin token is required")
    service: ReviewResolutionService = request.app.state.review_resolution
    try:
        return await service.reject_all_pending(reviewer="api-admin")
    except Exception as exc:
        raise _failure(
            503, "review.abort_failed", "Review abort could not complete"
        ) from exc


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
