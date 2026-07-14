"""Execution cancellation and retry logic."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlmodel import Session

from application.orchestrator.transition_service import (
    AlreadyCompletedError,
    AlreadyFinalizingError,
    ExecutionAttemptTransitionService,
)
from db.models import ExecutionRunRecord

logger = logging.getLogger(__name__)


def cancel_execution_attempt(session: Session, attempt_id: UUID) -> bool:
    """Safely cancel an execution run and its outbox via transition service."""
    run = session.get(ExecutionRunRecord, attempt_id)
    if not run:
        return False

    from schemas.enums import ExecutionRunStatus

    if run.status == ExecutionRunStatus.CANCELLED:
        return True
    if run.status == ExecutionRunStatus.FINALIZING:
        raise AlreadyFinalizingError("already_finalizing")
    if run.status == ExecutionRunStatus.COMPLETED:
        raise AlreadyCompletedError("already_completed")

    transition_service = ExecutionAttemptTransitionService(session)
    res = transition_service.cancel_attempt(
        execution_run_id=attempt_id, expected_attempt_version=run.attempt_version
    )
    if not res:
        # Check database to see if status was updated concurrently
        run_refreshed = session.get(ExecutionRunRecord, attempt_id)
        if run_refreshed:
            if run_refreshed.status == ExecutionRunStatus.CANCELLED:
                return True
            if run_refreshed.status == ExecutionRunStatus.FINALIZING:
                raise AlreadyFinalizingError("already_finalizing")
            elif run_refreshed.status == ExecutionRunStatus.COMPLETED:
                raise AlreadyCompletedError("already_completed")
    return res


def authorize_retry(
    session: Session,
    attempt_id: UUID,
    retry_reason: str = "manual_retry",
    authorization_metadata: dict[str, Any] | None = None,
) -> UUID | None:
    """Authorize retry of an attempt if it failed or was cancelled."""
    transition_service = ExecutionAttemptTransitionService(session)
    new_run = transition_service.authorize_new_attempt(
        old_execution_run_id=attempt_id,
        retry_reason=retry_reason,
        authorization_metadata=authorization_metadata or {},
    )
    return new_run.execution_run_id if new_run else None
