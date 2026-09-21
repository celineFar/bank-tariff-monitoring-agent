from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.api.routes import router
from app.domain.catalog import (
    CatalogLanguage,
    LocalizedCatalogTerms,
    ProductFamilyCatalogEntry,
    SeedCatalog,
    SeedCatalogEntry,
)
from app.domain.models import OfferingId, ProductType
from app.domain.monitoring import (
    ClaimedRun,
    MonitoringRun,
    OfferingExecution,
    OfferingRunStatus,
    PublicationResult,
    RunCommand,
    RunFailureCode,
    RunStatus,
    RunSubmissionResult,
    SnapshotAttempt,
    SnapshotStatus,
)
from app.domain.monitoring_workflow import MonitoringWorkflowResult
from app.domain.pipeline import IndexingRefreshResult, SourceManifest
from app.services.monitoring_pipeline import OfferingPipelineError, TariffPipeline
from app.services.run_service import RunService
from app.worker import MonitoringWorker

NOW = datetime(2026, 9, 19, tzinfo=UTC)


class _Runs:
    def __init__(self) -> None:
        self.runs: dict[UUID, MonitoringRun] = {}
        self.idempotency: dict[str, UUID] = {}
        self.executions: dict[UUID, OfferingExecution] = {}

    async def submit(
        self, command: RunCommand, *, idempotency_key: str | None = None
    ) -> RunSubmissionResult:
        if idempotency_key in self.idempotency:
            run = self.runs[self.idempotency[idempotency_key]]
            return RunSubmissionResult(
                run=run,
                created=False,
                reused_reason=RunFailureCode.IDEMPOTENCY_REUSED,
            )
        active = next(
            (
                item
                for item in self.runs.values()
                if item.command.product is command.product
                and item.status in {RunStatus.QUEUED, RunStatus.RUNNING}
            ),
            None,
        )
        if active is not None:
            return RunSubmissionResult(
                run=active,
                created=False,
                reused_reason=RunFailureCode.ACTIVE_RUN_EXISTS,
            )
        run = MonitoringRun(
            id=uuid4(), command=command, status=RunStatus.QUEUED, queued_at=NOW
        )
        self.runs[run.id] = run
        if idempotency_key:
            self.idempotency[idempotency_key] = run.id
        return RunSubmissionResult(run=run, created=True)

    async def get(self, run_id: UUID) -> MonitoringRun | None:
        return self.runs.get(run_id)

    async def claim_next(self, worker_id: str) -> ClaimedRun | None:
        run = next(
            (item for item in self.runs.values() if item.status is RunStatus.QUEUED),
            None,
        )
        if run is None:
            return None
        running = run.model_copy(
            update={"status": RunStatus.RUNNING, "started_at": NOW}
        )
        self.runs[run.id] = running
        return ClaimedRun(run=running, worker_id=worker_id)

    async def recover_abandoned(self, *, before: datetime) -> int:
        return 0

    async def finish(
        self,
        run_id: UUID,
        status: RunStatus,
        *,
        failure_code: str | None = None,
        failure_detail: str | None = None,
        summary: dict[str, object] | None = None,
    ) -> MonitoringRun:
        run = self.runs[run_id].model_copy(
            update={
                "status": status,
                "completed_at": NOW,
                "failure_code": failure_code,
                "failure_detail": failure_detail,
                "summary": summary or {},
            }
        )
        self.runs[run_id] = run
        return run

    async def create_offering_execution(
        self, run_id: UUID, product: ProductType, offering_id: OfferingId
    ) -> OfferingExecution:
        execution = OfferingExecution(
            id=uuid4(),
            run_id=run_id,
            product=product,
            offering_id=offering_id,
            status=OfferingRunStatus.PENDING,
        )
        self.executions[execution.id] = execution
        return execution

    async def start_offering_execution(
        self, offering_execution_id: UUID, *, stage: str = "starting"
    ) -> OfferingExecution:
        execution = self.executions[offering_execution_id].model_copy(
            update={
                "status": OfferingRunStatus.RUNNING,
                "current_stage": stage,
                "started_at": NOW,
            }
        )
        self.executions[execution.id] = execution
        return execution

    async def fail_offering_execution(
        self,
        offering_execution_id: UUID,
        *,
        stage: str,
        failure_code: str,
        failure_detail: str | None = None,
        audit_payload: dict[str, object] | None = None,
    ) -> OfferingExecution:
        execution = self.executions[offering_execution_id].model_copy(
            update={
                "status": OfferingRunStatus.FAILED,
                "current_stage": stage,
                "completed_at": NOW,
                "failure_code": failure_code,
                "failure_detail": failure_detail,
            }
        )
        self.executions[execution.id] = execution
        return execution


class _Indexing:
    def __init__(self, failing: set[OfferingId] | None = None) -> None:
        self.failing = failing or set()
        self.published: list[OfferingId] = []
        self.false_changes = 0

    async def refresh(self, offering, run_id: UUID, execution_id: UUID):
        if offering.offering_id in self.failing:
            raise OfferingPipelineError(
                "acquisition", "offering.acquisition_failed", TimeoutError()
            )
        self.published.append(offering.offering_id)
        snapshot = SnapshotAttempt(
            id=uuid4(),
            run_id=run_id,
            offering_execution_id=execution_id,
            product=offering.product,
            offering_id=offering.offering_id,
            status=SnapshotStatus.ACCEPTED,
            normalized_tariff={"interest_rate": "13.5%"},
            canonical_sha256="a" * 64,
            created_at=NOW,
            accepted_at=NOW,
        )
        return IndexingRefreshResult(
            manifest=SourceManifest(
                items=(),
                source_count=0,
                selected_count=0,
                document_count=1,
                chunk_count=1,
            ),
            snapshot=snapshot,
            publication=PublicationResult(
                snapshot_id=snapshot.id,
                document_results=(),
                offering_status=OfferingRunStatus.SUCCEEDED,
            ),
        )


def _catalog(*offerings: OfferingId) -> SeedCatalog:
    return SeedCatalog(
        families=tuple(
            ProductFamilyCatalogEntry(
                product=product,
                localized_names={
                    CatalogLanguage.ENGLISH: LocalizedCatalogTerms(
                        name=f"{product.value}-family"
                    ),
                    CatalogLanguage.ARMENIAN: LocalizedCatalogTerms(
                        name=f"hy-{product.value}-family"
                    ),
                },
            )
            for product in (ProductType.CONSUMER_LOAN, ProductType.MORTGAGE)
        ),
        offerings=tuple(
            SeedCatalogEntry(
                product=offering.product,
                offering_id=offering,
                display_name=offering.value,
                seed_url=f"https://ameriabank.am/{offering.value}",
                localized_names={
                    CatalogLanguage.ENGLISH: LocalizedCatalogTerms(name=offering.value),
                    CatalogLanguage.ARMENIAN: LocalizedCatalogTerms(
                        name=f"hy-{offering.value}"
                    ),
                },
            )
            for offering in offerings
        ),
    )


@pytest.mark.asyncio
async def test_consumer_standard_api_to_worker_publication_vertical_slice() -> None:
    runs = _Runs()
    indexing = _Indexing()
    pipeline = TariffPipeline(
        catalog=_catalog(OfferingId.CONSUMER_STANDARD),
        indexing=indexing,
        runs=runs,
    )

    class _Workflow:
        async def start(self, run):
            completed = await pipeline.execute(run)
            return MonitoringWorkflowResult(
                run_id=completed.id,
                status=completed.status,
                review_ids=(),
                summary=completed.summary,
            )

    worker = MonitoringWorker(
        runs=runs,
        workflow=_Workflow(),
        worker_id="test-worker",
    )
    app = FastAPI()
    app.state.run_service = RunService(runs)
    app.include_router(router)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        submitted = await client.post(
            "/api/v1/runs",
            json={"product": "consumer_loan", "offering_id": "consumer_standard"},
            headers={"Idempotency-Key": "slice-1"},
        )
        assert submitted.status_code == 202
        assert submitted.json()["run"]["status"] == "queued"
        assert await worker.process_next() is True
        status = await client.get(f"/api/v1/runs/{submitted.json()['run']['id']}")
        repeated = await client.post(
            "/api/v1/runs",
            json={"product": "consumer_loan", "offering_id": "consumer_standard"},
            headers={"Idempotency-Key": "slice-1"},
        )

    assert status.json()["status"] == "succeeded"
    assert indexing.published == [OfferingId.CONSUMER_STANDARD]
    assert repeated.json()["created"] is False
    assert repeated.json()["run"]["id"] == submitted.json()["run"]["id"]
    assert indexing.false_changes == 0


@pytest.mark.asyncio
async def test_failed_sibling_yields_partial_success_without_rollback() -> None:
    runs = _Runs()
    indexing = _Indexing(failing={OfferingId.OVERDRAFT})
    submitted = await runs.submit(
        RunCommand(product=ProductType.CONSUMER_LOAN, trigger="api")
    )
    claimed = await runs.claim_next("test-worker")
    assert claimed is not None
    pipeline = TariffPipeline(
        catalog=_catalog(OfferingId.CONSUMER_STANDARD, OfferingId.OVERDRAFT),
        indexing=indexing,
        runs=runs,
    )

    result = await pipeline.execute(claimed.run)

    assert result.status is RunStatus.PARTIAL_SUCCESS
    assert indexing.published == [OfferingId.CONSUMER_STANDARD]
    assert result.id == submitted.run.id
