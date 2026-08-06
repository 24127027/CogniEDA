"""Guarded, database-backed state transitions for durable execution attempts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from db.models import ExecutionOutboxRecord, ExecutionRunRecord, HypothesisRecord
from schemas.enums import ExecutionRunStatus


class ExecutionAttemptTransitionService:
    """The sole writer for mutable attempt and dispatch-intent state."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    def stage_admit_attempt(
        self,
        *,
        execution_run_id: UUID,
        task_id: UUID,
        hypothesis_id: UUID,
        executor_type: str,
        method_id: str,
        parameter_hash: str,
        dispatch_idempotency_key: str,
        prepared_payload: dict[str, Any],
        previous_attempt_id: UUID | None = None,
        retry_reason: str | None = None,
        retry_authorization_metadata: dict[str, Any] | None = None,
    ) -> ExecutionRunRecord:
        """Stage exactly one admitted v1 attempt and its paired pending outbox."""

        if not dispatch_idempotency_key:
            raise ValueError("An admitted attempt requires a dispatch idempotency key.")
        run = ExecutionRunRecord(
            execution_run_id=execution_run_id,
            task_id=task_id,
            hypothesis_id=hypothesis_id,
            executor_type=executor_type,
            method_id=method_id,
            parameter_hash=parameter_hash,
            status=ExecutionRunStatus.ADMITTED,
            dispatch_idempotency_key=dispatch_idempotency_key,
            attempt_version=1,
            previous_attempt_id=previous_attempt_id,
            retry_reason=retry_reason,
            retry_authorization_metadata=retry_authorization_metadata,
        )
        outbox = ExecutionOutboxRecord(
            execution_run_id=execution_run_id,
            dispatch_idempotency_key=dispatch_idempotency_key,
            executor_type=executor_type,
            method_id=method_id,
            parameter_hash=parameter_hash,
            prepared_payload=prepared_payload,
            status="pending",
        )
        self._session.add(run)
        self._session.flush()
        self._session.add(outbox)
        return run

    def claim_dispatch(
        self,
        execution_run_id: UUID,
        *,
        worker_id: str,
        expires_at: datetime,
    ) -> ExecutionRunRecord | None:
        """Lease an admitted attempt, fencing any expired prior worker."""

        now = self._now()
        claimed = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(
                or_(
                    ExecutionRunRecord.status == ExecutionRunStatus.ADMITTED,
                    (
                        ExecutionRunRecord.status.in_(
                            [
                                ExecutionRunStatus.DISPATCH_CLAIMED,
                                ExecutionRunStatus.RUNNING,
                            ]
                        )
                        & (ExecutionRunRecord.lease_expires_at < now)
                    ),
                )
            )
            .values(
                worker_id=worker_id,
                lease_epoch=ExecutionRunRecord.lease_epoch + 1,
                lease_acquired_at=now,
                lease_expires_at=expires_at,
                status=ExecutionRunStatus.DISPATCH_CLAIMED,
                attempt_version=ExecutionRunRecord.attempt_version + 1,
            )
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount != 1:
            self._session.rollback()
            return None
        consumed = self._session.execute(
            update(ExecutionOutboxRecord)
            .where(ExecutionOutboxRecord.execution_run_id == execution_run_id)
            .where(ExecutionOutboxRecord.status.in_(["pending", "dispatching"]))
            .values(status="dispatching")
        )
        if consumed.rowcount != 1:
            self._session.rollback()
            return None
        self._session.commit()
        return self._session.get(ExecutionRunRecord, execution_run_id)

    def renew_dispatch_lease(
        self,
        execution_run_id: UUID,
        *,
        worker_id: str,
        lease_epoch: int,
        expires_at: datetime,
    ) -> bool:
        updated = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(ExecutionRunRecord.worker_id == worker_id)
            .where(ExecutionRunRecord.lease_epoch == lease_epoch)
            .where(ExecutionRunRecord.lease_expires_at > self._now())
            .where(
                ExecutionRunRecord.status.in_(
                    [ExecutionRunStatus.DISPATCH_CLAIMED, ExecutionRunStatus.RUNNING]
                )
            )
            .values(
                lease_expires_at=expires_at,
                attempt_version=ExecutionRunRecord.attempt_version + 1,
            )
            .execution_options(synchronize_session=False)
        )
        if updated.rowcount != 1:
            self._session.rollback()
            return False
        self._session.commit()
        return True

    def mark_running(self, execution_run_id: UUID, *, worker_id: str, lease_epoch: int) -> bool:
        updated = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(ExecutionRunRecord.worker_id == worker_id)
            .where(ExecutionRunRecord.lease_epoch == lease_epoch)
            .where(ExecutionRunRecord.status == ExecutionRunStatus.DISPATCH_CLAIMED)
            .values(
                status=ExecutionRunStatus.RUNNING,
                attempt_version=ExecutionRunRecord.attempt_version + 1,
            )
            .execution_options(synchronize_session=False)
        )
        if updated.rowcount != 1:
            self._session.rollback()
            return False
        self._session.commit()
        return True

    def release_expired_dispatch(self, execution_run_id: UUID, *, attempt_version: int) -> bool:
        """Return an expired lease to admitted state without losing its outbox intent."""

        updated = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(ExecutionRunRecord.attempt_version == attempt_version)
            .where(
                ExecutionRunRecord.status.in_(
                    [ExecutionRunStatus.DISPATCH_CLAIMED, ExecutionRunStatus.RUNNING]
                )
            )
            .where(ExecutionRunRecord.lease_expires_at < self._now())
            .values(
                status=ExecutionRunStatus.ADMITTED,
                worker_id=None,
                lease_acquired_at=None,
                lease_expires_at=None,
                attempt_version=ExecutionRunRecord.attempt_version + 1,
            )
            .execution_options(synchronize_session=False)
        )
        if updated.rowcount != 1:
            self._session.rollback()
            return False
        self._session.execute(
            update(ExecutionOutboxRecord)
            .where(ExecutionOutboxRecord.execution_run_id == execution_run_id)
            .where(ExecutionOutboxRecord.status == "dispatching")
            .values(status="pending")
        )
        self._session.commit()
        return True

    def cancel_attempt(self, execution_run_id: UUID, *, attempt_version: int) -> bool:
        updated = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(ExecutionRunRecord.attempt_version == attempt_version)
            .where(
                ExecutionRunRecord.status.in_(
                    [
                        ExecutionRunStatus.ADMITTED,
                        ExecutionRunStatus.DISPATCH_CLAIMED,
                        ExecutionRunStatus.RUNNING,
                    ]
                )
            )
            .values(
                status=ExecutionRunStatus.CANCELLED,
                attempt_version=ExecutionRunRecord.attempt_version + 1,
            )
            .execution_options(synchronize_session=False)
        )
        if updated.rowcount != 1:
            self._session.rollback()
            return False
        self._session.execute(
            update(ExecutionOutboxRecord)
            .where(ExecutionOutboxRecord.execution_run_id == execution_run_id)
            .where(ExecutionOutboxRecord.status.in_(["pending", "dispatching"]))
            .values(status="cancelled")
        )
        self._session.commit()
        return True

    def authorize_retry(
        self,
        execution_run_id: UUID,
        *,
        retry_reason: str,
        authorization_metadata: dict[str, Any],
    ) -> ExecutionRunRecord | None:
        """Create at most one successor for a terminal failed/cancelled attempt."""

        previous = self._session.get(ExecutionRunRecord, execution_run_id)
        if previous is None or previous.status not in {
            ExecutionRunStatus.DISPATCH_FAILED,
            ExecutionRunStatus.EXECUTION_FAILED,
            ExecutionRunStatus.EXPIRED,
            ExecutionRunStatus.ABANDONED,
            ExecutionRunStatus.CANCELLED,
        }:
            return None
        successor = self._session.exec(
            select(ExecutionRunRecord).where(
                ExecutionRunRecord.previous_attempt_id == execution_run_id
            )
        ).first()
        if successor is not None:
            return successor
        outbox = self._session.exec(
            select(ExecutionOutboxRecord).where(
                ExecutionOutboxRecord.execution_run_id == execution_run_id
            )
        ).first()
        hypothesis = self._session.get(HypothesisRecord, previous.hypothesis_id)
        if outbox is None or hypothesis is None or hypothesis.task_id != previous.task_id:
            return None
        try:
            retry = self.stage_admit_attempt(
                execution_run_id=uuid4(),
                task_id=previous.task_id,
                hypothesis_id=hypothesis.hypothesis_id,
                executor_type=outbox.executor_type,
                method_id=outbox.method_id,
                parameter_hash=outbox.parameter_hash,
                dispatch_idempotency_key=str(uuid4()),
                prepared_payload=outbox.prepared_payload,
                previous_attempt_id=execution_run_id,
                retry_reason=retry_reason,
                retry_authorization_metadata=authorization_metadata,
            )
            self._session.commit()
            return retry
        except IntegrityError:
            self._session.rollback()
            return self._session.exec(
                select(ExecutionRunRecord).where(
                    ExecutionRunRecord.previous_attempt_id == execution_run_id
                )
            ).first()
