"""Guarded, database-backed state transitions for one execution attempt."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, or_, update
from sqlmodel import Session, select

from db.models import (
    ExecutionInboxRecord,
    ExecutionOutboxRecord,
    ExecutionRunRecord,
    HypothesisRecord,
)
from schemas.enums import ExecutionRunStatus


class ExecutionTransitionError(ValueError):
    """Base exception class for execution attempt transition failures."""

    pass


class AlreadyFinalizingError(ExecutionTransitionError):
    """Raised when an attempt is already finalizing."""

    pass


class AlreadyCompletedError(ExecutionTransitionError):
    """Raised when an attempt is already completed."""

    pass


class ClaimLostError(ExecutionTransitionError):
    """Raised when a finalization claim has been lost or cancelled."""

    pass


class ExecutionAttemptTransitionService:
    """The sole production writer for mutable execution-attempt protocol state.

    A method either commits one small transition, or (for finalization) stages a
    fenced transition in the caller's scientific transaction.  Callers never
    assign attempt state on ORM objects directly.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    def stage_admit_attempt(
        self,
        *,
        execution_run_id: UUID,
        task_id: UUID | None,
        hypothesis_id: UUID | None,
        analysis_frame_id: UUID | None = None,
        executor_type: str,
        method_id: str,
        parameter_hash: str,
        dispatch_idempotency_key: str,
        prepared_payload: dict[str, Any],
        previous_attempt_id: UUID | None = None,
        retry_reason: str | None = None,
        retry_authorization_metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> ExecutionRunRecord:
        """Stage one immutable attempt/outbox identity pair in the current transaction.

        Construction belongs here so callers cannot manufacture execution records
        outside the transition owner, including in an enclosing planner commit.
        """
        run = ExecutionRunRecord(
            execution_run_id=execution_run_id,
            task_id=task_id,
            hypothesis_id=hypothesis_id,
            analysis_frame_id=analysis_frame_id,
            executor_type=executor_type,
            method_id=method_id,
            parameter_hash=parameter_hash,
            status=ExecutionRunStatus.ADMITTED,
            dispatch_idempotency_key=dispatch_idempotency_key,
            attempt_version=1,
            previous_attempt_id=previous_attempt_id,
            retry_reason=retry_reason,
            retry_authorization_metadata=retry_authorization_metadata,
            created_at=created_at or self._now(),
        )
        outbox = ExecutionOutboxRecord(
            execution_run_id=execution_run_id,
            dispatch_idempotency_key=dispatch_idempotency_key,
            executor_type=executor_type,
            method_id=method_id,
            parameter_hash=parameter_hash,
            prepared_payload=prepared_payload,
            status="pending",
            created_at=created_at or self._now(),
        )
        if run.status != ExecutionRunStatus.ADMITTED or run.attempt_version != 1:
            raise ValueError("New attempts must begin admitted at version 1.")
        if not run.dispatch_idempotency_key:
            raise ValueError("An admitted attempt requires a dispatch idempotency key.")
        if (
            outbox.execution_run_id != run.execution_run_id
            or outbox.dispatch_idempotency_key != run.dispatch_idempotency_key
            or outbox.method_id != run.method_id
            or outbox.parameter_hash != run.parameter_hash
        ):
            raise ValueError("ExecutionRun and outbox immutable identity fields disagree.")
        self._session.add(run)
        # There is no ORM relationship between these tables, so flush the parent
        # before staging the dependent outbox on SQLite and other FK-enforcing DBs.
        self._session.flush()
        self._session.add(outbox)
        return run

    def admit_attempt(self, **kwargs: Any) -> ExecutionRunRecord:
        """Create and commit one new attempt and its matching outbox record."""
        run = self.stage_admit_attempt(**kwargs)
        self._session.commit()
        self._session.refresh(run)
        return run

    def claim_dispatch(
        self, execution_run_id: UUID, worker_id: str, expires_at: datetime
    ) -> ExecutionRunRecord | None:
        now = self._now()
        claimed = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(
                or_(
                    ExecutionRunRecord.status == ExecutionRunStatus.ADMITTED,
                    (
                        ExecutionRunRecord.status.in_(
                            [ExecutionRunStatus.DISPATCH_CLAIMED, ExecutionRunStatus.RUNNING]
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
        outbox = self._session.exec(
            select(ExecutionOutboxRecord).where(
                ExecutionOutboxRecord.execution_run_id == execution_run_id
            )
        ).first()
        if outbox is not None:
            consumed = self._session.execute(
                update(ExecutionOutboxRecord)
                .where(ExecutionOutboxRecord.outbox_id == outbox.outbox_id)
                .where(ExecutionOutboxRecord.status == "pending")
                .values(status="dispatching")
            )
            if consumed.rowcount != 1:
                self._session.rollback()
                return None
        self._session.commit()
        return self._session.get(ExecutionRunRecord, execution_run_id)

    def renew_dispatch_lease(
        self, execution_run_id: UUID, worker_id: str, lease_epoch: int, expires_at: datetime
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
                lease_expires_at=expires_at, attempt_version=ExecutionRunRecord.attempt_version + 1
            )
            .execution_options(synchronize_session=False)
        )
        if updated.rowcount != 1:
            self._session.rollback()
            return False
        self._session.commit()
        return True

    def mark_running(self, execution_run_id: UUID, worker_id: str, lease_epoch: int) -> bool:
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

    def accept_authoritative_result(
        self,
        *,
        execution_run_id: UUID,
        dispatch_idempotency_key: str,
        worker_id: str,
        lease_epoch: int,
        result_digest: str,
        executor_status: str,
        serialized_observations: dict[str, Any],
        error_message: str | None,
        method_id: str,
        producer_identity: str | None,
    ) -> ExecutionInboxRecord | None:
        """CAS result receipt; duplicate payloads replay and conflicts quarantine."""
        now = self._now()
        transitioned = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(ExecutionRunRecord.dispatch_idempotency_key == dispatch_idempotency_key)
            .where(ExecutionRunRecord.worker_id == worker_id)
            .where(ExecutionRunRecord.lease_epoch == lease_epoch)
            .where(ExecutionRunRecord.method_id == method_id)
            .where(
                ExecutionRunRecord.status.in_(
                    [ExecutionRunStatus.DISPATCH_CLAIMED, ExecutionRunStatus.RUNNING]
                )
            )
            .values(
                status=ExecutionRunStatus.RESULT_RECEIVED,
                attempt_version=ExecutionRunRecord.attempt_version + 1,
            )
            .execution_options(synchronize_session=False)
        )
        if transitioned.rowcount == 1:
            inbox = ExecutionInboxRecord(
                execution_run_id=execution_run_id,
                dispatch_idempotency_key=dispatch_idempotency_key,
                lease_epoch=lease_epoch,
                result_digest=result_digest,
                executor_status=executor_status,
                serialized_observations=serialized_observations,
                error_message=error_message,
                method_id=method_id,
                producer_identity=producer_identity,
                status="pending",
                created_at=now,
            )
            self._session.add(inbox)
            self._session.execute(
                update(ExecutionOutboxRecord)
                .where(ExecutionOutboxRecord.execution_run_id == execution_run_id)
                .where(ExecutionOutboxRecord.status == "dispatching")
                .values(status="processed", dispatched_at=now)
            )
            try:
                self._session.commit()
            except Exception:
                self._session.rollback()
                raise
            return inbox

        self._session.rollback()
        existing = self._session.exec(
            select(ExecutionInboxRecord).where(
                ExecutionInboxRecord.execution_run_id == execution_run_id
            )
        ).first()
        if existing is None:
            return None
        if (
            existing.dispatch_idempotency_key == dispatch_idempotency_key
            and existing.lease_epoch == lease_epoch
            and existing.result_digest == result_digest
        ):
            return existing
        # A conflicting envelope is retained for audit; it never replaces the authority.
        self._session.add(
            ExecutionInboxRecord(
                execution_run_id=execution_run_id,
                dispatch_idempotency_key=dispatch_idempotency_key,
                lease_epoch=lease_epoch,
                result_digest=result_digest,
                executor_status=executor_status,
                serialized_observations=serialized_observations,
                error_message=error_message,
                method_id=method_id,
                producer_identity=producer_identity,
                status="conflict",
                created_at=now,
            )
        )
        self.mark_result_conflict(execution_run_id)
        return None

    def mark_result_conflict(self, execution_run_id: UUID) -> bool:
        updated = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(
                ExecutionRunRecord.status.in_(
                    [
                        ExecutionRunStatus.RESULT_RECEIVED,
                        ExecutionRunStatus.DISPATCH_CLAIMED,
                        ExecutionRunStatus.RUNNING,
                    ]
                )
            )
            .values(
                status=ExecutionRunStatus.RESULT_CONFLICT,
                attempt_version=ExecutionRunRecord.attempt_version + 1,
            )
        )
        if updated.rowcount != 1:
            self._session.rollback()
            return False
        self._session.commit()
        return True

    def claim_finalization(
        self,
        execution_run_id: UUID,
        finalizer_owner_id: str,
        expected_attempt_version: int,
        expires_at: datetime | None = None,
    ) -> bool:
        now = self._now()
        updated = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(ExecutionRunRecord.attempt_version == expected_attempt_version)
            .where(
                or_(
                    ExecutionRunRecord.status == ExecutionRunStatus.RESULT_RECEIVED,
                    (ExecutionRunRecord.status == ExecutionRunStatus.FINALIZING)
                    & (ExecutionRunRecord.finalization_expires_at.is_not(None))
                    & (ExecutionRunRecord.finalization_expires_at < now),
                )
            )
            .values(
                status=ExecutionRunStatus.FINALIZING,
                attempt_version=ExecutionRunRecord.attempt_version + 1,
                finalizer_owner_id=finalizer_owner_id,
                finalization_fencing_epoch=func.coalesce(
                    ExecutionRunRecord.finalization_fencing_epoch, 0
                )
                + 1,
                finalization_claimed_at=now,
                finalization_expires_at=expires_at,
            )
            .execution_options(synchronize_session=False)
        )
        if updated.rowcount != 1:
            self._session.rollback()
            return False
        self._session.commit()
        return True

    def stage_complete_finalization(
        self,
        *,
        execution_run_id: UUID,
        finalizer_owner_id: str,
        finalization_fencing_epoch: int,
        attempt_version: int,
        final_status: ExecutionRunStatus = ExecutionRunStatus.COMPLETED,
    ) -> bool:
        """Stage the final CAS with scientific writes; caller commits or rolls back all."""
        updated = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(ExecutionRunRecord.status == ExecutionRunStatus.FINALIZING)
            .where(ExecutionRunRecord.finalizer_owner_id == finalizer_owner_id)
            .where(ExecutionRunRecord.finalization_fencing_epoch == finalization_fencing_epoch)
            .where(ExecutionRunRecord.attempt_version == attempt_version)
            .values(
                status=final_status,
                attempt_version=ExecutionRunRecord.attempt_version + 1,
                finalization_expires_at=None,
            )
            .execution_options(synchronize_session=False)
        )
        return updated.rowcount == 1

    def stage_consume_inbox(self, inbox_id: UUID) -> bool:
        updated = self._session.execute(
            update(ExecutionInboxRecord)
            .where(ExecutionInboxRecord.inbox_id == inbox_id)
            .where(ExecutionInboxRecord.status == "pending")
            .values(status="processed", processed_at=self._now())
        )
        return updated.rowcount == 1

    def stage_fail_finalization(
        self,
        *,
        execution_run_id: UUID,
        hypothesis_id: UUID,
        finalizer_owner_id: str,
        finalization_fencing_epoch: int,
        attempt_version: int,
    ) -> bool:
        """Atomically end a failed attempt and return its contract to approved."""
        if not self.stage_complete_finalization(
            execution_run_id=execution_run_id,
            finalizer_owner_id=finalizer_owner_id,
            finalization_fencing_epoch=finalization_fencing_epoch,
            attempt_version=attempt_version,
            final_status=ExecutionRunStatus.EXECUTION_FAILED,
        ):
            return False
        restored = self._session.execute(
            update(HypothesisRecord)
            .where(HypothesisRecord.hypothesis_id == hypothesis_id)
            .where(HypothesisRecord.status == "testing")
            .values(status="approved")
            .execution_options(synchronize_session=False)
        )
        return restored.rowcount == 1

    def fail_dispatch(self, execution_run_id: UUID, attempt_version: int, reason: str) -> bool:
        return self._terminal_with_outbox(
            execution_run_id, attempt_version, ExecutionRunStatus.DISPATCH_FAILED, reason, "failed"
        )

    def fail_execution(self, execution_run_id: UUID, attempt_version: int, reason: str) -> bool:
        return self._terminal_with_outbox(
            execution_run_id,
            attempt_version,
            ExecutionRunStatus.EXECUTION_FAILED,
            reason,
            "processed",
        )

    def _terminal_with_outbox(
        self,
        execution_run_id: UUID,
        attempt_version: int,
        status: ExecutionRunStatus,
        reason: str,
        outbox_status: str,
    ) -> bool:
        updated = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(ExecutionRunRecord.attempt_version == attempt_version)
            .where(
                ExecutionRunRecord.status.notin_(
                    [
                        ExecutionRunStatus.COMPLETED,
                        ExecutionRunStatus.CANCELLED,
                        ExecutionRunStatus.FINALIZING,
                    ]
                )
            )
            .values(
                status=status,
                recovery_status=reason,
                attempt_version=ExecutionRunRecord.attempt_version + 1,
            )
        )
        if updated.rowcount != 1:
            self._session.rollback()
            return False
        self._session.execute(
            update(ExecutionOutboxRecord)
            .where(ExecutionOutboxRecord.execution_run_id == execution_run_id)
            .values(status=outbox_status)
        )
        self._session.commit()
        return True

    def cancel_attempt(self, execution_run_id: UUID, expected_attempt_version: int) -> bool:
        updated = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(ExecutionRunRecord.attempt_version == expected_attempt_version)
            .where(
                ExecutionRunRecord.status.in_(
                    [
                        ExecutionRunStatus.ADMITTED,
                        ExecutionRunStatus.DISPATCH_CLAIMED,
                        ExecutionRunStatus.RUNNING,
                        ExecutionRunStatus.RESULT_RECEIVED,
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

    def expire_or_release_attempt(
        self,
        execution_run_id: UUID,
        expected_attempt_version: int,
        *,
        now: datetime | None = None,
    ) -> bool:
        now = now or self._now()
        updated = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(ExecutionRunRecord.attempt_version == expected_attempt_version)
            .where(
                ExecutionRunRecord.status.in_(
                    [ExecutionRunStatus.DISPATCH_CLAIMED, ExecutionRunStatus.RUNNING]
                )
            )
            .where(ExecutionRunRecord.lease_expires_at < now)
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

    def authorize_new_attempt(
        self, old_execution_run_id: UUID, retry_reason: str, authorization_metadata: dict[str, Any]
    ) -> ExecutionRunRecord | None:
        old_run = self._session.get(ExecutionRunRecord, old_execution_run_id)
        if old_run is None or old_run.status not in {
            ExecutionRunStatus.EXECUTION_FAILED,
            ExecutionRunStatus.DISPATCH_FAILED,
            ExecutionRunStatus.ABANDONED,
        }:
            return None
        old_outbox = self._session.exec(
            select(ExecutionOutboxRecord).where(
                ExecutionOutboxRecord.execution_run_id == old_execution_run_id
            )
        ).first()
        old_hypothesis = self._session.get(HypothesisRecord, old_run.hypothesis_id)
        if old_outbox is None or old_hypothesis is None:
            return None
        new_hypothesis = HypothesisRecord(
            hypothesis_id=uuid4(),
            task_id=old_hypothesis.task_id,
            profile_id=old_hypothesis.profile_id,
            statement=old_hypothesis.statement,
            analysis_intent=old_hypothesis.analysis_intent,
            variables=old_hypothesis.variables,
            scope=old_hypothesis.scope,
            validation_method=old_hypothesis.validation_method,
            evidence_expectation=old_hypothesis.evidence_expectation,
            status="approved",
        )
        self._session.add(new_hypothesis)
        new_run_id, dispatch_key = uuid4(), str(uuid4())
        run = self.stage_admit_attempt(
            execution_run_id=new_run_id,
            task_id=old_run.task_id,
            hypothesis_id=new_hypothesis.hypothesis_id,
            analysis_frame_id=old_run.analysis_frame_id,
            executor_type=old_outbox.executor_type,
            method_id=old_outbox.method_id,
            parameter_hash=old_outbox.parameter_hash,
            dispatch_idempotency_key=dispatch_key,
            prepared_payload=old_outbox.prepared_payload,
            previous_attempt_id=old_execution_run_id,
            retry_reason=retry_reason,
            retry_authorization_metadata=authorization_metadata,
        )
        self._session.commit()
        return run

    def mark_recovery_error(
        self, execution_run_id: UUID, expected_attempt_version: int, error_msg: str
    ) -> bool:
        updated = self._session.execute(
            update(ExecutionRunRecord)
            .where(ExecutionRunRecord.execution_run_id == execution_run_id)
            .where(ExecutionRunRecord.attempt_version == expected_attempt_version)
            .where(
                ExecutionRunRecord.status.notin_(
                    [ExecutionRunStatus.COMPLETED, ExecutionRunStatus.CANCELLED]
                )
            )
            .values(
                recovery_status=error_msg, attempt_version=ExecutionRunRecord.attempt_version + 1
            )
        )
        if updated.rowcount != 1:
            self._session.rollback()
            return False
        self._session.commit()
        return True
