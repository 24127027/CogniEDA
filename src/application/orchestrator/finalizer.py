"""Restart-safe Evidence admission from durable attempt state only."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import TypeAdapter
from sqlmodel import Session, select

from application.orchestrator.evidence_admission import (
    EvidenceAdmissionConflictError,
    execute_evidence_admission_plan,
    validate_and_build_evidence_admission_plan,
)
from application.orchestrator.execution_contracts import ExecutionReceiptEnvelope, PreparedExecution
from application.orchestrator.transition_service import (
    AlreadyCompletedError,
    AlreadyFinalizingError,
    ClaimLostError,
    ExecutionAttemptTransitionService,
)
from db.models import (
    DataProfileRecord,
    ExecutionInboxRecord,
    ExecutionOutboxRecord,
    ExecutionRunRecord,
    HypothesisRecord,
    TaskRecord,
)
from schemas.enums import ExecutionRunStatus


def finalize_attempt(
    session: Session,
    execution_run_id: UUID,
    *,
    finalizer_owner_id: str | None = None,
    claim_duration: timedelta = timedelta(minutes=5),
    test_hook: Callable[[str, Session], None] | None = None,
) -> bool:
    """Atomically admit AnalysisFrame and Evidence from the authoritative inbox row."""

    run = session.get(ExecutionRunRecord, execution_run_id)
    if run is None:
        return False
    if run.status in {
        ExecutionRunStatus.EVIDENCE_ADMITTED,
        ExecutionRunStatus.EXECUTION_FAILED,
    }:
        return True

    if test_hook:
        test_hook("before_claim", session)

    transition_service = ExecutionAttemptTransitionService(session)
    finalizer_owner_id = finalizer_owner_id or str(uuid.uuid4())
    expected_attempt_version = run.attempt_version
    expires_at = datetime.now(UTC) + claim_duration

    if not transition_service.claim_evidence_admission(
        execution_run_id=execution_run_id,
        finalizer_owner_id=finalizer_owner_id,
        expected_attempt_version=expected_attempt_version,
        expires_at=expires_at,
    ):
        session.rollback()
        run_refreshed = session.get(ExecutionRunRecord, execution_run_id)
        if run_refreshed:
            if run_refreshed.status in {
                ExecutionRunStatus.EVIDENCE_ADMITTED,
            }:
                raise AlreadyCompletedError("already_completed")
            elif run_refreshed.status == ExecutionRunStatus.EVIDENCE_ADMITTING:
                raise AlreadyFinalizingError("already_finalizing")
            elif run_refreshed.status == ExecutionRunStatus.CANCELLED:
                raise ClaimLostError("claim_lost")
        raise ClaimLostError("claim_lost")

    run = session.get(ExecutionRunRecord, execution_run_id)
    if run is None:
        session.rollback()
        return False

    inbox = session.exec(
        select(ExecutionInboxRecord).where(
            ExecutionInboxRecord.execution_run_id == execution_run_id,
            ExecutionInboxRecord.status == "pending",
        )
    ).first()
    if (
        inbox is None
        or inbox.dispatch_idempotency_key != run.dispatch_idempotency_key
        or inbox.lease_epoch != run.lease_epoch
    ):
        session.rollback()
        return False

    outbox = session.exec(
        select(ExecutionOutboxRecord).where(
            ExecutionOutboxRecord.execution_run_id == execution_run_id,
            ExecutionOutboxRecord.dispatch_idempotency_key == run.dispatch_idempotency_key,
        )
    ).first()
    if outbox is None:
        session.rollback()
        return False

    if inbox.executor_status == "failed":
        return _finalize_execution_failure(session, run, inbox, transition_service)

    try:
        result = TypeAdapter(ExecutionReceiptEnvelope).validate_python(
            inbox.serialized_observations
        )
        hypothesis = session.get(HypothesisRecord, run.hypothesis_id) if run.hypothesis_id else None
        task = session.get(TaskRecord, run.task_id) if run.task_id else None
        if hypothesis is None or task is None:
            return _finalize_execution_failure(session, run, inbox, transition_service)

        profile = session.get(DataProfileRecord, hypothesis.profile_id)
        if profile is None:
            return _finalize_execution_failure(session, run, inbox, transition_service)

        prepared = PreparedExecution.model_validate(outbox.prepared_payload).model_copy(
            update={
                "hypothesis_ref": str(hypothesis.hypothesis_id),
                "task_ref": str(task.task_id),
                "data_profile_ref": str(profile.profile_id),
                "execution_run_ref": str(run.execution_run_id),
                "execution_run_id": run.execution_run_id,
                "dispatch_idempotency_key": run.dispatch_idempotency_key,
                "lease_epoch": run.lease_epoch,
            }
        )

        try:
            plan = validate_and_build_evidence_admission_plan(
                prepared=prepared,
                result=result,
                run=run,
                inbox=inbox,
                profile=profile,
                hypothesis=hypothesis,
                task=task,
                session_id="durable-finalizer",
            )
        except EvidenceAdmissionConflictError:
            return _finalize_evidence_conflict(session, run, inbox, transition_service)
        except ValueError:
            return _finalize_execution_failure(session, run, inbox, transition_service)

        if test_hook:
            test_hook("before_complete", session)

        return execute_evidence_admission_plan(session, plan, test_hook=test_hook)

    except Exception:
        session.rollback()
        raise


def _finalize_execution_failure(
    session: Session,
    run: ExecutionRunRecord,
    inbox: ExecutionInboxRecord,
    transition_service: ExecutionAttemptTransitionService,
) -> bool:
    """Durably classify a failed execution without manufacturing Evidence."""

    if run.finalization_fencing_epoch is None or run.hypothesis_id is None:
        session.rollback()
        return False
    if not transition_service.stage_fail_execution(
        execution_run_id=run.execution_run_id,
        finalizer_owner_id=run.finalizer_owner_id or "",
        finalization_fencing_epoch=run.finalization_fencing_epoch,
        attempt_version=run.attempt_version,
    ) or not transition_service.stage_consume_authoritative_inbox(
        inbox_id=inbox.inbox_id,
        execution_run_id=run.execution_run_id,
        dispatch_idempotency_key=run.dispatch_idempotency_key or "",
        result_digest=inbox.result_digest,
    ):
        session.rollback()
        return False
    session.commit()
    return True


def _finalize_evidence_conflict(
    session: Session,
    run: ExecutionRunRecord,
    inbox: ExecutionInboxRecord,
    transition_service: ExecutionAttemptTransitionService,
) -> bool:
    """Durably quarantine a conflicting authoritative payload without Evidence."""

    if run.finalization_fencing_epoch is None:
        session.rollback()
        return False
    if not transition_service.stage_quarantine_evidence_conflict(
        execution_run_id=run.execution_run_id,
        finalizer_owner_id=run.finalizer_owner_id or "",
        finalization_fencing_epoch=run.finalization_fencing_epoch,
        attempt_version=run.attempt_version,
        reason="evidence_admission_inbox_conflict",
    ) or not transition_service.stage_mark_authoritative_inbox_conflict(
        inbox_id=inbox.inbox_id,
        execution_run_id=run.execution_run_id,
        dispatch_idempotency_key=run.dispatch_idempotency_key or "",
        result_digest=inbox.result_digest,
    ):
        session.rollback()
        return False
    session.commit()
    return False
