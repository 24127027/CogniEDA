"""Reconciliation for non-terminal attempts."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlmodel import Session

from application.orchestrator.finalizer import finalize_attempt
from application.orchestrator.transition_service import ExecutionAttemptTransitionService
from db.models import ExecutionInboxRecord, ExecutionRunRecord
from schemas.enums import ExecutionRunStatus

logger = logging.getLogger(__name__)


def reconcile_execution_attempts(session: Session) -> None:
    """Actionable reconciliation for pending runs."""
    transition_service = ExecutionAttemptTransitionService(session)

    # 1. Finalize attempts with pending inbox results
    pending_inboxes = session.exec(
        select(ExecutionInboxRecord).where(ExecutionInboxRecord.status == "pending")
    ).all()

    for inbox in pending_inboxes:
        try:
            finalize_attempt(session, inbox.execution_run_id)
        except Exception as e:
            logger.error(f"Error finalizing attempt {inbox.execution_run_id}: {e}")
            session.rollback()

    # 2. Reclaim expired leases
    now = datetime.now(UTC)
    expired_runs = session.exec(
        select(ExecutionRunRecord).where(
            ExecutionRunRecord.status.in_(
                [
                    ExecutionRunStatus.DISPATCH_CLAIMED,
                    ExecutionRunStatus.RUNNING,
                    ExecutionRunStatus.FINALIZING,
                ]
            )
        )
    ).all()

    for run in expired_runs:
        if run.status == ExecutionRunStatus.FINALIZING:
            if run.finalization_expires_at and run.finalization_expires_at < now:
                # A later finalizer may reclaim the expired claim through
                # finalize_attempt.
                pass
        elif run.lease_expires_at and run.lease_expires_at < now:
            transition_service.expire_or_release_attempt(
                execution_run_id=run.execution_run_id, expected_attempt_version=run.attempt_version
            )
