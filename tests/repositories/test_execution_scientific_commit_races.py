"""Concurrency and race condition tests at the scientific-commit boundary."""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from agents.planner.types import (
    AnalysisFrameObservation,
    EvidenceObservation,
    PreparedExecution,
)
from application.orchestrator.cancellation import cancel_execution_attempt
from application.orchestrator.execution_contracts import ExecutionReceiptEnvelope
from application.orchestrator.execution_identity import (
    method_parameter_hash,
    result_payload_digest,
)
from application.orchestrator.finalizer import finalize_attempt
from application.orchestrator.receiver import submit_execution_result
from application.orchestrator.transition_service import (
    AlreadyCompletedError,
    AlreadyFinalizingError,
    ClaimLostError,
    ExecutionAttemptTransitionService,
)
from db.models import (
    AnalysisFrameRecord,
    DataProfileRecord,
    DiscoveryRecord,
    EvidenceRecord,
    ExecutionInboxRecord,
    ExecutionOutboxRecord,
    ExecutionRunRecord,
    HypothesisRecord,
    PlannerOperationRecord,
    SessionFrameRecord,
    TaskRecord,
)
from db.session import get_session
from schemas.common import EvidenceResultSummary, MethodParameter
from schemas.enums import (
    AnalysisIntent,
    DataProfileLifecycleState,
    DataProfileMethod,
    EvidenceType,
    ExecutionRunStatus,
    HypothesisStatus,
    TaskKind,
    TaskLifecycleState,
)

logger = logging.getLogger(__name__)


def _assert_sqlite_concurrency_config(session: Session) -> None:
    """Prove every independent test connection uses production SQLite settings."""

    assert session.execute(text("PRAGMA journal_mode")).scalar_one().lower() == "wal"
    assert session.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000


def _setup_attempt_for_finalization(
    db_session: Session,
    run_id: UUID,
    *,
    admit_result: bool = True,
    p_value: float = 0.01,
) -> tuple[UUID, UUID, UUID, ExecutionReceiptEnvelope]:
    profile_id = uuid4()
    task_id = uuid4()
    hypothesis_id = uuid4()

    db_session.add(
        DataProfileRecord(
            profile_id=profile_id,
            dataset_path="test_dataset.csv",
            dvc_hash="dvc-hash-123",
            schema_summary={"column_order": ["x", "y"]},
            baseline_summary={"column_names": ["x", "y"]},
            row_count=100,
            column_count=2,
            method=DataProfileMethod.BASELINE_SUMMARY,
            lifecycle_state=DataProfileLifecycleState.ACTIVE,
            accepted_as_ground_truth=True,
        )
    )
    db_session.flush()
    db_session.add(
        TaskRecord(
            task_id=task_id,
            profile_id=profile_id,
            title="Statistical Association Task",
            description="Test association between X and Y",
            intent=AnalysisIntent.EXPLORATORY,
            kind=TaskKind.ANALYTICAL,
            variables=["x", "y"],
            evidence_expectation="p_value < 0.05",
            status=TaskLifecycleState.ACTIVE,
        )
    )
    db_session.flush()
    db_session.add(
        HypothesisRecord(
            hypothesis_id=hypothesis_id,
            task_id=task_id,
            profile_id=profile_id,
            statement="X is associated with Y.",
            variables=["x", "y"],
            scope="test scope",
            validation_method="deterministic_test",
            evidence_expectation="p_value < 0.05",
            status=HypothesisStatus.TESTING,
        )
    )
    db_session.flush()
    db_session.commit()

    params = [MethodParameter(name="alpha", value=0.05)]
    param_hash = method_parameter_hash(params)

    prepared = PreparedExecution(
        task_ref=str(task_id),
        data_profile_ref=str(profile_id),
        task_title="Statistical Association Task",
        dataset_path="test_dataset.csv",
        hypothesis={
            "statement": "X is associated with Y.",
            "variables": ["x", "y"],
            "scope": "test scope",
            "validation_method": "deterministic_test",
            "evidence_expectation": "p_value < 0.05",
        },
        specification={
            "claim_type": "association",
            "variable_bindings": ["x", "y"],
            "scope": "test scope",
            "evidence_expectation": "p_value < 0.05",
            "decision_rule": {"p_value": 0.05},
            "validation_method": "deterministic_test",
            "executor_id": "regression_executor",
            "method_parameters": [{"name": "alpha", "value": 0.05}],
        },
        contract_fingerprint="fingerprint-123",
    )

    from schemas.data_explorer_contracts import DataExplorerSuccessResult

    dx_result = DataExplorerSuccessResult(
        status="success",
        analysis_frame=AnalysisFrameObservation(
            frame_hash="frame-hash-123",
            column_refs=["x", "y"],
        ),
        evidence_observation=EvidenceObservation(
            evidence_type=EvidenceType.STATISTICAL_TEST,
            method="deterministic_test",
            parameters=params,
            result_summary=EvidenceResultSummary(
                summary=f"Observed p_value: {p_value}.",
                key_findings=["p_value was observed"],
                metric_name="p_value",
                metric_value=p_value,
            ),
            code_reference="tests/repositories/test_execution_scientific_commit_races.py",
        ),
    )
    transition_service = ExecutionAttemptTransitionService(db_session)
    transition_service.admit_attempt(
        execution_run_id=run_id,
        task_id=task_id,
        hypothesis_id=hypothesis_id,
        analysis_frame_id=None,
        executor_type="regression_executor",
        method_id="deterministic_test",
        parameter_hash=param_hash,
        dispatch_idempotency_key="idempotency-key-123",
        prepared_payload=prepared.model_dump(),
    )

    claimed = transition_service.claim_dispatch(
        run_id,
        "worker-123",
        datetime.now(UTC) + timedelta(minutes=5),
    )
    assert claimed is not None
    assert transition_service.mark_running(run_id, "worker-123", claimed.lease_epoch)
    durable_prepared = prepared.model_copy(
        update={
            "task_ref": str(task_id),
            "data_profile_ref": str(profile_id),
            "hypothesis_ref": str(hypothesis_id),
            "execution_run_id": run_id,
            "execution_run_ref": str(run_id),
            "dispatch_idempotency_key": "idempotency-key-123",
            "lease_epoch": claimed.lease_epoch,
        }
    )
    current_run = db_session.get(ExecutionRunRecord, run_id)
    current_outbox = db_session.exec(
        select(ExecutionOutboxRecord).where(ExecutionOutboxRecord.execution_run_id == run_id)
    ).one()
    current_outbox.prepared_payload = durable_prepared.model_dump(mode="json")
    db_session.add(current_outbox)
    db_session.flush()
    assert current_run is not None

    receipt = dx_result

    if admit_result:
        serialized_result = receipt.model_dump(mode="json")
        inbox = transition_service.accept_authoritative_result(
            execution_run_id=run_id,
            dispatch_idempotency_key="idempotency-key-123",
            worker_id="worker-123",
            lease_epoch=claimed.lease_epoch,
            result_digest=result_payload_digest(serialized_result),
            executor_status="completed",
            serialized_observations=serialized_result,
            error_message=None,
            method_id="deterministic_test",
            producer_identity="worker-123",
        )
        assert inbox is not None

    return run_id, hypothesis_id, task_id, receipt


def test_p_values_on_both_sides_of_threshold_have_identical_lifecycle(db_session: Session) -> None:
    attempts = [
        _setup_attempt_for_finalization(db_session, uuid4(), p_value=p_value)
        for p_value in (0.01, 0.9)
    ]
    db_session.commit()

    for run_id, _, _, _ in attempts:
        assert finalize_attempt(db_session, run_id) is True

    for run_id, hypothesis_id, task_id, _ in attempts:
        run = db_session.get(ExecutionRunRecord, run_id)
        hypothesis = db_session.get(HypothesisRecord, hypothesis_id)
        task = db_session.get(TaskRecord, task_id)
        assert run is not None and run.status == ExecutionRunStatus.EVIDENCE_ADMITTED
        assert hypothesis is not None
        assert hypothesis.status == HypothesisStatus.READY_FOR_EVALUATION
        assert task is not None and task.lifecycle_state == TaskLifecycleState.ACTIVE
        assert (
            db_session.exec(
                select(DiscoveryRecord).where(DiscoveryRecord.hypothesis_id == hypothesis_id)
            ).all()
            == []
        )


def test_concurrent_identical_result_admission_is_idempotent(db_session: Session) -> None:
    """Separate receiver transactions admit one authoritative identical result."""

    database_url = str(db_session.get_bind().url)
    run_id, _, _, result = _setup_attempt_for_finalization(db_session, uuid4(), admit_result=False)
    db_session.commit()
    run = db_session.get(ExecutionRunRecord, run_id)
    assert run is not None
    barrier = threading.Barrier(2)
    outcomes: list[tuple[object | None, Exception | None]] = []

    def receiver_worker() -> None:
        session = get_session(database_url)
        try:
            _assert_sqlite_concurrency_config(session)
            # Establish an independent ORM transaction before synchronizing.
            assert session.get(ExecutionRunRecord, run_id) is not None
            barrier.wait(timeout=5.0)
            outcomes.append(
                (
                    submit_execution_result(
                        session,
                        run_id,
                        "idempotency-key-123",
                        run.lease_epoch,
                        "worker-123",
                        "deterministic_test",
                        "completed",
                        result,
                    ),
                    None,
                )
            )
        except Exception as exc:
            outcomes.append((None, exc))
        finally:
            session.close()

    threads = [threading.Thread(target=receiver_worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert [error for _, error in outcomes] == [None, None]
    fresh = get_session(database_url)
    try:
        inboxes = fresh.exec(
            select(ExecutionInboxRecord).where(ExecutionInboxRecord.execution_run_id == run_id)
        ).all()
        assert len(inboxes) == 1
        assert inboxes[0].status == "pending"
        assert fresh.get(ExecutionRunRecord, run_id).status == ExecutionRunStatus.RESULT_RECEIVED
    finally:
        fresh.close()


def test_concurrent_conflicting_result_admission_quarantines_attempt(db_session: Session) -> None:
    """Competing receiver transactions retain both envelopes and block finalization."""

    database_url = str(db_session.get_bind().url)
    run_id, _, _, result = _setup_attempt_for_finalization(db_session, uuid4(), admit_result=False)
    db_session.commit()
    run = db_session.get(ExecutionRunRecord, run_id)
    assert run is not None
    conflicting_result = result.model_copy(
        update={
            "evidence_observation": result.evidence_observation.model_copy(
                update={
                    "result_summary": result.evidence_observation.result_summary.model_copy(
                        update={"metric_value": 0.02}
                    )
                }
            )
        }
    )
    barrier = threading.Barrier(2)
    outcomes: list[tuple[object | None, Exception | None]] = []

    def receiver_worker(payload: ExecutionReceiptEnvelope) -> None:
        session = get_session(database_url)
        try:
            _assert_sqlite_concurrency_config(session)
            assert session.get(ExecutionRunRecord, run_id) is not None
            barrier.wait(timeout=5.0)
            outcomes.append(
                (
                    submit_execution_result(
                        session,
                        run_id,
                        "idempotency-key-123",
                        run.lease_epoch,
                        "worker-123",
                        "deterministic_test",
                        "completed",
                        payload,
                    ),
                    None,
                )
            )
        except Exception as exc:
            outcomes.append((None, exc))
        finally:
            session.close()

    threads = [
        threading.Thread(target=receiver_worker, args=(result,)),
        threading.Thread(target=receiver_worker, args=(conflicting_result,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert [error for _, error in outcomes] == [None, None]
    assert sum(outcome is not None for outcome, _ in outcomes) == 1
    fresh = get_session(database_url)
    try:
        inboxes = fresh.exec(
            select(ExecutionInboxRecord).where(ExecutionInboxRecord.execution_run_id == run_id)
        ).all()
        assert {inbox.status for inbox in inboxes} == {"pending", "conflict"}
        assert len(inboxes) == 2
        assert fresh.get(ExecutionRunRecord, run_id).status == ExecutionRunStatus.RESULT_CONFLICT
        with pytest.raises(ClaimLostError):
            finalize_attempt(fresh, run_id, finalizer_owner_id="must-not-finalize")
    finally:
        fresh.close()


def test_concurrent_full_finalizer_invocation_races_claim(db_session: Session) -> None:
    database_url = str(db_session.get_bind().url)
    run_id = uuid4()
    _setup_attempt_for_finalization(db_session, run_id)
    db_session.commit()

    barrier = threading.Barrier(2)
    thread_results: list[Any] = []

    def finalizer_worker(worker_id: str) -> None:
        session = get_session(database_url)
        _assert_sqlite_concurrency_config(session)
        try:

            def test_hook(event: str, sess: Session) -> None:
                if event == "before_claim":
                    barrier.wait(timeout=5.0)

            res = finalize_attempt(
                session, run_id, finalizer_owner_id=worker_id, test_hook=test_hook
            )
            thread_results.append((worker_id, res, None))
        except Exception as exc:
            thread_results.append((worker_id, False, exc))
        finally:
            session.close()

    t1 = threading.Thread(target=finalizer_worker, args=("finalizer-A",))
    t2 = threading.Thread(target=finalizer_worker, args=("finalizer-B",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Assertions
    successes = [r for r in thread_results if r[1] is True]
    failures = [r for r in thread_results if r[1] is False]

    assert len(successes) == 1, "Exactly one finalizer must succeed."
    assert len(failures) == 1, "Exactly one finalizer must fail."

    loser_exc = failures[0][2]
    assert loser_exc is not None, "Loser must throw an exception."
    assert isinstance(loser_exc, (AlreadyFinalizingError, AlreadyCompletedError, ClaimLostError))

    # fresh session validation
    fresh_session = get_session(database_url)
    _assert_sqlite_concurrency_config(fresh_session)
    try:
        run = fresh_session.get(ExecutionRunRecord, run_id)
        assert run is not None
        assert run.status == ExecutionRunStatus.EVIDENCE_ADMITTED

        # Ensure scientific writes are created exactly once
        hyp_id = run.hypothesis_id
        hyp = fresh_session.get(HypothesisRecord, hyp_id)
        assert hyp is not None

        evidences = fresh_session.exec(
            select(EvidenceRecord).where(EvidenceRecord.hypothesis_id == hyp_id)
        ).all()
        assert len(evidences) == 1

        discoveries = fresh_session.exec(
            select(DiscoveryRecord).where(DiscoveryRecord.hypothesis_id == hyp_id)
        ).all()
        assert len(discoveries) == 0

        frames = fresh_session.exec(
            select(AnalysisFrameRecord).where(AnalysisFrameRecord.data_profile_id == hyp.profile_id)
        ).all()
        assert len(frames) == 1

        inbox = fresh_session.exec(
            select(ExecutionInboxRecord).where(ExecutionInboxRecord.execution_run_id == run_id)
        ).first()
        assert inbox is not None
        assert inbox.status == "processed"

        outbox = fresh_session.exec(
            select(ExecutionOutboxRecord).where(ExecutionOutboxRecord.execution_run_id == run_id)
        ).first()
        assert outbox is not None
        assert outbox.status == "processed"

        # Replay should be idempotent and return True without duplicates
        assert finalize_attempt(fresh_session, run_id, finalizer_owner_id="finalizer-C") is True
        assert (
            len(
                fresh_session.exec(
                    select(EvidenceRecord).where(EvidenceRecord.hypothesis_id == hyp_id)
                ).all()
            )
            == 1
        )
    finally:
        fresh_session.close()


def test_cancellation_wins_against_finalization(db_session: Session) -> None:
    database_url = str(db_session.get_bind().url)
    run_id = uuid4()
    _setup_attempt_for_finalization(db_session, run_id)
    db_session.commit()

    finalizer_ready = threading.Event()
    canceller_done = threading.Event()
    thread_results: list[Any] = []

    def finalizer_worker() -> None:
        session = get_session(database_url)
        _assert_sqlite_concurrency_config(session)
        try:

            def test_hook(event: str, sess: Session) -> None:
                if event == "before_claim":
                    finalizer_ready.set()
                    assert canceller_done.wait(timeout=5.0)

            res = finalize_attempt(
                session, run_id, finalizer_owner_id="finalizer-A", test_hook=test_hook
            )
            thread_results.append(("finalizer", res, None))
        except Exception as exc:
            thread_results.append(("finalizer", False, exc))
        finally:
            session.close()

    def canceller_worker() -> None:
        session = get_session(database_url)
        _assert_sqlite_concurrency_config(session)
        try:
            assert finalizer_ready.wait(timeout=5.0)
            res = cancel_execution_attempt(session, run_id)
            thread_results.append(("canceller", res, None))
        except Exception as exc:
            thread_results.append(("canceller", False, exc))
        finally:
            canceller_done.set()
            session.close()

    t1 = threading.Thread(target=finalizer_worker)
    t2 = threading.Thread(target=canceller_worker)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Assertions
    canceller_res = [r for r in thread_results if r[0] == "canceller"][0]
    finalizer_res = [r for r in thread_results if r[0] == "finalizer"][0]

    assert canceller_res[1] is True, "Canceller should successfully win the race."
    assert finalizer_res[1] is False, "Finalizer must fail the claim."
    assert isinstance(finalizer_res[2], ClaimLostError)

    # fresh session validation
    fresh_session = get_session(database_url)
    _assert_sqlite_concurrency_config(fresh_session)
    try:
        run = fresh_session.get(ExecutionRunRecord, run_id)
        assert run is not None
        assert run.status == ExecutionRunStatus.CANCELLED

        # Cancellation retains attempt provenance without creating scientific state.
        frames = fresh_session.exec(select(AnalysisFrameRecord)).all()
        evidences = fresh_session.exec(
            select(EvidenceRecord).where(EvidenceRecord.hypothesis_id == run.hypothesis_id)
        ).all()
        discoveries = fresh_session.exec(
            select(DiscoveryRecord).where(DiscoveryRecord.hypothesis_id == run.hypothesis_id)
        ).all()
        session_frames = fresh_session.exec(select(SessionFrameRecord)).all()
        inbox = fresh_session.exec(
            select(ExecutionInboxRecord).where(ExecutionInboxRecord.execution_run_id == run_id)
        ).one()
        task = fresh_session.get(TaskRecord, run.task_id)
        hypothesis = fresh_session.get(HypothesisRecord, run.hypothesis_id)

        assert frames == []
        assert evidences == []
        assert discoveries == []
        assert session_frames == []
        assert inbox.status == "cancelled"
        assert inbox.processed_at is not None
        assert task is not None and task.lifecycle_state == TaskLifecycleState.ACTIVE
        assert hypothesis is not None
        assert hypothesis.status not in {
            HypothesisStatus.EVALUATED,
            HypothesisStatus.FAILED,
            HypothesisStatus.CANCELLED,
            HypothesisStatus.ARCHIVED,
        }

        # Repeated cancellation is idempotent and returns True
        assert cancel_execution_attempt(fresh_session, run_id) is True
    finally:
        fresh_session.close()


def test_finalization_wins_against_cancellation(db_session: Session) -> None:
    database_url = str(db_session.get_bind().url)
    run_id = uuid4()
    _setup_attempt_for_finalization(db_session, run_id)
    db_session.commit()

    finalizer_claimed = threading.Event()
    canceller_done = threading.Event()
    thread_results: list[Any] = []

    def finalizer_worker() -> None:
        session = get_session(database_url)
        _assert_sqlite_concurrency_config(session)
        try:

            def test_hook(event: str, sess: Session) -> None:
                if event in {"before_complete", "before_commit"}:
                    finalizer_claimed.set()
                    assert canceller_done.wait(timeout=5.0)

            res = finalize_attempt(
                session, run_id, finalizer_owner_id="finalizer-A", test_hook=test_hook
            )
            thread_results.append(("finalizer", res, None))
        except Exception as exc:
            thread_results.append(("finalizer", False, exc))
        finally:
            session.close()

    def canceller_worker() -> None:
        session = get_session(database_url)
        _assert_sqlite_concurrency_config(session)
        try:
            # Let the finalizer claim the attempt first, setting it to FINALIZING
            assert finalizer_claimed.wait(timeout=5.0)
            res = cancel_execution_attempt(session, run_id)
            thread_results.append(("canceller", res, None))
        except Exception as exc:
            thread_results.append(("canceller", False, exc))
        finally:
            canceller_done.set()
            session.close()

    t1 = threading.Thread(target=finalizer_worker)
    t2 = threading.Thread(target=canceller_worker)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Assertions
    canceller_res = [r for r in thread_results if r[0] == "canceller"][0]
    finalizer_res = [r for r in thread_results if r[0] == "finalizer"][0]

    assert finalizer_res[1] is True, "Finalizer must successfully win and commit."
    assert canceller_res[1] is False, "Canceller must fail."
    assert isinstance(canceller_res[2], AlreadyFinalizingError)

    # fresh session validation
    fresh_session = get_session(database_url)
    _assert_sqlite_concurrency_config(fresh_session)
    try:
        run = fresh_session.get(ExecutionRunRecord, run_id)
        assert run is not None
        assert run.status == ExecutionRunStatus.EVIDENCE_ADMITTED

        # Evidence exists
        evidences = fresh_session.exec(
            select(EvidenceRecord).where(EvidenceRecord.hypothesis_id == run.hypothesis_id)
        ).all()
        assert len(evidences) == 1

        # Subsequent cancellation fails with AlreadyCompletedError
        with pytest.raises(AlreadyCompletedError):
            cancel_execution_attempt(fresh_session, run_id)
    finally:
        fresh_session.close()


def test_stale_finalizer_is_fenced_after_reclaim(db_session: Session) -> None:
    database_url = str(db_session.get_bind().url)
    run_id = uuid4()
    _setup_attempt_for_finalization(db_session, run_id)
    db_session.commit()

    barrier_a = threading.Barrier(2)
    barrier_b = threading.Barrier(2)
    thread_results: list[Any] = []

    def finalizer_a_worker() -> None:
        session = get_session(database_url)
        _assert_sqlite_concurrency_config(session)
        try:

            def test_hook(event: str, sess: Session) -> None:
                if event == "before_complete":
                    # Wait for test to manually expire the lease
                    barrier_a.wait(timeout=5.0)
                    # Wait for B to claim and commit
                    barrier_b.wait(timeout=5.0)

            res = finalize_attempt(
                session, run_id, finalizer_owner_id="finalizer-A", test_hook=test_hook
            )
            thread_results.append(("finalizer-A", res, None))
        except Exception as exc:
            thread_results.append(("finalizer-A", False, exc))
        finally:
            session.close()

    t1 = threading.Thread(target=finalizer_a_worker)
    t1.start()

    # Let A claim finalization and pause at before_complete
    barrier_a.wait(timeout=5.0)

    # Expire A's claim manually in a separate controller session
    controller_session = get_session(database_url)
    _assert_sqlite_concurrency_config(controller_session)
    try:
        run = controller_session.get(ExecutionRunRecord, run_id)
        assert run is not None
        assert run.status == ExecutionRunStatus.EVIDENCE_ADMITTING
        assert run.finalizer_owner_id == "finalizer-A"

        # Backdate the claim expiry
        run.finalization_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        controller_session.add(run)
        controller_session.commit()
    finally:
        controller_session.close()

    # Now let Finalizer B run to completion
    session_b = get_session(database_url)
    _assert_sqlite_concurrency_config(session_b)
    try:
        res_b = finalize_attempt(session_b, run_id, finalizer_owner_id="finalizer-B")
        thread_results.append(("finalizer-B", res_b, None))
    except Exception as exc:
        thread_results.append(("finalizer-B", False, exc))
    finally:
        session_b.close()

    # Release finalizer A to attempt its write with stale owner/epoch/version
    barrier_b.wait(timeout=5.0)
    t1.join()

    # Assertions
    res_a = [r for r in thread_results if r[0] == "finalizer-A"][0]
    res_b = [r for r in thread_results if r[0] == "finalizer-B"][0]

    assert res_b[1] is True, "Finalizer B should have committed successfully."
    assert res_a[1] is False, "Finalizer A must have failed and returned False."

    # fresh session validation
    fresh_session = get_session(database_url)
    _assert_sqlite_concurrency_config(fresh_session)
    try:
        run = fresh_session.get(ExecutionRunRecord, run_id)
        assert run is not None
        assert run.status == ExecutionRunStatus.EVIDENCE_ADMITTED
        assert run.finalizer_owner_id == "finalizer-B"

        # Evidence and Discovery exist exactly once (from B)
        evidences = fresh_session.exec(
            select(EvidenceRecord).where(EvidenceRecord.hypothesis_id == run.hypothesis_id)
        ).all()
        assert len(evidences) == 1
    finally:
        fresh_session.close()


@pytest.mark.parametrize(
    "failure_event",
    [
        "after_analysis_frame",
        "after_evidence",
        "after_run_transition",
        "after_hypothesis_transition",
        "after_inbox_consumption",
        "before_commit",
    ],
)
def test_finalization_rollback_after_each_staged_component_and_eventual_retry(
    db_session: Session,
    failure_event: str,
) -> None:
    database_url = str(db_session.get_bind().url)
    run_id = uuid4()
    run_id, hypothesis_id, task_id, _ = _setup_attempt_for_finalization(db_session, run_id)
    db_session.commit()

    # Inject after every staged component and at the final pre-commit boundary.
    session_a = get_session(database_url)
    _assert_sqlite_concurrency_config(session_a)
    try:

        def test_hook(event: str, sess: Session) -> None:
            if event == failure_event:
                raise RuntimeError(f"Injected transaction failure after {failure_event}")

        with pytest.raises(RuntimeError, match="Injected transaction failure"):
            finalize_attempt(
                session_a, run_id, finalizer_owner_id="finalizer-A", test_hook=test_hook
            )
    finally:
        session_a.close()

    # Assert scientific transaction fully rolled back
    fresh_session = get_session(database_url)
    _assert_sqlite_concurrency_config(fresh_session)
    try:
        # Run state remains FINALIZING (since claim was committed, but final commit rolled back)
        # inbox status must still be pending because transaction rolled back
        inbox = fresh_session.exec(
            select(ExecutionInboxRecord).where(ExecutionInboxRecord.execution_run_id == run_id)
        ).first()
        assert inbox is not None
        assert inbox.status == "pending"

        # No scientific artifact, lifecycle change, frame, or operation survives rollback.
        frames = fresh_session.exec(select(AnalysisFrameRecord)).all()
        evidences = fresh_session.exec(
            select(EvidenceRecord).where(EvidenceRecord.hypothesis_id == hypothesis_id)
        ).all()
        discoveries = fresh_session.exec(
            select(DiscoveryRecord).where(DiscoveryRecord.hypothesis_id == hypothesis_id)
        ).all()
        session_frames = fresh_session.exec(select(SessionFrameRecord)).all()
        operations = fresh_session.exec(select(PlannerOperationRecord)).all()
        task = fresh_session.get(TaskRecord, task_id)
        hypothesis = fresh_session.get(HypothesisRecord, hypothesis_id)

        assert frames == []
        assert evidences == []
        assert discoveries == []
        assert session_frames == []
        assert operations == []
        assert task is not None and task.lifecycle_state == "active"
        assert hypothesis is not None and hypothesis.status == "testing"

        # Now, since the claim is active, a replacement finalizer needs
        # to wait for expiry or reclaim.
        # Let's backdate the claim to make it reclaimable
        run = fresh_session.get(ExecutionRunRecord, run_id)
        assert run is not None
        run.finalization_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        fresh_session.add(run)
        fresh_session.commit()

        # Retry finalization with a fresh finalizer
        session_b = get_session(database_url)
        _assert_sqlite_concurrency_config(session_b)
        try:
            assert finalize_attempt(session_b, run_id, finalizer_owner_id="finalizer-B") is True
        finally:
            session_b.close()

        # Verify retry is successful and the complete scientific transaction is committed once.
        fresh_session.refresh(run)
        assert run.status == ExecutionRunStatus.EVIDENCE_ADMITTED
        assert run.finalizer_owner_id == "finalizer-B"

        inbox = fresh_session.exec(
            select(ExecutionInboxRecord).where(ExecutionInboxRecord.execution_run_id == run_id)
        ).one()
        frames = fresh_session.exec(select(AnalysisFrameRecord)).all()
        evidences = fresh_session.exec(
            select(EvidenceRecord).where(EvidenceRecord.hypothesis_id == run.hypothesis_id)
        ).all()
        discoveries = fresh_session.exec(
            select(DiscoveryRecord).where(DiscoveryRecord.hypothesis_id == run.hypothesis_id)
        ).all()
        session_frames = fresh_session.exec(select(SessionFrameRecord)).all()
        operations = fresh_session.exec(select(PlannerOperationRecord)).all()
        task = fresh_session.get(TaskRecord, task_id)
        hypothesis = fresh_session.get(HypothesisRecord, hypothesis_id)

        assert inbox.status == "processed"
        assert len(frames) == 1
        assert len(evidences) == 1
        assert len(discoveries) == 0
        assert len(session_frames) == 0
        assert operations == []
        assert task is not None and task.lifecycle_state == TaskLifecycleState.ACTIVE
        assert hypothesis is not None
        assert hypothesis.status == HypothesisStatus.READY_FOR_EVALUATION

        # Finalizer replay is idempotent and cannot duplicate any cardinality-bound artifact.
        assert finalize_attempt(fresh_session, run_id, finalizer_owner_id="finalizer-C") is True
        assert len(fresh_session.exec(select(AnalysisFrameRecord)).all()) == 1
        assert len(fresh_session.exec(select(EvidenceRecord)).all()) == 1
        assert len(fresh_session.exec(select(DiscoveryRecord)).all()) == 0
        assert len(fresh_session.exec(select(SessionFrameRecord)).all()) == 0
        assert fresh_session.exec(select(PlannerOperationRecord)).all() == []
    finally:
        fresh_session.close()
