"""Independently invokable consumer for admitted execution outbox records."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session

from agents.planner.types import PreparedExecution
from application.orchestrator.receiver import submit_execution_result
from application.orchestrator.transition_service import ExecutionAttemptTransitionService
from db.models import ExecutionOutboxRecord
from repositories.execution_outbox_repository import ExecutionOutboxRepository

logger = logging.getLogger(__name__)


async def dispatch_pending_attempts(
    session: Session,
    executor: Any,
    worker_id: str,
    max_attempts: int = 10,
    lease_duration_seconds: int = 300,
) -> int:
    """Claim and dispatch durable work without Planner state or object handles."""

    outbox_repo = ExecutionOutboxRepository(session)
    transition_service = ExecutionAttemptTransitionService(session)
    dispatched = 0

    for outbox in outbox_repo.list(status="pending")[:max_attempts]:
        now = datetime.now(UTC)
        run = transition_service.claim_dispatch(
            execution_run_id=outbox.execution_run_id,
            worker_id=worker_id,
            expires_at=now + timedelta(seconds=lease_duration_seconds),
        )
        if run is None:
            continue

        record = session.get(ExecutionOutboxRecord, outbox.outbox_id)
        if record is None or record.status != "dispatching":
            continue

        prepared = PreparedExecution.model_validate(record.prepared_payload).model_copy(
            update={
                "execution_run_id": run.execution_run_id,
                "dispatch_idempotency_key": run.dispatch_idempotency_key,
                "lease_epoch": run.lease_epoch,
            }
        )

        transition_service.mark_running(run.execution_run_id, worker_id, run.lease_epoch)

        result = None
        executor_status = "failed"
        error_message: str | None = None
        try:
            result = executor.execute(prepared)
            executor_status = result.status
            error_message = result.error_message
        except Exception as exc:
            error_message = str(exc)

        envelope = submit_execution_result(
            session,
            execution_run_id=run.execution_run_id,
            dispatch_idempotency_key=record.dispatch_idempotency_key,
            lease_epoch=run.lease_epoch,
            worker_id=worker_id,
            method_id=record.method_id,
            executor_status=executor_status,
            result=result,
            error_msg=error_message,
        )
        if envelope is not None:
            dispatched += 1

    return dispatched
