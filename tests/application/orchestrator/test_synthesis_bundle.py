"""Repository-backed admission and structural-safety tests for protected bundles."""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError
from sqlmodel import select

from application.orchestrator.synthesis_bundle import (
    SynthesisBundleError,
    build_synthesis_bundle,
    compute_bundle_digest,
)
from db.models import (
    DataProfileRecord,
    DiscoveryRecord,
    ExecutionOutboxRecord,
    ExecutionRunRecord,
    HypothesisRecord,
)
from package2_helpers import persist_package2_lineage
from schemas.enums import (
    DataProfileLifecycleState,
    DiscoveryEpistemicStatus,
    ExecutionRunStatus,
    HypothesisStatus,
)
from schemas.specialist_contracts import (
    AdmittedEvidenceSnapshot,
    AnalysisFrameEvaluationSnapshot,
    DataProfileEvaluationSnapshot,
    DiscoverySynthesisBundle,
    ExecutionRunEvaluationSnapshot,
    HypothesisEvaluationSnapshot,
)


def test_builder_uses_only_repository_identity_and_builds_complete_manifest(db_session) -> None:
    lineage = persist_package2_lineage(db_session)

    bundle, manifest = build_synthesis_bundle(db_session, lineage.hypothesis_id)

    assert bundle.input_digest == compute_bundle_digest(bundle)
    assert [item.evidence_id for item in bundle.admitted_evidence] == [lineage.evidence_id]
    assert [item.analysis_frame_id for item in bundle.analysis_frames] == [
        lineage.analysis_frame_id
    ]
    assert [item.execution_run_id for item in bundle.execution_runs] == [lineage.execution_run_id]
    assert manifest.bundle_digest == bundle.input_digest
    assert {(entry.object_type.value, entry.object_id) for entry in manifest.entries} == {
        ("Hypothesis", lineage.hypothesis_id),
        ("DataProfile", lineage.profile_id),
        ("AnalysisFrame", lineage.analysis_frame_id),
        ("ExecutionRun", lineage.execution_run_id),
        ("Evidence", lineage.evidence_id),
    }


def test_bundle_schema_structurally_excludes_unsafe_context_channels(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    forbidden = {
        "assumption",
        "assumptions",
        "task",
        "tasks",
        "discovery",
        "discoveries",
        "session_frame",
        "chat",
        "user_decision",
        "planner_operation",
        "generated_view",
        "cache",
        "raw_data",
        "dataset_path",
        "context",
        "metadata",
    }
    model_types = (
        DiscoverySynthesisBundle,
        HypothesisEvaluationSnapshot,
        DataProfileEvaluationSnapshot,
        AnalysisFrameEvaluationSnapshot,
        ExecutionRunEvaluationSnapshot,
        AdmittedEvidenceSnapshot,
    )
    for model_type in model_types:
        assert forbidden.isdisjoint(model_type.model_fields)

    payload = bundle.model_dump(mode="python")
    for field in forbidden:
        candidate = dict(payload)
        candidate[field] = "forbidden"
        with pytest.raises(ValidationError):
            DiscoverySynthesisBundle.model_validate(candidate)


def test_builder_has_no_caller_supplied_scientific_context_parameters() -> None:
    parameters = set(inspect.signature(build_synthesis_bundle).parameters)
    assert parameters == {"session", "hypothesis_id", "contract_version", "allow_evaluated"}


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("hypothesis", "READY_FOR_EVALUATION"),
        ("profile", "active and accepted"),
        ("run", "Evidence and admitted execution provenance"),
        ("outbox", "Outbox execution contract differs"),
        ("outbox_seed", "Outbox execution contract differs"),
    ],
)
def test_builder_rejects_each_noncanonical_authority(
    db_session, mutation: str, message: str
) -> None:
    lineage = persist_package2_lineage(db_session)
    if mutation == "hypothesis":
        hypothesis = db_session.get(HypothesisRecord, lineage.hypothesis_id)
        assert hypothesis is not None
        hypothesis.status = HypothesisStatus.TESTING
        db_session.add(hypothesis)
    elif mutation == "profile":
        profile = db_session.get(DataProfileRecord, lineage.profile_id)
        assert profile is not None
        profile.lifecycle_state = DataProfileLifecycleState.SUPERSEDED
        db_session.add(profile)
    elif mutation == "run":
        run = db_session.get(ExecutionRunRecord, lineage.execution_run_id)
        assert run is not None
        run.status = ExecutionRunStatus.CANCELLED
        db_session.add(run)
    else:
        outbox = db_session.exec(
            select(ExecutionOutboxRecord).where(
                ExecutionOutboxRecord.execution_run_id == lineage.execution_run_id
            )
        ).one()
        payload = dict(outbox.prepared_payload)
        if mutation == "outbox":
            specification = dict(payload["specification"])
            specification["decision_rule"] = {"p_value": 0.01}
            payload["specification"] = specification
        else:
            payload["deterministic_seed"] = 999
        outbox.prepared_payload = payload
        db_session.add(outbox)
    db_session.commit()

    with pytest.raises(SynthesisBundleError, match=message):
        build_synthesis_bundle(db_session, lineage.hypothesis_id)


def test_builder_rejects_existing_discovery_without_loading_it_as_context(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    db_session.add(
        DiscoveryRecord(
            hypothesis_id=lineage.hypothesis_id,
            evidence_ids=[str(lineage.evidence_id)],
            claim={"statement": "Existing claim.", "scope": "scope"},
            epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
            scope="scope",
            validity_basis={"source": "existing"},
        )
    )
    db_session.commit()

    with pytest.raises(SynthesisBundleError, match="Discovery already exists"):
        build_synthesis_bundle(db_session, lineage.hypothesis_id)
