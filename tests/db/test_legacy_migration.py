"""Adversarial tests for Package 6 legacy inventory and quarantine migration."""

from __future__ import annotations

from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from db.init_db import init_db
from db.legacy_migration import (
    PACKAGE6_MIGRATION_NAME,
    PACKAGE6_MIGRATION_VERSION,
    LegacyPayloadMigrator,
)
from db.models import (
    AnalysisFrameRecord,
    DataProfileRecord,
    DiscoveryRecord,
    EvidenceRecord,
    ExecutionInboxRecord,
    ExecutionRunRecord,
    HypothesisRecord,
    SessionFrameRecord,
    TaskRecord,
)
from db.session import create_db_engine, get_session
from memory.retrieval_engine import DiscoveryRetrievalEngine
from schemas.enums import (
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    EvidenceType,
    ExecutionRunStatus,
    HypothesisStatus,
    SessionFrameStatus,
    TaskKind,
    TaskLifecycleState,
    ValiditySourceState,
)
from schemas.retrieval import RetrievalRequest


def _database_url(tmp_path, name: str) -> str:
    return f"sqlite:///{(tmp_path / name).as_posix()}"


def _seed_lineage(session, *, suffix: str) -> tuple[UUID, UUID, UUID]:
    profile_id, task_id, hypothesis_id = uuid4(), uuid4(), uuid4()
    session.add(
        DataProfileRecord(
            profile_id=profile_id,
            dataset_path=f"legacy-{suffix}.csv",
            dvc_hash=f"legacy-{suffix}",
            schema_summary={"column_order": ["x"]},
            baseline_summary={"column_names": ["x"]},
            row_count=10,
            column_count=1,
            method="baseline_summary",
        )
    )
    session.flush()
    session.add(
        TaskRecord(
            task_id=task_id,
            profile_id=profile_id,
            title=f"Legacy task {suffix}",
            description="Legacy analytical task.",
            variables=["x"],
            task_kind=TaskKind.ANALYTICAL,
            lifecycle_state=TaskLifecycleState.ACTIVE,
        )
    )
    session.flush()
    session.add(
        HypothesisRecord(
            hypothesis_id=hypothesis_id,
            task_id=task_id,
            profile_id=profile_id,
            statement=f"Legacy hypothesis {suffix}",
            variables=["x"],
            scope="legacy scope",
            validation_method="legacy_method",
            evidence_expectation="A bounded observation.",
            status=HypothesisStatus.TESTING,
        )
    )
    session.flush()
    return profile_id, task_id, hypothesis_id


def _seed_run(
    session,
    *,
    task_id: UUID,
    hypothesis_id: UUID,
    suffix: str,
    status: str = "running",
) -> ExecutionRunRecord:
    run = ExecutionRunRecord(
        execution_run_id=uuid4(),
        task_id=task_id,
        hypothesis_id=hypothesis_id,
        executor_type="legacy_executor",
        method_id="legacy_method",
        parameter_hash=f"legacy-parameters-{suffix}",
        dispatch_idempotency_key=f"legacy-dispatch-{suffix}",
        status=ExecutionRunStatus.RUNNING,
    )
    session.add(run)
    session.flush()
    if status != ExecutionRunStatus.RUNNING.value:
        session.exec(
            text("UPDATE execution_runs SET status = :status WHERE execution_run_id = :run_id"),
            params={"status": status, "run_id": run.execution_run_id.hex},
        )
        session.expire(run)
    return run


def _quarantine_rows(session) -> list[tuple]:
    return list(
        session.exec(
            text(
                "SELECT source_type, source_id, reason, payload_json "
                "FROM legacy_scientific_quarantine ORDER BY quarantine_id"
            )
        ).all()
    )


def test_fresh_database_installs_exact_marker_quarantine_and_triggers(tmp_path) -> None:
    database_url = _database_url(tmp_path, "fresh.sqlite3")
    init_db(database_url)
    engine = create_db_engine(database_url)
    inspector = inspect(engine)

    assert {
        "legacy_scientific_quarantine",
        "schema_migration_markers",
    } <= set(inspector.get_table_names())
    assert {
        "legacy_scientific_quarantine_immutable_update",
        "legacy_scientific_quarantine_immutable_delete",
    } <= {
        row[0]
        for row in engine.connect().execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'trigger' AND name LIKE 'legacy_scientific_quarantine_%'"
            )
        )
    }
    with get_session(database_url) as session:
        marker = session.exec(
            text(
                "SELECT migration_name, version FROM schema_migration_markers "
                "WHERE migration_name = :name"
            ),
            params={"name": PACKAGE6_MIGRATION_NAME},
        ).one()
        assert marker == (PACKAGE6_MIGRATION_NAME, PACKAGE6_MIGRATION_VERSION)
        report = LegacyPayloadMigrator(session).inventory()
        assert report.legacy_inbox_payloads_count == 0
        assert report.partial_artifact_chains_count == 0


def test_pending_processed_authority_payloads_and_failure_placeholders_are_quarantined(
    tmp_path,
) -> None:
    database_url = _database_url(tmp_path, "inboxes.sqlite3")
    init_db(database_url)
    inbox_ids: list[UUID] = []
    original_payloads: dict[UUID, dict] = {}

    with get_session(database_url) as session:
        for suffix, inbox_status, executor_status, payload in (
            (
                "pending",
                "pending",
                "completed",
                {
                    "status": "success",
                    "analysis": {"evaluation": {"p_value": 0.01}},
                },
            ),
            (
                "processed",
                "processed",
                "completed",
                {
                    "status": "success",
                    "nested": {"target_hypothesis_status": "confirmed"},
                },
            ),
            (
                "failure",
                "pending",
                "failed",
                {},
            ),
        ):
            _, task_id, hypothesis_id = _seed_lineage(session, suffix=suffix)
            run = _seed_run(
                session,
                task_id=task_id,
                hypothesis_id=hypothesis_id,
                suffix=suffix,
            )
            inbox = ExecutionInboxRecord(
                execution_run_id=run.execution_run_id,
                dispatch_idempotency_key=run.dispatch_idempotency_key or "",
                lease_epoch=1,
                result_digest=f"legacy-digest-{suffix}",
                executor_status=executor_status,
                serialized_observations=payload,
                error_message="legacy failure" if executor_status == "failed" else None,
                method_id="legacy_method",
                status=inbox_status,
            )
            session.add(inbox)
            session.flush()
            inbox_ids.append(inbox.inbox_id)
            original_payloads[inbox.inbox_id] = payload
        session.commit()

    with get_session(database_url) as session:
        migrator = LegacyPayloadMigrator(session)
        report = migrator.inventory()
        assert report.pending_legacy_inboxes_count == 1
        assert report.processed_legacy_inboxes_count == 1
        assert report.failure_placeholders_count == 1

        first = migrator.migrate_all()
        second = migrator.migrate_all()
        assert first["inbox_migrated"] == 3
        assert second["inbox_migrated"] == 0
        for inbox_id in inbox_ids:
            inbox = session.get(ExecutionInboxRecord, inbox_id)
            assert inbox is not None
            assert inbox.status == "quarantined"
            assert inbox.serialized_observations == original_payloads[inbox_id]
            assert "QUARANTINED_PACKAGE6_LEGACY_PAYLOAD" in (inbox.error_message or "")
        assert {row[0] for row in _quarantine_rows(session)} == {"execution_inbox"}


def test_exact_observation_chain_is_preserved_but_partial_chain_is_not_promoted(
    tmp_path,
) -> None:
    database_url = _database_url(tmp_path, "upgrade.sqlite3")
    init_db(database_url)

    with get_session(database_url) as session:
        exact_profile, exact_task, exact_hypothesis = _seed_lineage(session, suffix="exact")
        exact_run = _seed_run(
            session,
            task_id=exact_task,
            hypothesis_id=exact_hypothesis,
            suffix="exact",
            status="completed",
        )
        frame = AnalysisFrameRecord(
            data_profile_id=exact_profile,
            frame_hash="legacy-exact-frame",
            column_refs=["x"],
        )
        session.add(frame)
        session.flush()
        session.exec(
            text(
                "UPDATE execution_runs SET analysis_frame_id = :frame_id "
                "WHERE execution_run_id = :run_id"
            ),
            params={
                "frame_id": frame.analysis_frame_id.hex,
                "run_id": exact_run.execution_run_id.hex,
            },
        )
        evidence = EvidenceRecord(
            hypothesis_id=exact_hypothesis,
            profile_id=exact_profile,
            analysis_frame_ref=str(frame.analysis_frame_id),
            execution_run_ref=str(exact_run.execution_run_id),
            evidence_type=EvidenceType.STATISTICAL_TEST,
            method="legacy_method",
            result_summary={"summary": "Observed legacy result."},
        )
        session.add(evidence)

        _, partial_task, partial_hypothesis = _seed_lineage(session, suffix="partial")
        partial_run = _seed_run(
            session,
            task_id=partial_task,
            hypothesis_id=partial_hypothesis,
            suffix="partial",
            status="finalizing",
        )
        exact_run_id = exact_run.execution_run_id
        partial_run_id = partial_run.execution_run_id
        session.exec(
            text(
                "UPDATE hypotheses SET status = 'confirmed' "
                "WHERE hypothesis_id IN (:exact_hypothesis, :partial_hypothesis)"
            ),
            params={
                "exact_hypothesis": exact_hypothesis.hex,
                "partial_hypothesis": partial_hypothesis.hex,
            },
        )
        session.exec(
            text("UPDATE tasks SET lifecycle_state = 'COMPLETED' WHERE task_id = :partial_task"),
            params={"partial_task": partial_task.hex},
        )
        session.commit()

    with get_session(database_url) as session:
        report = LegacyPayloadMigrator(session).inventory()
        assert report.legacy_completed_runs_count == 1
        assert report.legacy_finalizing_runs_count == 1
        assert report.legacy_terminal_hypotheses_count == 2
        assert report.partial_artifact_chains_count == 1
        result = LegacyPayloadMigrator(session).migrate_all()
        assert result["runs_migrated"] == 2
        assert result["hypotheses_migrated"] == 2

        exact_run_record = session.get(ExecutionRunRecord, exact_run_id)
        partial_run_record = session.get(ExecutionRunRecord, partial_run_id)
        exact_hypothesis_record = session.get(HypothesisRecord, exact_hypothesis)
        partial_hypothesis_record = session.get(HypothesisRecord, partial_hypothesis)
        partial_task_record = session.get(TaskRecord, partial_task)
        assert exact_run_record is not None
        assert exact_run_record.status == ExecutionRunStatus.EVIDENCE_ADMITTED
        assert exact_hypothesis_record is not None
        assert exact_hypothesis_record.status == HypothesisStatus.READY_FOR_EVALUATION
        assert partial_run_record is not None
        assert partial_run_record.status == ExecutionRunStatus.ABANDONED
        assert partial_run_record.validity_state == ValiditySourceState.UNVERIFIED
        assert partial_hypothesis_record is not None
        assert partial_hypothesis_record.status == HypothesisStatus.ARCHIVED
        assert partial_task_record is not None
        assert partial_task_record.lifecycle_state == TaskLifecycleState.ACTIVE


def test_unverified_discovery_and_conclusion_frame_are_excluded_from_retrieval(
    tmp_path,
) -> None:
    database_url = _database_url(tmp_path, "legacy-discovery.sqlite3")
    init_db(database_url)
    with get_session(database_url) as session:
        profile_id, task_id, hypothesis_id = _seed_lineage(session, suffix="discovery")
        evidence = EvidenceRecord(
            hypothesis_id=hypothesis_id,
            profile_id=profile_id,
            analysis_frame_ref="legacy-frame",
            execution_run_ref="legacy-run",
            evidence_type=EvidenceType.STATISTICAL_TEST,
            method="legacy_method",
            result_summary={"summary": "Legacy observation."},
        )
        session.add(evidence)
        session.flush()
        discovery = DiscoveryRecord(
            hypothesis_id=hypothesis_id,
            evidence_ids=[str(evidence.evidence_id)],
            claim={
                "statement": "Application-authored legacy conclusion.",
                "scope": "legacy scope",
                "conditions": [],
            },
            epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
            scope="legacy scope",
            validity_basis={
                "data_profile_id": str(profile_id),
                "analysis_frame_refs": ["legacy-frame"],
                "hypothesis_id": str(hypothesis_id),
                "evidence_ids": [str(evidence.evidence_id)],
                "method": "legacy_method",
                "decision_rule": {},
                "uncertainty": None,
                "invalidators": [],
                "assumptions_excluded_from_inference": True,
            },
        )
        session.add(discovery)
        session.flush()
        frame = SessionFrameRecord(
            frame_topic="Legacy conclusion frame",
            objective_snapshot="Legacy objective",
            frame_outcome="Application-authored conclusion.",
            relevant_discovery_refs=[str(discovery.discovery_id)],
        )
        session.add(frame)
        session.commit()
        discovery_id = discovery.discovery_id
        frame_id = frame.session_frame_id

        result = LegacyPayloadMigrator(session).migrate_all()
        assert result["discoveries_quarantined"] == 1
        assert result["session_frames_quarantined"] == 1
        session.expire_all()
        persisted_discovery = session.get(DiscoveryRecord, discovery_id)
        persisted_frame = session.get(SessionFrameRecord, frame_id)
        assert persisted_discovery is not None
        assert persisted_discovery.lifecycle_state == DiscoveryLifecycleState.INVALIDATED
        assert persisted_discovery.claim == discovery.claim
        assert persisted_frame is not None
        assert persisted_frame.frame_status == SessionFrameStatus.SUPERSEDED
        assert persisted_frame.frame_outcome == frame.frame_outcome
        assert persisted_frame.stale_context == [
            {
                "artifact_type": "session_frame",
                "reason": "legacy_unverified_conclusion_frame",
                "ref_id": str(frame_id),
                "replacement_ref_id": None,
            }
        ]

        retrieval = DiscoveryRetrievalEngine(session).retrieve(
            RetrievalRequest(
                objective_id=uuid4(),
                active_data_profile_id=profile_id,
                query_text="legacy conclusion",
            )
        )
        retrieved_ids = {
            item.discovery_id
            for item in (retrieval.motivation_candidates + retrieval.other_relevant_discoveries)
        }
        assert discovery_id not in retrieved_ids


def test_interrupted_migration_rolls_back_and_retries_deterministically(
    tmp_path, monkeypatch
) -> None:
    database_url = _database_url(tmp_path, "interrupted.sqlite3")
    init_db(database_url)
    with get_session(database_url) as session:
        _, task_id, hypothesis_id = _seed_lineage(session, suffix="interrupted")
        run = _seed_run(
            session,
            task_id=task_id,
            hypothesis_id=hypothesis_id,
            suffix="interrupted",
        )
        inbox = ExecutionInboxRecord(
            execution_run_id=run.execution_run_id,
            dispatch_idempotency_key=run.dispatch_idempotency_key or "",
            lease_epoch=1,
            result_digest="interrupted-digest",
            executor_status="completed",
            serialized_observations={
                "status": "success",
                "evaluation": {"verdict": "confirmed"},
            },
            method_id="legacy_method",
        )
        session.add(inbox)
        session.commit()

        migrator = LegacyPayloadMigrator(session)

        def fail_before_marker() -> None:
            raise RuntimeError("simulated migration interruption")

        monkeypatch.setattr(migrator, "_record_completed_marker", fail_before_marker)
        with pytest.raises(RuntimeError, match="simulated migration interruption"):
            migrator.migrate_all()
        session.expire_all()
        rolled_back = session.get(ExecutionInboxRecord, inbox.inbox_id)
        assert rolled_back is not None and rolled_back.status == "pending"
        assert _quarantine_rows(session) == []

        retried = LegacyPayloadMigrator(session).migrate_all()
        assert retried["inbox_migrated"] == 1
        assert session.get(ExecutionInboxRecord, inbox.inbox_id).status == "quarantined"


def test_quarantine_rows_are_database_immutable(tmp_path) -> None:
    database_url = _database_url(tmp_path, "immutable.sqlite3")
    init_db(database_url)
    with get_session(database_url) as session:
        _, task_id, hypothesis_id = _seed_lineage(session, suffix="immutable")
        run = _seed_run(
            session,
            task_id=task_id,
            hypothesis_id=hypothesis_id,
            suffix="immutable",
        )
        inbox = ExecutionInboxRecord(
            execution_run_id=run.execution_run_id,
            dispatch_idempotency_key=run.dispatch_idempotency_key or "",
            lease_epoch=1,
            result_digest="immutable-digest",
            executor_status="failed",
            serialized_observations={},
            method_id="legacy_method",
        )
        session.add(inbox)
        session.commit()
        LegacyPayloadMigrator(session).migrate_all()
        quarantine_id = session.exec(
            text("SELECT quarantine_id FROM legacy_scientific_quarantine")
        ).one()[0]

        with pytest.raises(IntegrityError, match="quarantine is immutable"):
            session.exec(
                text(
                    "UPDATE legacy_scientific_quarantine SET reason = 'tampered' "
                    "WHERE quarantine_id = :quarantine_id"
                ),
                params={"quarantine_id": quarantine_id},
            )
            session.commit()
        session.rollback()
        with pytest.raises(IntegrityError, match="quarantine is immutable"):
            session.exec(
                text(
                    "DELETE FROM legacy_scientific_quarantine WHERE quarantine_id = :quarantine_id"
                ),
                params={"quarantine_id": quarantine_id},
            )
            session.commit()


def test_unsupported_database_is_explicit() -> None:
    session = Mock()
    session.get_bind.return_value.dialect.name = "postgresql"
    with pytest.raises(ValueError, match="supports SQLite only"):
        LegacyPayloadMigrator(session)
