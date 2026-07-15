"""Durable, immutable receipt of executor result envelopes."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlmodel import Session

from application.orchestrator.execution_contracts import ExecutorResult
from db.models import ExecutionInboxRecord


def submit_execution_result(
    session: Session,
    execution_run_id: UUID,
    dispatch_idempotency_key: str,
    lease_epoch: int,
    worker_id: str,
    method_id: str,
    executor_status: str,
    result: Any,
    error_msg: str | None = None,
) -> ExecutionInboxRecord | None:
    """Accept one fenced result, or retain an immutable conflict for audit.

    This is intentionally the only result-admission boundary.  It neither
    finalizes scientific state nor mutates an already received payload.
    """

    if executor_status not in {"completed", "failed"}:
        raise ValueError("Executor status must be completed or failed.")
    payload = _canonical_result_payload(result, executor_status=executor_status)
    digest = _result_digest(payload)

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


def _canonical_result_payload(result: Any, *, executor_status: str) -> dict[str, Any]:
    if result is None:
        if executor_status == "failed":
            return {}
        raise ValueError("Completed executor results require an ExecutorResult payload.")
    if isinstance(result, ExecutorResult):
        validated = result
    elif isinstance(result, dict):
        validated = ExecutorResult.model_validate(result)
    else:
        raise ValueError("Execution results must be ExecutorResult or JSON-object payloads.")
    if validated.status != executor_status:
        raise ValueError("Executor status must match the result envelope status.")
    payload = validated.model_dump(mode="json")
    # The round-trip both rejects NaN/Infinity and strips Python-only values.
    return json.loads(json.dumps(payload, sort_keys=True, allow_nan=False, separators=(",", ":")))


def _result_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
