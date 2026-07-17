from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from application.orchestrator.execution_admission import build_execution_admission_operations
from application.orchestrator.planner_commit import commit_planner_operations
from application.orchestrator.transition_service import ExecutionAttemptTransitionService
from repositories import (
    DataProfileRepository,
    ExecutionApprovalRepository,
    ExecutionOutboxRepository,
    ExecutionRunRepository,
    HypothesisRepository,
    PlannerOperationRepository,
    TaskRepository,
)
from schemas.artifacts import DataProfile, Hypothesis, Task
from schemas.common import BaselineSummary, QualityFlag, SchemaSummary
from schemas.enums import (
    DataProfileLifecycleState,
    DataProfileMethod,
    ExecutionApprovalStatus,
    ExecutionRunStatus,
    QualityFlagSeverity,
)
from schemas.provenance import ExecutionApproval


def seed_execution_contract(db_session):
    profile = DataProfileRepository(db_session).create(
        DataProfile(
            dataset_path="data/customers.csv",
            method=DataProfileMethod.BASELINE_SUMMARY,
            schema_summary=SchemaSummary(column_order=["monthly_spend", "churned"]),
            baseline_summary=BaselineSummary(column_names=["monthly_spend", "churned"]),
            row_count=10,
            column_count=2,
            quality_flags=[
                QualityFlag(
                    code="ok",
                    severity=QualityFlagSeverity.INFO,
                    message="Ready for testing.",
                )
            ],
            lifecycle_state=DataProfileLifecycleState.ACTIVE,
            accepted_as_ground_truth=True,
        )
    )
    task = TaskRepository(db_session).create(
        Task(
            title="Test churn association",
            description="Evaluate spend and churn.",
            profile_id=profile.profile_id,
            variables=["monthly_spend", "churned"],
            evidence_expectation="A scoped statistical test.",
        )
    )
    hypothesis = HypothesisRepository(db_session).create(
        Hypothesis(
            task_id=task.task_id,
            profile_id=profile.profile_id,
            statement="Spend is associated with churn.",
            variables=["monthly_spend", "churned"],
            scope="Customers in the accepted profile.",
            validation_method="logistic_regression",
            evidence_expectation="Regression coefficient and uncertainty.",
        )
    )
    return profile, task, hypothesis


def test_commit_admits_one_matching_run_and_outbox_atomically(db_session) -> None:
    _, task, hypothesis = seed_execution_contract(db_session)
    run, operations = build_execution_admission_operations(
        session_id="planner-session",
        task_id=task.task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        executor_type="hypothesis_analyst",
        method_id="logistic_regression",
        parameter_hash="parameters-v1",
        prepared_payload={"contract": "immutable"},
    )
    persisted = PlannerOperationRepository(db_session).create_batch(operations)

    result = commit_planner_operations(
        db_session,
        session_id="planner-session",
        operation_ids=[operation.operation_id for operation in persisted],
    )

    admitted = ExecutionRunRepository(db_session).get_by_id(run.execution_run_id)
    outbox = ExecutionOutboxRepository(db_session).get_by_execution_run_id(run.execution_run_id)
    assert result.committed_operation_ids == [operation.operation_id for operation in persisted]
    assert admitted is not None
    assert admitted.status == ExecutionRunStatus.ADMITTED
    assert admitted.attempt_version == 1
    assert outbox is not None
    assert outbox.execution_run_id == admitted.execution_run_id
    assert outbox.dispatch_idempotency_key == admitted.dispatch_idempotency_key
    assert outbox.status == "pending"


def test_commit_rejects_mismatched_admission_pair_without_partial_write(db_session) -> None:
    _, task, hypothesis = seed_execution_contract(db_session)
    run, operations = build_execution_admission_operations(
        session_id="planner-session",
        task_id=task.task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        executor_type="hypothesis_analyst",
        method_id="logistic_regression",
        parameter_hash="parameters-v1",
        prepared_payload={"contract": "immutable"},
    )
    operations[1].payload["method_id"] = "different_method"
    persisted = PlannerOperationRepository(db_session).create_batch(operations)

    result = commit_planner_operations(
        db_session,
        session_id="planner-session",
        operation_ids=[operation.operation_id for operation in persisted],
    )

    assert result.committed_operation_ids == []
    assert result.failed_operation_ids
    assert ExecutionRunRepository(db_session).get_by_id(run.execution_run_id) is None
    assert (
        ExecutionOutboxRepository(db_session).get_by_execution_run_id(run.execution_run_id)
        is None
    )


def test_execution_approval_is_session_bound_and_consumed_once(db_session) -> None:
    profile, task, hypothesis = seed_execution_contract(db_session)
    approvals = ExecutionApprovalRepository(db_session)
    approval = approvals.create(
        ExecutionApproval(
            session_id="planner-session",
            task_id=task.task_id,
            profile_id=profile.profile_id,
            hypothesis_id=hypothesis.hypothesis_id,
            execution_ref="execution:churn-v1",
            contract_fingerprint="contract-v1",
        )
    )

    approved = approvals.set_status(
        approval.execution_approval_id,
        expected_status=ExecutionApprovalStatus.PENDING,
        status=ExecutionApprovalStatus.APPROVED,
    )
    consumed = approvals.set_status(
        approval.execution_approval_id,
        expected_status=ExecutionApprovalStatus.APPROVED,
        status=ExecutionApprovalStatus.CONSUMED,
    )

    assert approved.status == ExecutionApprovalStatus.APPROVED
    assert consumed.status == ExecutionApprovalStatus.CONSUMED
    with pytest.raises(ValueError, match="expected state"):
        approvals.set_status(
            approval.execution_approval_id,
            expected_status=ExecutionApprovalStatus.PENDING,
            status=ExecutionApprovalStatus.APPROVED,
        )


def test_dispatch_lease_fences_stale_worker_and_reclaims_expired_claim(db_session) -> None:
    _, task, hypothesis = seed_execution_contract(db_session)
    service = ExecutionAttemptTransitionService(db_session)
    run = service.stage_admit_attempt(
        execution_run_id=uuid4(),
        task_id=task.task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        executor_type="hypothesis_analyst",
        method_id="logistic_regression",
        parameter_hash="parameters-v1",
        dispatch_idempotency_key="dispatch-v1",
        prepared_payload={"contract": "immutable"},
    )
    db_session.commit()

    first = service.claim_dispatch(
        run.execution_run_id,
        worker_id="worker-a",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    second = service.claim_dispatch(
        run.execution_run_id,
        worker_id="worker-b",
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )

    assert first is not None
    assert second is not None
    assert second.lease_epoch == 2
    assert not service.mark_running(
        run.execution_run_id,
        worker_id="worker-a",
        lease_epoch=first.lease_epoch,
    )
    assert service.mark_running(
        run.execution_run_id,
        worker_id="worker-b",
        lease_epoch=second.lease_epoch,
    )


def test_cancelled_attempt_has_one_idempotent_retry_successor(db_session) -> None:
    _, task, hypothesis = seed_execution_contract(db_session)
    service = ExecutionAttemptTransitionService(db_session)
    run = service.stage_admit_attempt(
        execution_run_id=uuid4(),
        task_id=task.task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        executor_type="hypothesis_analyst",
        method_id="logistic_regression",
        parameter_hash="parameters-v1",
        dispatch_idempotency_key="dispatch-v1",
        prepared_payload={"contract": "immutable"},
    )
    db_session.commit()
    assert service.cancel_attempt(run.execution_run_id, attempt_version=1)

    first = service.authorize_retry(
        run.execution_run_id,
        retry_reason="retry after cancellation",
        authorization_metadata={"approved_by": "user"},
    )
    second = service.authorize_retry(
        run.execution_run_id,
        retry_reason="retry after cancellation",
        authorization_metadata={"approved_by": "user"},
    )

    assert first is not None
    assert second is not None
    assert first.execution_run_id == second.execution_run_id
    assert first.previous_attempt_id == run.execution_run_id
