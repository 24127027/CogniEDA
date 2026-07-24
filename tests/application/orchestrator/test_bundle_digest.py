"""Canonicalization and mutation-safety tests for protected bundle identity."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from application.orchestrator.synthesis_bundle import (
    build_synthesis_bundle,
    compute_bundle_digest,
)
from db.models import (
    AssumptionRecord,
    EvidenceRecord,
    ExecutionRunRecord,
    SessionFrameRecord,
    TaskRecord,
)
from package2_helpers import persist_package2_lineage


def test_rebuilding_unchanged_durable_state_is_deterministic(db_session) -> None:
    lineage = persist_package2_lineage(db_session)

    first, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    second, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)

    assert first == second
    assert first.input_digest == second.input_digest == compute_bundle_digest(first)
    assert first.hypothesis.deterministic_seed is not None
    changed_seed = first.model_copy(
        update={
            "hypothesis": first.hypothesis.model_copy(
                update={"deterministic_seed": first.hypothesis.deterministic_seed + 1}
            )
        }
    )
    assert compute_bundle_digest(changed_seed) != first.input_digest


def test_task_wording_assumption_and_session_frame_cannot_change_digest(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    first, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)

    task = db_session.get(TaskRecord, lineage.task_id)
    assert task is not None
    task.title = "Completely different workflow wording"
    task.description = "Still not a scientific premise."
    db_session.add(task)
    db_session.add(
        AssumptionRecord(
            statement="A planning-only assumption.",
            scope="planning",
            scoped_data_profile_ids=[str(lineage.profile_id)],
        )
    )
    db_session.add(
        SessionFrameRecord(
            frame_topic="Conversation state",
            objective_snapshot="A raw session snapshot excluded from evaluation.",
            active_assumption_refs=[],
        )
    )
    db_session.commit()

    second, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    assert second.input_digest == first.input_digest


def test_scientific_evidence_change_alters_digest_and_nonfinite_number_is_rejected(
    db_session,
) -> None:
    lineage = persist_package2_lineage(db_session)
    first, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    evidence = db_session.get(EvidenceRecord, lineage.evidence_id)
    assert evidence is not None
    changed = dict(evidence.result_summary)
    changed["metric_value"] = 0.02
    evidence.result_summary = changed
    db_session.add(evidence)
    db_session.commit()

    second, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    assert second.input_digest != first.input_digest

    evidence = db_session.get(EvidenceRecord, lineage.evidence_id)
    assert evidence is not None
    invalid = dict(evidence.result_summary)
    invalid["metric_value"] = float("nan")
    evidence.result_summary = invalid
    db_session.add(evidence)
    db_session.commit()
    with pytest.raises(ValueError, match="NaN or Infinity"):
        build_synthesis_bundle(db_session, lineage.hypothesis_id)


def test_owner_lease_and_timestamps_are_not_scientific_digest_inputs(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    first, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    run = db_session.get(ExecutionRunRecord, lineage.execution_run_id)
    evidence = db_session.get(EvidenceRecord, lineage.evidence_id)
    assert run is not None and evidence is not None
    run.worker_id = "replacement-worker"
    run.lease_epoch += 100
    run.finalizer_owner_id = "historical-finalizer"
    evidence.created_at += timedelta(days=30)
    db_session.add(run)
    db_session.add(evidence)
    db_session.commit()

    second, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    assert second.input_digest == first.input_digest


def test_bundle_and_nested_scientific_content_are_deeply_immutable(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)

    with pytest.raises(ValidationError):
        bundle.input_digest = "f" * 64
    with pytest.raises(ValidationError):
        bundle.hypothesis.scope = "expanded"
    with pytest.raises(ValidationError):
        bundle.admitted_evidence[0].result.summary = "mutated"
