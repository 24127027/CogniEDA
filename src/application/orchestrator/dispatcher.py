"""Independently invokable consumer for admitted execution outbox records."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session

from application.orchestrator.execution_contracts import PreparedExecution
from application.orchestrator.receiver import submit_execution_result
from application.orchestrator.scientific_processing import _method_parameter_hash
from application.orchestrator.transition_service import ExecutionAttemptTransitionService
from db.models import (
    DataProfileRecord,
    ExecutionOutboxRecord,
    ExecutionRunRecord,
    HypothesisRecord,
)
from repositories.execution_outbox_repository import ExecutionOutboxRepository

logger = logging.getLogger(__name__)


async def dispatch_pending_attempts(
    session: Session,
    executor_dispatcher: Any,
    worker_id: str,
    max_attempts: int = 10,
    lease_duration_seconds: int = 300,
    context_factory: Callable[[], Any] | None = None,
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

        result = None
        executor_status = "failed"
        error_message: str | None = None
        try:
            from agents.executor.types import ExecutorContext

            prepared = _reconstruct_prepared_execution(session, record, run)
            if not transition_service.mark_running(
                run.execution_run_id, worker_id, run.lease_epoch
            ):
                continue
            context = context_factory() if context_factory is not None else ExecutorContext()
            result = await executor_dispatcher.dispatch(prepared, context)
            executor_status = result.status
            error_message = result.error_message
        except Exception as exc:
            result = None
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


def _reconstruct_prepared_execution(
    session: Session,
    record: ExecutionOutboxRecord,
    run: ExecutionRunRecord,
) -> PreparedExecution:
    """Bind the immutable payload to durable attempt and FCO identities."""
    prepared = PreparedExecution.model_validate(record.prepared_payload)
    hypothesis = session.get(HypothesisRecord, run.hypothesis_id)
    if hypothesis is None or run.task_id is None or hypothesis.task_id != run.task_id:
        raise ValueError("ExecutionRun has no matching durable Task and Hypothesis identity.")
    profile = session.get(DataProfileRecord, hypothesis.profile_id)
    if profile is None or prepared.dataset_path != profile.dataset_path:
        raise ValueError("Prepared execution does not match its durable DataProfile.")
    if (
        prepared.hypothesis.statement != hypothesis.statement
        or prepared.hypothesis.variables != hypothesis.variables
        or prepared.hypothesis.scope != hypothesis.scope
        or prepared.hypothesis.validation_method != hypothesis.validation_method
        or prepared.hypothesis.evidence_expectation != hypothesis.evidence_expectation
    ):
        raise ValueError("Prepared execution does not match its durable Hypothesis.")
    parameter_hash = _method_parameter_hash(prepared.specification.method_parameters)
    if (
        record.execution_run_id != run.execution_run_id
        or record.dispatch_idempotency_key != run.dispatch_idempotency_key
        or record.executor_type != run.executor_type
        or record.method_id != run.method_id
        or record.parameter_hash != run.parameter_hash
        or prepared.specification.executor_id != run.executor_type
        or prepared.specification.validation_method != run.method_id
        or parameter_hash != run.parameter_hash
    ):
        raise ValueError("Prepared execution disagrees with immutable attempt identity.")

    return prepared.model_copy(
        update={
            "task_ref": str(run.task_id),
            "hypothesis_ref": str(hypothesis.hypothesis_id),
            "data_profile_ref": str(hypothesis.profile_id),
            "execution_run_id": run.execution_run_id,
            "dispatch_idempotency_key": run.dispatch_idempotency_key,
            "lease_epoch": run.lease_epoch,
        }
    )
