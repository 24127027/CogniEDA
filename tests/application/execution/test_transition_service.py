"""Tests for ExecutionAttemptTransitionService."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from application.evidence.identity import result_payload_digest
from application.execution.transition_service import ExecutionAttemptTransitionService
from db.models import (
    ExecutionInboxRecord,
    ExecutionOutboxRecord,
    ExecutionRunRecord,
)
from schemas.common import EvidenceResultSummary
from schemas.enums import EvidenceType, ExecutionRunStatus
from schemas.execution.data_explorer import DataExplorerSuccessResult
from schemas.execution.observations import AnalysisFrameObservation, EvidenceObservation


@pytest.fixture
def memory_session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _observation_payload() -> dict:
    return DataExplorerSuccessResult(
        analysis_frame=AnalysisFrameObservation(frame_hash="frame-hash"),
        evidence_observation=EvidenceObservation(
            evidence_type=EvidenceType.STATISTICAL_TEST,
            method="test_method",
            result_summary=EvidenceResultSummary(summary="Observed test result."),
        ),
    ).model_dump(mode="json")


def test_transition_service_admission(memory_session: Session):
    service = ExecutionAttemptTransitionService(memory_session)

    run_id = uuid.uuid4()
    task_id = uuid.uuid4()
    hyp_id = uuid.uuid4()
    dispatch_key = str(uuid.uuid4())

    run = service.admit_attempt(
        execution_run_id=run_id,
        task_id=task_id,
        hypothesis_id=hyp_id,
        analysis_frame_id=None,
        executor_type="test",
        method_id="test_method",
        parameter_hash="hash",
        dispatch_idempotency_key=dispatch_key,
        prepared_payload={},
    )

    assert run.status == ExecutionRunStatus.ADMITTED
    assert run.attempt_version == 1

    outbox = memory_session.exec(
        select(ExecutionOutboxRecord).where(ExecutionOutboxRecord.execution_run_id == run_id)
    ).first()
    assert outbox is not None
    assert outbox.execution_run_id == run.execution_run_id
    assert outbox.dispatch_idempotency_key == run.dispatch_idempotency_key
    assert outbox.executor_type == run.executor_type
    assert outbox.method_id == run.method_id
    assert outbox.parameter_hash == run.parameter_hash


def test_transition_service_claim_dispatch(memory_session: Session):
    service = ExecutionAttemptTransitionService(memory_session)
    run_id = uuid.uuid4()
    service.admit_attempt(
        execution_run_id=run_id,
        task_id=uuid.uuid4(),
        hypothesis_id=uuid.uuid4(),
        analysis_frame_id=None,
        executor_type="test",
        method_id="test_method",
        parameter_hash="hash",
        dispatch_idempotency_key=str(uuid.uuid4()),
        prepared_payload={},
    )

    expires = datetime.now(UTC) + timedelta(minutes=5)
    run = service.claim_dispatch(run_id, "worker_1", expires)

    assert run is not None
    assert run.status == ExecutionRunStatus.DISPATCH_CLAIMED
    assert run.worker_id == "worker_1"
    assert run.lease_epoch == 1
    assert run.attempt_version == 2


def test_dispatch_claim_rolls_back_when_authoritative_outbox_is_missing(
    memory_session: Session,
) -> None:
    service = ExecutionAttemptTransitionService(memory_session)
    run_id = uuid.uuid4()
    service.admit_attempt(
        execution_run_id=run_id,
        task_id=uuid.uuid4(),
        hypothesis_id=uuid.uuid4(),
        executor_type="test",
        method_id="test_method",
        parameter_hash="hash",
        dispatch_idempotency_key="dispatch-key",
        prepared_payload={},
    )
    outbox = memory_session.exec(
        select(ExecutionOutboxRecord).where(
            ExecutionOutboxRecord.execution_run_id == run_id
        )
    ).one()
    memory_session.delete(outbox)
    memory_session.commit()

    assert (
        service.claim_dispatch(
            run_id,
            "worker",
            datetime.now(UTC) + timedelta(minutes=1),
        )
        is None
    )
    run = memory_session.get(ExecutionRunRecord, run_id)
    assert run is not None and run.status == ExecutionRunStatus.ADMITTED


def test_expired_worker_cannot_submit_without_reclaim(memory_session: Session) -> None:
    service = ExecutionAttemptTransitionService(memory_session)
    run_id = uuid.uuid4()
    service.admit_attempt(
        execution_run_id=run_id,
        task_id=uuid.uuid4(),
        hypothesis_id=uuid.uuid4(),
        executor_type="test",
        method_id="test_method",
        parameter_hash="hash",
        dispatch_idempotency_key="dispatch-key",
        prepared_payload={},
    )
    claimed = service.claim_dispatch(
        run_id,
        "worker",
        datetime.now(UTC) + timedelta(minutes=1),
    )
    assert claimed is not None
    assert service.mark_running(run_id, "worker", claimed.lease_epoch)
    run = memory_session.get(ExecutionRunRecord, run_id)
    assert run is not None
    run.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    memory_session.add(run)
    memory_session.commit()

    payload = _observation_payload()
    assert (
        service.accept_authoritative_result(
            execution_run_id=run_id,
            dispatch_idempotency_key="dispatch-key",
            worker_id="worker",
            lease_epoch=claimed.lease_epoch,
            result_digest=result_payload_digest(payload),
            executor_status="completed",
            serialized_observations=payload,
            error_message=None,
            method_id="test_method",
            producer_identity="worker",
        )
        is None
    )
    assert memory_session.exec(select(ExecutionInboxRecord)).all() == []
    persisted = memory_session.get(ExecutionRunRecord, run_id)
    assert persisted is not None and persisted.status == ExecutionRunStatus.RUNNING


@pytest.mark.parametrize(
    "identity_field",
    ["execution_run_id", "dispatch_idempotency_key", "worker_id", "lease_epoch", "method_id"],
)
def test_result_receipt_rejects_each_attempt_identity_mismatch_independently(
    memory_session: Session,
    identity_field: str,
) -> None:
    service = ExecutionAttemptTransitionService(memory_session)
    run_id = uuid.uuid4()
    dispatch_key = str(uuid.uuid4())
    service.admit_attempt(
        execution_run_id=run_id,
        task_id=uuid.uuid4(),
        hypothesis_id=uuid.uuid4(),
        analysis_frame_id=None,
        executor_type="test",
        method_id="test_method",
        parameter_hash="hash",
        dispatch_idempotency_key=dispatch_key,
        prepared_payload={},
    )
    claimed = service.claim_dispatch(
        run_id,
        "worker_1",
        datetime.now(UTC) + timedelta(minutes=5),
    )
    assert claimed is not None
    assert service.mark_running(run_id, "worker_1", claimed.lease_epoch)

    identity = {
        "execution_run_id": run_id,
        "dispatch_idempotency_key": dispatch_key,
        "worker_id": "worker_1",
        "lease_epoch": claimed.lease_epoch,
        "method_id": "test_method",
    }
    identity[identity_field] = {
        "execution_run_id": uuid.uuid4(),
        "dispatch_idempotency_key": str(uuid.uuid4()),
        "worker_id": "worker_2",
        "lease_epoch": claimed.lease_epoch + 1,
        "method_id": "other_method",
    }[identity_field]

    payload = _observation_payload()
    assert (
        service.accept_authoritative_result(
            **identity,
            result_digest=result_payload_digest(payload),
            executor_status="completed",
            serialized_observations=payload,
            error_message=None,
            producer_identity="worker_1",
        )
        is None
    )
    assert memory_session.exec(select(ExecutionInboxRecord)).all() == []
    persisted_run = memory_session.get(ExecutionRunRecord, run_id)
    assert persisted_run is not None
    assert persisted_run.status == ExecutionRunStatus.RUNNING
    outbox = memory_session.exec(
        select(ExecutionOutboxRecord).where(ExecutionOutboxRecord.execution_run_id == run_id)
    ).one()
    assert outbox.status == "dispatching"


def test_transition_service_concurrent_evidence_admission_claim(memory_session: Session):
    service = ExecutionAttemptTransitionService(memory_session)
    run_id = uuid.uuid4()
    dispatch_key = str(uuid.uuid4())
    service.admit_attempt(
        execution_run_id=run_id,
        task_id=uuid.uuid4(),
        hypothesis_id=uuid.uuid4(),
        analysis_frame_id=None,
        executor_type="test",
        method_id="test_method",
        parameter_hash="hash",
        dispatch_idempotency_key=dispatch_key,
        prepared_payload={},
    )

    expires = datetime.now(UTC) + timedelta(minutes=5)
    assert service.claim_dispatch(run_id, "worker_1", expires) is not None
    assert service.mark_running(run_id, "worker_1", 1)

    payload = _observation_payload()
    service.accept_authoritative_result(
        execution_run_id=run_id,
        dispatch_idempotency_key=dispatch_key,
        worker_id="worker_1",
        lease_epoch=1,
        result_digest=result_payload_digest(payload),
        executor_status="completed",
        serialized_observations=payload,
        error_message=None,
        method_id="test_method",
        producer_identity="worker_1",
    )

    received = memory_session.get(ExecutionRunRecord, run_id)
    assert received is not None
    # Evidence-admission claim 1 wins.
    won = service.claim_evidence_admission(
        run_id, "admission_1", received.attempt_version, expires
    )
    assert won is True

    # Evidence-admission claim 2 loses because the version has incremented.
    won2 = service.claim_evidence_admission(
        run_id, "admission_2", received.attempt_version, expires
    )
    assert won2 is False


def test_cancellation_and_evidence_admission_have_one_terminal_winner(
    memory_session: Session,
):
    """A cancellation CAS prevents a subsequently stale admission claim."""
    service = ExecutionAttemptTransitionService(memory_session)
    run_id = uuid.uuid4()
    dispatch_key = str(uuid.uuid4())
    service.admit_attempt(
        execution_run_id=run_id,
        task_id=uuid.uuid4(),
        hypothesis_id=uuid.uuid4(),
        analysis_frame_id=None,
        executor_type="test",
        method_id="test_method",
        parameter_hash="hash",
        dispatch_idempotency_key=dispatch_key,
        prepared_payload={},
    )
    claimed = service.claim_dispatch(run_id, "worker", datetime.now(UTC) + timedelta(minutes=1))
    assert claimed is not None
    assert service.mark_running(run_id, "worker", claimed.lease_epoch)
    payload = _observation_payload()
    received = service.accept_authoritative_result(
        execution_run_id=run_id,
        dispatch_idempotency_key=dispatch_key,
        worker_id="worker",
        lease_epoch=claimed.lease_epoch,
        result_digest=result_payload_digest(payload),
        executor_status="completed",
        serialized_observations=payload,
        error_message=None,
        method_id="test_method",
        producer_identity="worker",
    )
    assert received is not None
    run = memory_session.get(ExecutionRunRecord, run_id)
    assert service.cancel_attempt(run_id, run.attempt_version)
    assert not service.claim_evidence_admission(
        run_id, "admission", run.attempt_version, datetime.now(UTC) + timedelta(minutes=1)
    )
    assert memory_session.get(ExecutionRunRecord, run_id).status == ExecutionRunStatus.CANCELLED


def test_reclaimed_evidence_admission_fences_late_commit(memory_session: Session):
    """A reclaimed claim gets a higher epoch and rejects the stale owner's CAS."""
    service = ExecutionAttemptTransitionService(memory_session)
    run_id = uuid.uuid4()
    dispatch_key = str(uuid.uuid4())
    service.admit_attempt(
        execution_run_id=run_id,
        task_id=uuid.uuid4(),
        hypothesis_id=uuid.uuid4(),
        analysis_frame_id=None,
        executor_type="test",
        method_id="test_method",
        parameter_hash="hash",
        dispatch_idempotency_key=dispatch_key,
        prepared_payload={},
    )
    dispatch = service.claim_dispatch(run_id, "worker", datetime.now(UTC) + timedelta(minutes=1))
    assert dispatch is not None
    assert service.mark_running(run_id, "worker", dispatch.lease_epoch)
    payload = _observation_payload()
    assert service.accept_authoritative_result(
        execution_run_id=run_id,
        dispatch_idempotency_key=dispatch_key,
        worker_id="worker",
        lease_epoch=dispatch.lease_epoch,
        result_digest=result_payload_digest(payload),
        executor_status="completed",
        serialized_observations=payload,
        error_message=None,
        method_id="test_method",
        producer_identity="worker",
    )
    received = memory_session.get(ExecutionRunRecord, run_id)
    assert service.claim_evidence_admission(
        run_id, "admission-a", received.attempt_version, datetime.now(UTC) + timedelta(minutes=1)
    )
    first = memory_session.get(ExecutionRunRecord, run_id)
    first_epoch = first.finalization_fencing_epoch
    first_version = first.attempt_version
    first.finalization_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    memory_session.add(first)
    memory_session.commit()
    assert not service.stage_admit_evidence(
        execution_run_id=run_id,
        finalizer_owner_id="admission-a",
        finalization_fencing_epoch=first_epoch,
        attempt_version=first_version,
    )
    memory_session.rollback()
    assert service.claim_evidence_admission(
        run_id, "admission-b", first.attempt_version, datetime.now(UTC) + timedelta(minutes=1)
    )
    second = memory_session.get(ExecutionRunRecord, run_id)
    assert second.finalization_fencing_epoch == first_epoch + 1
    assert not service.stage_admit_evidence(
        execution_run_id=run_id,
        finalizer_owner_id="admission-a",
        finalization_fencing_epoch=first_epoch,
        attempt_version=first_version,
    )
    memory_session.rollback()
    assert service.stage_admit_evidence(
        execution_run_id=run_id,
        finalizer_owner_id="admission-b",
        finalization_fencing_epoch=second.finalization_fencing_epoch,
        attempt_version=second.attempt_version,
    )
    memory_session.commit()
    run_rec = memory_session.get(ExecutionRunRecord, run_id)
    assert run_rec is not None and run_rec.status == ExecutionRunStatus.EVIDENCE_ADMITTED


def test_authorize_new_attempt_reuses_hypothesis_and_idempotent(memory_session: Session):
    service = ExecutionAttemptTransitionService(memory_session)
    run_id = uuid.uuid4()
    hyp_id = uuid.uuid4()

    # We need a hypothesis record
    from db.models import HypothesisRecord

    hyp = HypothesisRecord(
        hypothesis_id=hyp_id,
        task_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        statement="statement",
        analysis_intent="exploratory",
        variables=[],
        scope="scope",
        validation_method="method",
        evidence_expectation="expect",
        status="testing",
    )
    memory_session.add(hyp)
    from db.models import TaskRecord
    memory_session.add(
        TaskRecord(
            task_id=hyp.task_id,
            profile_id=hyp.profile_id,
            title="test task",
            description="test",
            variables=["x"],
            task_kind="analytical",
            lifecycle_state="active",
        )
    )
    memory_session.commit()

    from application.evidence.identity import method_parameter_hash
    from schemas.execution.contracts import PreparedExecution

    prepared_payload = PreparedExecution(
        task_ref=str(hyp.task_id),
        data_profile_ref=str(hyp.profile_id),
        hypothesis_ref=str(hyp_id),
        task_title="test task",
        dataset_path="data.csv",
        hypothesis={
            "statement": "statement",
            "variables": [],
            "scope": "scope",
            "validation_method": "test_method",
            "evidence_expectation": "expect",
        },
        specification={
            "claim_type": "association",
            "variable_bindings": [],
            "scope": "scope",
            "evidence_expectation": "expect",
            "decision_rule": {"p_value": 0.05},
            "validation_method": "test_method",
            "executor_id": "test",
            "method_parameters": [],
        },
        contract_fingerprint="test-contract",
    ).model_dump(mode="json")
    parameter_hash = method_parameter_hash([])
    dispatch_key = str(uuid.uuid4())
    run = service.admit_attempt(
        execution_run_id=run_id,
        task_id=hyp.task_id,
        hypothesis_id=hyp_id,
        analysis_frame_id=None,
        executor_type="test",
        method_id="test_method",
        parameter_hash=parameter_hash,
        dispatch_idempotency_key=dispatch_key,
        prepared_payload=prepared_payload,
    )

    # Fail it so it's retryable
    service.fail_execution(run_id, run.attempt_version, "failed")

    # First retry
    new_run = service.authorize_new_attempt(run_id, "retry", {})
    assert new_run is not None
    assert new_run.execution_run_id != run_id
    assert new_run.hypothesis_id == hyp_id  # Reused hypothesis!
    assert new_run.previous_attempt_id == run_id

    # Check hypothesis count
    from sqlmodel import select

    hyp_count = len(memory_session.exec(select(HypothesisRecord)).all())
    assert hyp_count == 1

    # Concurrent / idempotent retry
    new_run_2 = service.authorize_new_attempt(run_id, "retry", {})
    assert new_run_2 is not None
    assert new_run_2.execution_run_id == new_run.execution_run_id

    # A failed successor is retried from itself, never by forking the original
    # predecessor into a second direct successor.
    assert service.fail_execution(
        new_run.execution_run_id,
        new_run.attempt_version,
        "second failure",
    )
    assert service.authorize_new_attempt(run_id, "retry original", {}) is not None
    assert (
        service.authorize_new_attempt(run_id, "retry original", {}).execution_run_id
        == new_run.execution_run_id
    )


def test_execution_run_predecessor_is_database_unique(memory_session: Session):
    predecessor_id = uuid.uuid4()
    memory_session.add(ExecutionRunRecord(previous_attempt_id=predecessor_id))
    memory_session.commit()

    memory_session.add(ExecutionRunRecord(previous_attempt_id=predecessor_id))
    with pytest.raises(IntegrityError):
        memory_session.commit()
    memory_session.rollback()
