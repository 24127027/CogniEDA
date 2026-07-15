"""Application-owned construction of durable execution-admission operations."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from schemas.enums import (
    ExecutionRunStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
)
from schemas.planner_operations import PlannerOperation
from schemas.provenance import ExecutionOutbox, ExecutionRun


def build_execution_admission_operations(
    *,
    session_id: str | None,
    task_id: UUID,
    hypothesis_id: UUID,
    executor_type: str,
    method_id: str,
    parameter_hash: str,
    prepared_payload: dict[str, Any],
) -> tuple[ExecutionRun, list[PlannerOperation]]:
    """Build the immutable attempt/outbox pair for the application commit boundary."""

    dispatch_key = str(uuid4())
    execution_run = ExecutionRun(
        task_id=task_id,
        hypothesis_id=hypothesis_id,
        executor_type=executor_type,
        method_id=method_id,
        parameter_hash=parameter_hash,
        status=ExecutionRunStatus.ADMITTED,
        dispatch_idempotency_key=dispatch_key,
    )
    outbox = ExecutionOutbox(
        execution_run_id=execution_run.execution_run_id,
        dispatch_idempotency_key=dispatch_key,
        executor_type=executor_type,
        method_id=method_id,
        parameter_hash=parameter_hash,
        prepared_payload=prepared_payload,
    )
    return execution_run, [
        PlannerOperation(
            session_id=session_id,
            operation_type=PlannerOperationType.CREATE_EXECUTION_RUN,
            payload=execution_run.model_dump(mode="json"),
            produced_by_node=PlannerNodeName.PREPARE_EXECUTION,
            approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
        ),
        PlannerOperation(
            session_id=session_id,
            operation_type=PlannerOperationType.CREATE_EXECUTION_OUTBOX,
            payload=outbox.model_dump(mode="json"),
            produced_by_node=PlannerNodeName.PREPARE_EXECUTION,
            approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
        ),
    ]
