"""Durable, immutable receipt of executor result envelopes."""

from __future__ import annotations

import json
from uuid import UUID

from pydantic import TypeAdapter
from sqlmodel import Session

from application.orchestrator.execution_contracts import ExecutionReceiptEnvelope
from application.orchestrator.execution_identity import result_payload_digest
from db.models import ExecutionInboxRecord


def submit_execution_result(
    session: Session,
    execution_run_id: UUID,
    dispatch_idempotency_key: str,
    lease_epoch: int,
    worker_id: str,
    method_id: str,
    executor_status: str,
    result: ExecutionReceiptEnvelope,
    error_msg: str | None = None,
) -> ExecutionInboxRecord | None:
    """Accept one fenced result, or retain an immutable conflict for audit.

    This is intentionally the only result-admission boundary. It neither
    finalizes scientific state nor mutates an already received payload.
    """

    if executor_status not in {"completed", "failed"}:
        raise ValueError("Executor status must be completed or failed.")
    payload = _canonical_result_payload(result, executor_status=executor_status)
    digest = result_payload_digest(payload)

    from application.orchestrator.transition_service import ExecutionAttemptTransitionService

    transition_service = ExecutionAttemptTransitionService(session)

    return transition_service.accept_authoritative_result(
        execution_run_id=execution_run_id,
        dispatch_idempotency_key=dispatch_idempotency_key,
        worker_id=worker_id,
        lease_epoch=lease_epoch,
        result_digest=digest,
        executor_status=executor_status,
        serialized_observations=payload,
        error_message=error_msg,
        method_id=method_id,
        producer_identity=worker_id,
    )


def _canonical_result_payload(
    result: ExecutionReceiptEnvelope,
    *,
    executor_status: str,
) -> dict[str, object]:
    validated = TypeAdapter(ExecutionReceiptEnvelope).validate_python(result)
    expected_status = "success" if executor_status == "completed" else "failed"
    if validated.status != expected_status:
        raise ValueError("Executor status must match the result envelope status.")
    payload = validated.model_dump(mode="json")
    return json.loads(json.dumps(payload, sort_keys=True, allow_nan=False, separators=(",", ":")))
