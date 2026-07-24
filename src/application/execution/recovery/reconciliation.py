"""Reconciliation for non-terminal attempts."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlmodel import Session

from application.execution.recovery.evidence_admission_recovery import finalize_attempt
from application.execution.transition_service import (
    AlreadyFinalizingError,
    ClaimLostError,
    ExecutionAttemptTransitionService,
)
from db.models import ExecutionInboxRecord, ExecutionRunRecord
from schemas.enums import ExecutionRunStatus

logger = logging.getLogger(__name__)


class ExecutionReconciliationError(RuntimeError):
    """Raised when durable reconciliation encounters an unexpected service failure."""


def reconcile_execution_attempts(session: Session) -> None:
    """Actionable reconciliation for pending runs."""
    transition_service = ExecutionAttemptTransitionService(session)

    # 1. Finalize attempts with pending inbox results
    pending_inboxes = session.exec(
        select(ExecutionInboxRecord).where(ExecutionInboxRecord.status == "pending")
    ).all()

    errors: list[str] = []
    for inbox in pending_inboxes:
        try:
            finalize_attempt(session, inbox.execution_run_id)
        except (AlreadyFinalizingError, ClaimLostError):
            session.rollback()
        except Exception as exc:
            session.rollback()
            errors.append(f"{inbox.execution_run_id}: {type(exc).__name__}: {exc}")

    # 2. Reclaim expired leases
    now = datetime.now(UTC)
    expired_runs = session.exec(
        select(ExecutionRunRecord).where(
            ExecutionRunRecord.status.in_(
                [
                    ExecutionRunStatus.DISPATCH_CLAIMED,
                    ExecutionRunStatus.RUNNING,
                    ExecutionRunStatus.EVIDENCE_ADMITTING,
                ]
            )
        )
    ).all()

    for run in expired_runs:
        if run.status == ExecutionRunStatus.EVIDENCE_ADMITTING:
            if run.finalization_expires_at and run.finalization_expires_at < now:
                # A later finalizer may reclaim the expired claim through finalize_attempt.
                pass
        elif run.lease_expires_at and run.lease_expires_at < now:
            transition_service.expire_or_release_attempt(
                execution_run_id=run.execution_run_id, expected_attempt_version=run.attempt_version
            )

    if errors:
        raise ExecutionReconciliationError(
            "Execution reconciliation failed for durable attempts: " + "; ".join(errors)
        )
