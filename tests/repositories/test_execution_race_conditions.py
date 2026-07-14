"""Tests proving the concurrency safety of the Execution subsystem."""

import threading
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from application.orchestrator.transition_service import ExecutionAttemptTransitionService
from db.models import DataProfileRecord, ExecutionRunRecord, HypothesisRecord, TaskRecord
from db.session import get_session
from schemas.enums import ExecutionRunStatus


def _create_admitted_run(db_session) -> str:
    profile_id = uuid4()
    task_id = uuid4()
    hypothesis_id = uuid4()
    db_session.add(
        DataProfileRecord(
            profile_id=profile_id,
            dataset_path="test",
            dvc_hash=str(uuid4()),
            schema_summary={"column_order": []},
            baseline_summary={"column_names": []},
            row_count=0,
            column_count=0,
            method="baseline_summary",
        )
    )
    db_session.flush()
    db_session.add(
        TaskRecord(
            task_id=task_id,
            profile_id=profile_id,
            title="test",
            description="test",
            variables=[],
            task_kind="analytical",
        )
    )
    db_session.flush()
    db_session.add(
        HypothesisRecord(
            hypothesis_id=hypothesis_id,
            task_id=task_id,
            profile_id=profile_id,
            statement="test",
            variables=[],
            scope="test",
            validation_method="test",
            evidence_expectation="test",
        )
    )
    db_session.flush()

    svc = ExecutionAttemptTransitionService(db_session)
    run_id = uuid4()
    svc.admit_attempt(
        execution_run_id=run_id,
        task_id=task_id,
        hypothesis_id=hypothesis_id,
        executor_type="test",
        method_id="test",
        parameter_hash="test",
        dispatch_idempotency_key="key",
        prepared_payload={},
    )
    db_session.commit()
    return str(run_id)


def _move_to_result_received(db_session, run_id: UUID) -> None:
    service = ExecutionAttemptTransitionService(db_session)
    claimed = service.claim_dispatch(
        run_id,
        "worker-1",
        datetime.now(UTC) + timedelta(minutes=5),
    )
    assert claimed is not None
    assert service.mark_running(run_id, "worker-1", claimed.lease_epoch)
    assert service.accept_authoritative_result(
        execution_run_id=run_id,
        dispatch_idempotency_key="key",
        worker_id="worker-1",
        lease_epoch=claimed.lease_epoch,
        result_digest="authoritative-result",
        executor_status="completed",
        serialized_observations={},
        error_message=None,
        method_id="test",
        producer_identity="worker-1",
    )


def test_concurrent_finalization_claim_has_real_overlap(db_session):
    database_url = str(db_session.get_bind().url)
    run_id_str = _create_admitted_run(db_session)

    # We must mark the run as execution_completed so it can be finalized
    from uuid import UUID

    run_id = UUID(run_id_str)

    _move_to_result_received(db_session, run_id)

    barrier = threading.Barrier(2)
    results = []
    expected_versions = []

    def claim_worker(worker_id):
        session = get_session(database_url)
        try:
            svc = ExecutionAttemptTransitionService(session)
            run = session.get(ExecutionRunRecord, run_id)
            expected_versions.append(run.attempt_version)
            # Both independent transactions hold the same pre-claim snapshot
            # before either can execute the conditional UPDATE.
            barrier.wait(timeout=5.0)
            res = svc.claim_finalization(
                run_id,
                worker_id,
                run.attempt_version,
                datetime.now(UTC) + timedelta(minutes=5),
            )
            if res:
                results.append(True)
        except Exception as e:
            results.append(e)
        finally:
            session.close()

    t1 = threading.Thread(target=claim_worker, args=("finalizer-A",))
    t2 = threading.Thread(target=claim_worker, args=("finalizer-B",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    successes = [r for r in results if r is True]
    assert expected_versions[0] == expected_versions[1]
    assert len(successes) == 1, "Exactly one thread should successfully claim finalization."


def test_cancellation_beats_finalization(db_session):
    database_url = str(db_session.get_bind().url)
    run_id_str = _create_admitted_run(db_session)
    from uuid import UUID

    run_id = UUID(run_id_str)

    _move_to_result_received(db_session, run_id)

    # Cancel runs first
    cancel_session = get_session(database_url)
    cancel_svc = ExecutionAttemptTransitionService(cancel_session)
    cancel_run = cancel_session.get(ExecutionRunRecord, run_id)
    cancel_res = cancel_svc.cancel_attempt(run_id, cancel_run.attempt_version)
    cancel_session.close()

    assert cancel_res is True

    # Finalizer tries to claim
    finalize_session = get_session(database_url)
    finalize_svc = ExecutionAttemptTransitionService(finalize_session)
    run = finalize_session.get(ExecutionRunRecord, run_id)
    claim_res = finalize_svc.claim_finalization(
        run_id,
        "finalizer-A",
        run.attempt_version,
        datetime.now(UTC) + timedelta(minutes=5),
    )
    finalize_session.close()

    assert claim_res is False, "Finalization claim should fail because the attempt was cancelled."


def test_finalization_beats_cancellation(db_session):
    database_url = str(db_session.get_bind().url)
    run_id_str = _create_admitted_run(db_session)
    from uuid import UUID

    run_id = UUID(run_id_str)

    _move_to_result_received(db_session, run_id)

    # Finalizer claims
    finalize_session = get_session(database_url)
    finalize_svc = ExecutionAttemptTransitionService(finalize_session)
    run = finalize_session.get(ExecutionRunRecord, run_id)
    claim_res = finalize_svc.claim_finalization(
        run_id,
        "finalizer-A",
        run.attempt_version,
        datetime.now(UTC) + timedelta(minutes=5),
    )
    assert claim_res is True

    run = finalize_session.get(ExecutionRunRecord, run_id)
    # Finalize records success using stage_complete_finalization + commit
    finalize_svc.stage_complete_finalization(
        execution_run_id=run_id,
        finalizer_owner_id="finalizer-A",
        finalization_fencing_epoch=run.finalization_fencing_epoch,
        attempt_version=run.attempt_version,
        final_status=ExecutionRunStatus.COMPLETED,
    )
    finalize_session.commit()
    finalize_session.close()

    # Cancel tries to run
    cancel_session = get_session(database_url)
    cancel_svc = ExecutionAttemptTransitionService(cancel_session)
    run_for_cancel = cancel_session.get(ExecutionRunRecord, run_id)
    cancel_res = cancel_svc.cancel_attempt(run_id, run_for_cancel.attempt_version)
    cancel_session.close()

    assert cancel_res is False, "Cancellation should fail because the attempt is already finalized."


def test_stale_finalizer_is_fenced_after_reclaim(db_session):
    database_url = str(db_session.get_bind().url)
    run_id_str = _create_admitted_run(db_session)
    from uuid import UUID

    run_id = UUID(run_id_str)

    _move_to_result_received(db_session, run_id)

    # Finalizer A claims but expires
    session_a = get_session(database_url)
    svca = ExecutionAttemptTransitionService(session_a)
    run = session_a.get(ExecutionRunRecord, run_id)
    claim_a = svca.claim_finalization(
        run_id,
        "finalizer-A",
        run.attempt_version,
        datetime.now(UTC) - timedelta(minutes=1),
    )
    assert claim_a is True
    run_a = session_a.get(ExecutionRunRecord, run_id)
    epoch_a = run_a.finalization_fencing_epoch
    version_a = run_a.attempt_version
    session_a.close()  # Return to pool, we can still use epoch_a logically

    # Finalizer B claims (reclaim)
    session_b = get_session(database_url)
    svcb = ExecutionAttemptTransitionService(session_b)
    run = session_b.get(ExecutionRunRecord, run_id)
    claim_b = svcb.claim_finalization(
        run_id,
        "finalizer-B",
        run.attempt_version,
        datetime.now(UTC) + timedelta(minutes=5),
    )
    assert claim_b is True
    run_b = session_b.get(ExecutionRunRecord, run_id)
    epoch_b = run_b.finalization_fencing_epoch
    version_b = run_b.attempt_version
    assert epoch_b > epoch_a

    # Finalizer A wakes up and tries to record success
    session_a_wake = get_session(database_url)
    svca_wake = ExecutionAttemptTransitionService(session_a_wake)
    res_a = svca_wake.stage_complete_finalization(
        execution_run_id=run_id,
        finalizer_owner_id="finalizer-A",
        finalization_fencing_epoch=epoch_a,
        attempt_version=version_a,
        final_status=ExecutionRunStatus.COMPLETED,
    )
    if res_a:
        session_a_wake.commit()
    session_a_wake.close()

    assert res_a is False, "Stale finalizer must be fenced out."

    # Finalizer B can still succeed
    res_b = svcb.stage_complete_finalization(
        execution_run_id=run_id,
        finalizer_owner_id="finalizer-B",
        finalization_fencing_epoch=epoch_b,
        attempt_version=version_b,
        final_status=ExecutionRunStatus.COMPLETED,
    )
    if res_b:
        session_b.commit()
    session_b.close()

    assert res_b is True, "Valid finalizer should succeed."
