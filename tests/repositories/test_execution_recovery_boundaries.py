"""Focused regression tests for durable execution-attempt boundaries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import inspect, text

from application.orchestrator.transition_service import ExecutionAttemptTransitionService
from db.init_db import init_db
from db.models import DataProfileRecord, ExecutionRunRecord, HypothesisRecord, TaskRecord
from db.session import create_db_engine, get_session
from schemas.enums import ExecutionRunStatus


def test_lease_claim_and_renewal_fence_stale_owners(db_session) -> None:
    """Independent connections cannot both own or renew one attempt lease."""

    from uuid import uuid4

    from application.orchestrator.transition_service import ExecutionAttemptTransitionService

    first_svc = ExecutionAttemptTransitionService(db_session)
    run_id = uuid4()

    from db.models import DataProfileRecord, HypothesisRecord, TaskRecord

    profile_id = uuid4()
    task_id = uuid4()
    hypothesis_id = uuid4()
    db_session.add(
        DataProfileRecord(
            profile_id=profile_id,
            dataset_path="test",
            dvc_hash="test",
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
    db_session.commit()

    run_id = uuid4()

    run = first_svc.admit_attempt(
        execution_run_id=run_id,
        task_id=task_id,
        hypothesis_id=hypothesis_id,
        executor_type="test",
        method_id="test",
        parameter_hash="test",
        dispatch_idempotency_key="key",
        prepared_payload={},
    )

    database_url = str(db_session.get_bind().url)
    first_session = get_session(database_url)
    second_session = get_session(database_url)
    try:
        first_svc = ExecutionAttemptTransitionService(first_session)

        first = first_svc.claim_dispatch(
            run.execution_run_id,
            "worker-a",
            expires_at=datetime.now(UTC) + timedelta(minutes=1),
        )

        # second claim fails due to version/epoch
        second = first_svc.claim_dispatch(
            run.execution_run_id,
            "worker-b",
            expires_at=datetime.now(UTC) + timedelta(minutes=1),
        )

        assert first is not None
        assert first.lease_epoch == 1
        assert second is None

        # worker-b reclaims after expire
        assert first_svc.expire_or_release_attempt(
            run.execution_run_id,
            first.attempt_version,
            now=datetime.now(UTC) + timedelta(minutes=2),
        )

        reclaimed = first_svc.claim_dispatch(
            run.execution_run_id,
            "worker-b",
            expires_at=datetime.now(UTC) + timedelta(minutes=3),
        )
        assert reclaimed is not None
        assert reclaimed.lease_epoch == 2

    finally:
        first_session.close()
        second_session.close()


def test_init_db_upgrades_a_prior_execution_runs_table_without_create_all_migration(
    tmp_path,
) -> None:
    """The upgrade covers every committed pre-protocol ExecutionRun layout."""

    database_url = f"sqlite:///{(tmp_path / 'legacy.sqlite3').as_posix()}"
    engine = create_db_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE execution_runs ("
                "execution_run_id CHAR(32) PRIMARY KEY, "
                "task_id CHAR(32), hypothesis_id CHAR(32), analysis_frame_id CHAR(32), "
                "executor_type VARCHAR, method_id VARCHAR, parameter_hash VARCHAR, "
                "status VARCHAR NOT NULL, "
                "created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO execution_runs "
                "(execution_run_id, task_id, hypothesis_id, analysis_frame_id, executor_type, "
                "method_id, parameter_hash, status, created_at) VALUES "
                "('legacy-incomplete', 'legacy-task', 'legacy-hypothesis', NULL, 'legacy', "
                "'method', 'parameters', 'running', '2026-07-14 00:00:00'), "
                "('legacy-completed', 'legacy-task', 'legacy-hypothesis', NULL, 'legacy', "
                "'method', 'parameters', 'completed', '2026-07-14 00:00:00')"
            )
        )

    init_db(database_url)
    init_db(database_url)
    inspector = inspect(create_db_engine(database_url))
    columns = {column["name"] for column in inspector.get_columns("execution_runs")}
    assert {
        "dispatch_idempotency_key",
        "worker_id",
        "lease_epoch",
        "attempt_version",
        "finalization_fencing_epoch",
        "previous_attempt_id",
    } <= columns
    indexes = {index["name"] for index in inspector.get_indexes("execution_runs")}
    assert {
        "ix_execution_runs_status",
        "ix_execution_runs_dispatch_idempotency_key",
        "ix_execution_runs_hypothesis_id",
    } <= indexes
    assert {"execution_approvals", "execution_outbox", "execution_inbox"} <= set(
        inspector.get_table_names()
    )
    with create_db_engine(database_url).connect() as connection:
        statuses = dict(
            connection.execute(text("SELECT execution_run_id, status FROM execution_runs")).all()
        )
    assert statuses["legacy-incomplete"] == ExecutionRunStatus.ABANDONED.value
    assert statuses["legacy-completed"] == ExecutionRunStatus.COMPLETED.value

    session = get_session(database_url)
    try:
        profile_id, task_id, hypothesis_id, run_id = (uuid4() for _ in range(4))
        session.add(
            DataProfileRecord(
                profile_id=profile_id,
                dataset_path="upgraded-test",
                dvc_hash="test",
                schema_summary={"column_order": []},
                baseline_summary={"column_names": []},
                row_count=0,
                column_count=0,
                method="baseline_summary",
            )
        )
        session.flush()
        session.add(
            TaskRecord(
                task_id=task_id,
                profile_id=profile_id,
                title="upgraded test",
                description="test",
                variables=[],
                task_kind="analytical",
            )
        )
        session.flush()
        session.add(
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
        session.flush()
        service = ExecutionAttemptTransitionService(session)
        service.admit_attempt(
            execution_run_id=run_id,
            task_id=task_id,
            hypothesis_id=hypothesis_id,
            executor_type="test",
            method_id="test",
            parameter_hash="test",
            dispatch_idempotency_key="upgrade-key",
            prepared_payload={},
        )
        claimed = service.claim_dispatch(
            run_id,
            "worker",
            datetime.now(UTC) + timedelta(minutes=1),
        )
        assert claimed is not None
        assert service.mark_running(run_id, "worker", claimed.lease_epoch)
        assert service.accept_authoritative_result(
            execution_run_id=run_id,
            dispatch_idempotency_key="upgrade-key",
            worker_id="worker",
            lease_epoch=claimed.lease_epoch,
            result_digest="upgrade-result",
            executor_status="completed",
            serialized_observations={},
            error_message=None,
            method_id="test",
            producer_identity="worker",
        )
        received = session.get(ExecutionRunRecord, run_id)
        assert service.claim_finalization(
            run_id,
            "finalizer",
            received.attempt_version,
            datetime.now(UTC) + timedelta(minutes=1),
        )
        finalizing = session.get(ExecutionRunRecord, run_id)
        assert service.stage_complete_finalization(
            execution_run_id=run_id,
            finalizer_owner_id="finalizer",
            finalization_fencing_epoch=finalizing.finalization_fencing_epoch,
            attempt_version=finalizing.attempt_version,
        )
        session.commit()
        assert session.get(ExecutionRunRecord, run_id).status == ExecutionRunStatus.COMPLETED
    finally:
        session.close()
