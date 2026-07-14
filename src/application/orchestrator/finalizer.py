"""Restart-safe scientific finalization from durable attempt state only."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from langgraph.runtime import Runtime
from sqlmodel import Session, select

from agents.planner.nodes import evaluate_hypothesis, review_execution, validate_evidence
from agents.planner.types import Context, ExecutorResult, PreparedExecution, State
from application.orchestrator.planner_commit import commit_planner_operations
from application.orchestrator.transition_service import (
    AlreadyCompletedError,
    AlreadyFinalizingError,
    ClaimLostError,
    ExecutionAttemptTransitionService,
)
from db.models import ExecutionInboxRecord, ExecutionOutboxRecord, ExecutionRunRecord
from schemas.enums import ExecutionRunStatus, PlannerOperationType


def finalize_attempt(
    session: Session,
    execution_run_id: UUID,
    *,
    finalizer_owner_id: str | None = None,
    claim_duration: timedelta = timedelta(minutes=5),
    test_hook: Callable[[str, Session], None] | None = None,
) -> bool:
    """Atomically synthesize scientific state from the authoritative inbox row."""

    run = session.get(ExecutionRunRecord, execution_run_id)
    if run is None:
        return False
    if run.status == ExecutionRunStatus.COMPLETED:
        return True

    if test_hook:
        test_hook("before_claim", session)

    transition_service = ExecutionAttemptTransitionService(session)
    finalizer_owner_id = finalizer_owner_id or str(uuid.uuid4())
    expected_attempt_version = run.attempt_version
    expires_at = datetime.now(UTC) + claim_duration

    if not transition_service.claim_finalization(
        execution_run_id=execution_run_id,
        finalizer_owner_id=finalizer_owner_id,
        expected_attempt_version=expected_attempt_version,
        expires_at=expires_at,
    ):
        session.rollback()
        run_refreshed = session.get(ExecutionRunRecord, execution_run_id)
        if run_refreshed:
            if run_refreshed.status == ExecutionRunStatus.COMPLETED:
                raise AlreadyCompletedError("already_completed")
            elif run_refreshed.status == ExecutionRunStatus.FINALIZING:
                raise AlreadyFinalizingError("already_finalizing")
            elif run_refreshed.status == ExecutionRunStatus.CANCELLED:
                raise ClaimLostError("claim_lost")
        raise ClaimLostError("claim_lost")

    run = session.get(ExecutionRunRecord, execution_run_id)

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
        return False
    outbox = session.exec(
        select(ExecutionOutboxRecord).where(
            ExecutionOutboxRecord.execution_run_id == execution_run_id,
            ExecutionOutboxRecord.dispatch_idempotency_key == run.dispatch_idempotency_key,
        )
    ).first()
    if outbox is None:
        return False

    if inbox.executor_status == "failed":
        return _finalize_execution_failure(session, run, inbox, transition_service)
    try:
        result = ExecutorResult.model_validate(inbox.serialized_observations)
        prepared = PreparedExecution.model_validate(outbox.prepared_payload).model_copy(
            update={
                "hypothesis_ref": "hypothesis:durable",
                "execution_run_ref": "execution_run:durable",
                "execution_run_id": run.execution_run_id,
                "dispatch_idempotency_key": run.dispatch_idempotency_key,
                "lease_epoch": run.lease_epoch,
            }
        )
        state = State(
            query="",
            session_id="durable-finalizer",
            prepared_execution=prepared,
            executor_result=result,
            object_reference_index={
                prepared.task_ref: str(run.task_id),
                prepared.data_profile_ref: str(_profile_id_for_run(session, run)),
                prepared.hypothesis_ref: str(run.hypothesis_id),
                prepared.execution_run_ref: str(run.execution_run_id),
            },
        )
        database_url = str(session.get_bind().url)
        runtime = Runtime(context=Context(database_url=database_url))
        review_execution(state, runtime)
        state.planner_operations = [
            operation
            for operation in state.planner_operations
            if operation.operation_type != PlannerOperationType.CREATE_EXECUTION_INBOX
        ]
        validate_evidence(state, runtime)
        evaluate_hypothesis(state, runtime)
        if state.execution_review is not None and not state.execution_review.succeeded:
            return _finalize_execution_failure(session, run, inbox, transition_service)

        if run.finalization_fencing_epoch is None:
            raise ValueError("Finalization claim did not allocate a fencing epoch.")

        if test_hook:
            test_hook("before_complete", session)

        if not transition_service.stage_complete_finalization(
            execution_run_id=execution_run_id,
            finalizer_owner_id=finalizer_owner_id,
            finalization_fencing_epoch=run.finalization_fencing_epoch,
            attempt_version=run.attempt_version,
        ) or not transition_service.stage_consume_inbox(inbox.inbox_id):
            session.rollback()
            return False
        state.planner_operations = [
            operation
            for operation in state.planner_operations
            if operation.operation_type != PlannerOperationType.UPDATE_EXECUTION_RUN
        ]
        result_commit = commit_planner_operations(session, state.planner_operations, commit=False)
        if result_commit.failed_operation_ids:
            session.rollback()
            return False

        if test_hook:
            test_hook("before_commit", session)

        session.commit()
        return True
    except Exception:
        session.rollback()
        raise


def _profile_id_for_run(session: Session, run: ExecutionRunRecord) -> UUID:
    from db.models import HypothesisRecord

    hypothesis = session.get(HypothesisRecord, run.hypothesis_id)
    if hypothesis is None:
        raise ValueError("ExecutionRun references a missing Hypothesis.")
    return hypothesis.profile_id


def _finalize_execution_failure(
    session: Session,
    run: ExecutionRunRecord,
    inbox: ExecutionInboxRecord,
    transition_service: ExecutionAttemptTransitionService,
) -> bool:
    """Durably classify a failed execution without manufacturing Evidence."""

    if run.finalization_fencing_epoch is None:
        return False
    if not transition_service.stage_fail_finalization(
        execution_run_id=run.execution_run_id,
        hypothesis_id=run.hypothesis_id,
        finalizer_owner_id=run.finalizer_owner_id or "",
        finalization_fencing_epoch=run.finalization_fencing_epoch,
        attempt_version=run.attempt_version,
    ) or not transition_service.stage_consume_inbox(inbox.inbox_id):
        session.rollback()
        return False
    session.commit()
    return True
