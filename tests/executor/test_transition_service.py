"""Tests for ExecutionAttemptTransitionService."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from application.orchestrator.transition_service import ExecutionAttemptTransitionService
from db.models import (
    ExecutionOutboxRecord,
    ExecutionRunRecord,
)
from schemas.enums import ExecutionRunStatus


@pytest.fixture
def memory_session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


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

    outbox = memory_session.get(ExecutionOutboxRecord, run_id)
    # The outbox might not be indexed by run_id natively if outbox_id is primary
    from sqlmodel import select

    outbox = memory_session.exec(
        select(ExecutionOutboxRecord).where(ExecutionOutboxRecord.execution_run_id == run_id)
    ).first()
    assert outbox is not None


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


def test_transition_service_concurrent_finalization_claim(memory_session: Session):
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

    service.accept_authoritative_result(
        execution_run_id=run_id,
        dispatch_idempotency_key=dispatch_key,
        worker_id="worker_1",
        lease_epoch=1,
        result_digest="digest",
        executor_status="completed",
        serialized_observations={},
        error_message=None,
        method_id="test_method",
        producer_identity="worker_1",
    )

    # Finalization claim 1 wins
    won = service.claim_finalization(run_id, "finalizer_1", 4, expires)
    assert won is True

    # Finalization claim 2 loses because version has incremented
    won2 = service.claim_finalization(run_id, "finalizer_2", 4, expires)
    assert won2 is False


def test_cancellation_and_finalization_have_one_terminal_winner(memory_session: Session):
    """A cancellation CAS prevents a subsequently stale finalization claim."""
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
    received = service.accept_authoritative_result(
        execution_run_id=run_id,
        dispatch_idempotency_key=dispatch_key,
        worker_id="worker",
        lease_epoch=claimed.lease_epoch,
        result_digest="authoritative",
        executor_status="completed",
        serialized_observations={},
        error_message=None,
        method_id="test_method",
        producer_identity="worker",
    )
    assert received is not None
    run = memory_session.get(ExecutionRunRecord, run_id)
    assert service.cancel_attempt(run_id, run.attempt_version)
    assert not service.claim_finalization(
        run_id, "finalizer", run.attempt_version, datetime.now(UTC) + timedelta(minutes=1)
    )
    assert memory_session.get(ExecutionRunRecord, run_id).status == ExecutionRunStatus.CANCELLED


def test_reclaimed_finalizer_fences_late_commit(memory_session: Session):
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
    assert service.accept_authoritative_result(
        execution_run_id=run_id,
        dispatch_idempotency_key=dispatch_key,
        worker_id="worker",
        lease_epoch=dispatch.lease_epoch,
        result_digest="authoritative",
        executor_status="completed",
        serialized_observations={},
        error_message=None,
        method_id="test_method",
        producer_identity="worker",
    )
    received = memory_session.get(ExecutionRunRecord, run_id)
    assert service.claim_finalization(
        run_id, "finalizer-a", received.attempt_version, datetime.now(UTC) - timedelta(seconds=1)
    )
    first = memory_session.get(ExecutionRunRecord, run_id)
    first_epoch = first.finalization_fencing_epoch
    first_version = first.attempt_version
    assert service.claim_finalization(
        run_id, "finalizer-b", first.attempt_version, datetime.now(UTC) + timedelta(minutes=1)
    )
    second = memory_session.get(ExecutionRunRecord, run_id)
    assert second.finalization_fencing_epoch == first_epoch + 1
    assert not service.stage_complete_finalization(
        execution_run_id=run_id,
        finalizer_owner_id="finalizer-a",
        finalization_fencing_epoch=first_epoch,
        attempt_version=first_version,
    )
    memory_session.rollback()
    assert service.stage_complete_finalization(
        execution_run_id=run_id,
        finalizer_owner_id="finalizer-b",
        finalization_fencing_epoch=second.finalization_fencing_epoch,
        attempt_version=second.attempt_version,
    )
    memory_session.commit()
    assert memory_session.get(ExecutionRunRecord, run_id).status == ExecutionRunStatus.COMPLETED
