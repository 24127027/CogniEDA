"""Wave 1.1B-2A Evidence-admission contract and migration-safety tests."""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import TypeAdapter, ValidationError
from sqlmodel import select

from application.orchestrator.evidence_admission import (
    ANALYSIS_FRAME_ORDINAL,
    CONTRACT_VERSION,
    EVIDENCE_ADMISSION_NAMESPACE,
    EVIDENCE_ADMISSION_WRITE_SET,
    EVIDENCE_ORDINAL,
    RESOLVED_POST_ADMISSION_STATUS,
    EvidenceAdmissionPlan,
    EvidenceAdmissionReplayDisposition,
    classify_evidence_admission_replay,
    compute_analysis_frame_fingerprint,
    compute_evidence_fingerprint,
    execute_evidence_admission_plan,
    generate_deterministic_analysis_frame_id,
    generate_deterministic_evidence_id,
    validate_and_build_evidence_admission_plan,
)
from application.orchestrator.execution_contracts import (
    ExecutionReceiptEnvelope,
    ExecutionSpecification,
    HypothesisDraft,
    PreparedExecution,
)
from application.orchestrator.execution_identity import (
    canonical_sha256,
    method_parameter_hash,
    result_payload_digest,
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
    SessionFrameRecord,
    TaskRecord,
)
from schemas.common import EvaluationThresholds, EvidenceResultSummary, MethodParameter
from schemas.data_explorer_contracts import (
    DataExplorerFailureReason,
    DataExplorerFailureResult,
    DataExplorerSuccessResult,
)
from schemas.enums import (
    EvidenceType,
    ExecutionRunStatus,
    HypothesisStatus,
)
from schemas.execution_observations import AnalysisFrameObservation, EvidenceObservation


def _make_prepared_and_run(
    *,
    execution_run_id: UUID | None = None,
    task_id: UUID | None = None,
    hypothesis_id: UUID | None = None,
    profile_id: UUID | None = None,
    p_value_threshold: float = 0.05,
    variable_bindings: list[str] | None = None,
    finalizing: bool = True,
) -> tuple[PreparedExecution, ExecutionRunRecord, UUID, UUID, UUID]:
    run_id = execution_run_id or uuid4()
    t_id = task_id or uuid4()
    h_id = hypothesis_id or uuid4()
    p_id = profile_id or uuid4()
    bindings = variable_bindings if variable_bindings is not None else ["x", "y"]
    method_parameters = [MethodParameter(name="method_name", value="pearson")]
    parameter_hash = method_parameter_hash(method_parameters)

    prepared = PreparedExecution(
        execution_ref="exec:123",
        task_ref=str(t_id),
        data_profile_ref=str(p_id),
        hypothesis_ref=str(h_id),
        execution_run_ref=str(run_id),
        task_title="Test Task",
        dataset_path="data.csv",
        hypothesis=HypothesisDraft(
            statement="X correlates with Y",
            variables=bindings,
            scope="test_scope",
            validation_method="deterministic_test",
            evidence_expectation="p_value < 0.05",
        ),
        specification=ExecutionSpecification(
            claim_type="association",
            variable_bindings=bindings,
            scope="test_scope",
            evidence_expectation="p_value < 0.05",
            decision_rule=EvaluationThresholds(p_value=p_value_threshold),
            validation_method="deterministic_test",
            executor_id="data_explorer",
            method_parameters=method_parameters,
        ),
        deterministic_seed=42,
        contract_fingerprint="fp123",
        execution_run_id=run_id,
        dispatch_idempotency_key="idempotency_key_1",
        lease_epoch=1,
    )
    run = ExecutionRunRecord(
        execution_run_id=run_id,
        task_id=t_id,
        hypothesis_id=h_id,
        executor_type="data_explorer",
        method_id="deterministic_test",
        parameter_hash=parameter_hash,
        status=(
            ExecutionRunStatus.EVIDENCE_ADMITTING
            if finalizing
            else ExecutionRunStatus.RUNNING
        ),
        worker_id="worker_1",
        dispatch_idempotency_key="idempotency_key_1",
        lease_epoch=1,
        lease_acquired_at=datetime.now(UTC),
        lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        attempt_version=4 if finalizing else 1,
        finalizer_owner_id="finalizer_1" if finalizing else None,
        finalization_fencing_epoch=2 if finalizing else None,
        finalization_claimed_at=datetime.now(UTC) if finalizing else None,
        finalization_expires_at=(
            datetime.now(UTC) + timedelta(minutes=5) if finalizing else None
        ),
    )
    return prepared, run, p_id, h_id, t_id


def _make_completed_executor_result(
    *,
    p_value: float = 0.01,
    variable_bindings: list[str] | None = None,
) -> ExecutionReceiptEnvelope:
    bindings = variable_bindings if variable_bindings is not None else ["x", "y"]
    method_parameters = [MethodParameter(name="method_name", value="pearson")]
    return DataExplorerSuccessResult(
        analysis_frame=AnalysisFrameObservation(
            frame_hash="frame_hash_123",
            column_refs=bindings,
            row_filter_description="none",
        ),
        evidence_observation=EvidenceObservation(
            evidence_type=EvidenceType.STATISTICAL_TEST,
            method="deterministic_test",
            parameters=method_parameters,
            result_summary=EvidenceResultSummary(
                summary=f"p_value: {p_value}",
                metric_name="p_value",
                metric_value=p_value,
            ),
            artifact_refs=["chart.png"],
            limitations=["small_sample"],
            code_reference="test.py",
            environment_reference="env1",
        ),
    )


def _make_inbox(result: ExecutionReceiptEnvelope, run: ExecutionRunRecord) -> ExecutionInboxRecord:
    return ExecutionInboxRecord(
        execution_run_id=run.execution_run_id,
        dispatch_idempotency_key=run.dispatch_idempotency_key or "",
        lease_epoch=run.lease_epoch,
        result_digest=result_payload_digest(result.model_dump(mode="json")),
        executor_status="completed" if result.status == "success" else "failed",
        serialized_observations=result.model_dump(mode="json"),
        method_id=run.method_id or "",
        status="pending",
    )


def _build_plan(
    prepared: PreparedExecution,
    result: ExecutionReceiptEnvelope,
    run: ExecutionRunRecord,
    profile_id: UUID,
    hypothesis_id: UUID,
    task_id: UUID,
    *,
    inbox: ExecutionInboxRecord | None = None,
    contract_version: str = CONTRACT_VERSION,
    records: tuple[DataProfileRecord, HypothesisRecord, TaskRecord] | None = None,
) -> EvidenceAdmissionPlan:
    profile, hypothesis, task = records or _make_durable_authority(
        prepared,
        profile_id=profile_id,
        hypothesis_id=hypothesis_id,
        task_id=task_id,
    )
    return validate_and_build_evidence_admission_plan(
        prepared=prepared,
        result=result,
        run=run,
        inbox=inbox or _make_inbox(result, run),
        profile=profile,
        hypothesis=hypothesis,
        task=task,
        contract_version=contract_version,
    )


def _make_durable_authority(
    prepared: PreparedExecution,
    *,
    profile_id: UUID,
    hypothesis_id: UUID,
    task_id: UUID,
) -> tuple[DataProfileRecord, HypothesisRecord, TaskRecord]:
    profile = DataProfileRecord(
        profile_id=profile_id,
        dataset_path=prepared.dataset_path,
        method="custom",
        schema_summary={},
        baseline_summary={},
        row_count=10,
        column_count=len(prepared.specification.variable_bindings),
        lifecycle_state="active",
        accepted_as_ground_truth=True,
    )
    task = TaskRecord(
        task_id=task_id,
        profile_id=profile_id,
        title=prepared.task_title,
        description="Approved analytical task",
        lifecycle_state="active",
        task_kind="analytical",
        variables=list(prepared.specification.variable_bindings),
        evidence_expectation=prepared.specification.evidence_expectation,
    )
    hypothesis = HypothesisRecord(
        hypothesis_id=hypothesis_id,
        task_id=task_id,
        profile_id=profile_id,
        statement=prepared.hypothesis.statement,
        variables=list(prepared.specification.variable_bindings),
        scope=prepared.specification.scope,
        validation_method=prepared.specification.validation_method,
        evidence_expectation=prepared.specification.evidence_expectation,
        status="testing",
    )
    return profile, hypothesis, task


def test_completed_observation_only_and_legacy_executor_results_validate() -> None:
    observation_only = _make_completed_executor_result()

    assert (
        TypeAdapter(ExecutionReceiptEnvelope).validate_python(
            observation_only.model_dump(mode="json")
        )
        == observation_only
    )


def test_completed_and_failure_payload_rules_remain_strict() -> None:
    completed = _make_completed_executor_result()
    base = completed.model_dump(mode="json")
    for missing_field in ("analysis_frame", "evidence_observation"):
        invalid = dict(base)
        invalid.pop(missing_field)
        with pytest.raises(ValidationError):
            TypeAdapter(ExecutionReceiptEnvelope).validate_python(invalid)

    failure = DataExplorerFailureResult(
        failure_reason=DataExplorerFailureReason.METHOD_EXECUTION_FAILURE,
        message="Technical error",
    )
    assert failure.status == "failed"
    with pytest.raises(ValidationError):
        TypeAdapter(ExecutionReceiptEnvelope).validate_python(
            completed.model_dump(mode="json") | {"error_message": "Error string"}
        )


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "execution_run_id",
        "task_id",
        "hypothesis_id",
        "data_profile_id",
        "discovery_claim",
        "epistemic_status",
        "validity_basis",
        "finalize",
    ],
)
def test_executor_result_rejects_unknown_identity_and_authority_fields(
    forbidden_field: str,
) -> None:
    payload = _make_completed_executor_result().model_dump(mode="json")
    payload[forbidden_field] = "forbidden"
    with pytest.raises(ValidationError):
        TypeAdapter(ExecutionReceiptEnvelope).validate_python(payload)


def test_deterministic_ids_are_versioned_attempt_scoped_and_ordinal_safe() -> None:
    run_id = uuid4()
    retry_id = uuid4()

    assert EVIDENCE_ADMISSION_NAMESPACE.version == 4
    assert generate_deterministic_analysis_frame_id(run_id) == (
        generate_deterministic_analysis_frame_id(run_id)
    )
    assert generate_deterministic_evidence_id(run_id) == generate_deterministic_evidence_id(run_id)
    assert generate_deterministic_analysis_frame_id(run_id) != generate_deterministic_evidence_id(
        run_id
    )
    assert generate_deterministic_analysis_frame_id(run_id) != (
        generate_deterministic_analysis_frame_id(retry_id)
    )
    assert generate_deterministic_evidence_id(run_id) != generate_deterministic_evidence_id(
        run_id, ordinal=EVIDENCE_ORDINAL + 1
    )
    assert generate_deterministic_analysis_frame_id(
        run_id, contract_version="evidence-admission/v2"
    ) != generate_deterministic_analysis_frame_id(run_id)
    assert ANALYSIS_FRAME_ORDINAL == EVIDENCE_ORDINAL == 0


def test_canonicalization_normalizes_dicts_models_paths_uuids_and_numeric_values() -> None:
    identifier = uuid4()
    first = {
        "nested": {"b": [1.0, MethodParameter(name="alpha", value=0.05)], "a": identifier},
        "optional": None,
    }
    second = {
        "optional": None,
        "nested": {"a": str(identifier), "b": [1, {"name": "alpha", "value": 0.05}]},
    }

    assert canonical_sha256(first) == canonical_sha256(second)
    assert canonical_sha256({"items": ["a", "b"]}) != canonical_sha256({"items": ["b", "a"]})


@pytest.mark.parametrize("unsupported", [float("nan"), float("inf"), float("-inf")])
def test_canonicalization_rejects_non_finite_numbers(unsupported: float) -> None:
    with pytest.raises(ValueError, match="NaN or Infinity"):
        canonical_sha256({"metric": unsupported})


def test_plan_materializes_exactly_one_detached_frame_and_evidence() -> None:
    prepared, run, profile_id, hypothesis_id, task_id = _make_prepared_and_run()
    result = _make_completed_executor_result()
    plan = _build_plan(prepared, result, run, profile_id, hypothesis_id, task_id)

    assert plan.analysis_frame_id == generate_deterministic_analysis_frame_id(run.execution_run_id)
    assert plan.evidence_id == generate_deterministic_evidence_id(run.execution_run_id)
    assert plan.evidence.analysis_frame_ref == str(plan.analysis_frame_id)
    assert plan.evidence.execution_run_ref == str(run.execution_run_id)
    assert plan.evidence.hypothesis_id == hypothesis_id
    assert plan.evidence.profile_id == profile_id
    assert plan.analysis_frame_fingerprint == compute_analysis_frame_fingerprint(
        plan.analysis_frame
    )
    assert plan.evidence_fingerprint == compute_evidence_fingerprint(plan.evidence)
    assert [operation.operation_type for operation in plan.operations] == [
        "create_analysis_frame",
        "create_evidence",
    ]


def test_plan_carries_complete_transaction_authority_and_resolved_lifecycle() -> None:
    prepared, run, profile_id, hypothesis_id, task_id = _make_prepared_and_run()
    result = _make_completed_executor_result()
    inbox = _make_inbox(result, run)
    plan = _build_plan(
        prepared,
        result,
        run,
        profile_id,
        hypothesis_id,
        task_id,
        inbox=inbox,
    )

    assert plan.finalization_owner == run.finalizer_owner_id
    assert plan.finalization_fencing_epoch == run.finalization_fencing_epoch
    assert plan.expected_attempt_version == run.attempt_version
    assert plan.inbox_id == inbox.inbox_id
    assert plan.required_run_status is ExecutionRunStatus.EVIDENCE_ADMITTING
    assert plan.required_inbox_status == "pending"
    assert plan.atomic_write_set == EVIDENCE_ADMISSION_WRITE_SET
    assert plan.inbox_result_digest == inbox.result_digest
    assert plan.post_admission_status_dependency == RESOLVED_POST_ADMISSION_STATUS
    serialized = repr(plan)
    for forbidden_status in ("awaiting_evaluation", "completed_task"):
        assert forbidden_status not in serialized.lower()


def test_replay_classifier_distinguishes_new_idempotent_conflict_and_partial_state() -> None:
    prepared, run, profile_id, hypothesis_id, task_id = _make_prepared_and_run()
    plan = _build_plan(
        prepared,
        _make_completed_executor_result(),
        run,
        profile_id,
        hypothesis_id,
        task_id,
    )

    assert (
        classify_evidence_admission_replay(
            plan,
            existing_analysis_frame_id=None,
            existing_analysis_frame_fingerprint=None,
            existing_evidence_id=None,
            existing_evidence_fingerprint=None,
        )
        is EvidenceAdmissionReplayDisposition.NEW
    )
    assert (
        classify_evidence_admission_replay(
            plan,
            existing_analysis_frame_id=plan.analysis_frame_id,
            existing_analysis_frame_fingerprint=plan.analysis_frame_fingerprint,
            existing_evidence_id=plan.evidence_id,
            existing_evidence_fingerprint=plan.evidence_fingerprint,
        )
        is EvidenceAdmissionReplayDisposition.IDEMPOTENT
    )
    assert (
        classify_evidence_admission_replay(
            plan,
            existing_analysis_frame_id=plan.analysis_frame_id,
            existing_analysis_frame_fingerprint="different",
            existing_evidence_id=plan.evidence_id,
            existing_evidence_fingerprint=plan.evidence_fingerprint,
        )
        is EvidenceAdmissionReplayDisposition.CONFLICT
    )
    assert (
        classify_evidence_admission_replay(
            plan,
            existing_analysis_frame_id=plan.analysis_frame_id,
            existing_analysis_frame_fingerprint=plan.analysis_frame_fingerprint,
            existing_evidence_id=None,
            existing_evidence_fingerprint=None,
        )
        is EvidenceAdmissionReplayDisposition.CONFLICT
    )


def _persist_admission_authority_and_plan(db_session) -> EvidenceAdmissionPlan:
    prepared, run, profile_id, hypothesis_id, task_id = _make_prepared_and_run()
    result = _make_completed_executor_result()
    inbox = _make_inbox(result, run)
    profile, hypothesis, task = _make_durable_authority(
        prepared,
        profile_id=profile_id,
        hypothesis_id=hypothesis_id,
        task_id=task_id,
    )
    run.status = ExecutionRunStatus.EVIDENCE_ADMITTING
    db_session.add(profile)
    db_session.flush()
    db_session.add(task)
    db_session.flush()
    db_session.add(hypothesis)
    db_session.flush()
    db_session.add(run)
    db_session.flush()
    db_session.add(inbox)
    db_session.commit()
    return validate_and_build_evidence_admission_plan(
        prepared=prepared,
        result=result,
        run=run,
        inbox=inbox,
        profile=profile,
        hypothesis=hypothesis,
        task=task,
    )


def _stage_plan_artifacts(
    db_session,
    plan: EvidenceAdmissionPlan,
    *,
    include_evidence: bool,
) -> None:
    db_session.add(
        AnalysisFrameRecord(
            analysis_frame_id=plan.analysis_frame.analysis_frame_id,
            data_profile_id=plan.analysis_frame.data_profile_id,
            frame_hash=plan.analysis_frame.frame_hash,
            frame_ref=plan.analysis_frame.frame_ref,
            column_refs=list(plan.analysis_frame.column_refs),
            row_filter_description=plan.analysis_frame.row_filter_description,
            created_at=plan.analysis_frame.created_at,
        )
    )
    if include_evidence:
        db_session.add(
            EvidenceRecord(
                evidence_id=plan.evidence.evidence_id,
                hypothesis_id=plan.evidence.hypothesis_id,
                profile_id=plan.evidence.profile_id,
                analysis_frame_ref=plan.evidence.analysis_frame_ref,
                execution_run_ref=plan.evidence.execution_run_ref,
                evidence_type=plan.evidence.evidence_type,
                method=plan.evidence.method,
                parameters=[
                    parameter.model_dump(mode="json")
                    for parameter in plan.evidence.parameters
                ],
                provenance=plan.evidence.provenance.model_dump(mode="json"),
                result_summary=plan.evidence.result_summary.model_dump(mode="json"),
                artifact_refs=list(plan.evidence.artifact_refs),
                limitations=list(plan.evidence.limitations),
                created_at=plan.evidence.created_at,
            )
        )
    db_session.commit()


def test_idempotent_artifact_replay_finishes_the_atomic_lifecycle(db_session) -> None:
    plan = _persist_admission_authority_and_plan(db_session)
    _stage_plan_artifacts(db_session, plan, include_evidence=True)

    assert execute_evidence_admission_plan(db_session, plan) is True

    run = db_session.get(ExecutionRunRecord, plan.execution_run_id)
    hypothesis = db_session.get(HypothesisRecord, plan.hypothesis_id)
    inbox = db_session.get(ExecutionInboxRecord, plan.inbox_id)
    assert run is not None
    assert run.status == ExecutionRunStatus.EVIDENCE_ADMITTED
    assert run.analysis_frame_id == plan.analysis_frame_id
    assert hypothesis is not None
    assert hypothesis.status == HypothesisStatus.READY_FOR_EVALUATION
    assert inbox is not None and inbox.status == "processed"


def test_partial_artifact_replay_is_durably_quarantined(db_session) -> None:
    plan = _persist_admission_authority_and_plan(db_session)
    _stage_plan_artifacts(db_session, plan, include_evidence=False)

    assert execute_evidence_admission_plan(db_session, plan) is False

    run = db_session.get(ExecutionRunRecord, plan.execution_run_id)
    hypothesis = db_session.get(HypothesisRecord, plan.hypothesis_id)
    inbox = db_session.get(ExecutionInboxRecord, plan.inbox_id)
    assert run is not None
    assert run.status == ExecutionRunStatus.RESULT_CONFLICT
    assert run.recovery_status == "evidence_admission_artifact_conflict"
    assert hypothesis is not None and hypothesis.status == HypothesisStatus.TESTING
    assert inbox is not None and inbox.status == "conflict"
    assert db_session.get(EvidenceRecord, plan.evidence_id) is None


def test_meaningful_stored_content_change_changes_fingerprint_not_identity() -> None:
    prepared, run, profile_id, hypothesis_id, task_id = _make_prepared_and_run()
    first = _build_plan(
        prepared,
        _make_completed_executor_result(p_value=0.01),
        run,
        profile_id,
        hypothesis_id,
        task_id,
    )
    second = _build_plan(
        prepared,
        _make_completed_executor_result(p_value=0.99),
        run,
        profile_id,
        hypothesis_id,
        task_id,
    )

    assert first.evidence_id == second.evidence_id
    assert first.evidence_fingerprint != second.evidence_fingerprint


def test_evaluation_and_decision_threshold_do_not_affect_admission_artifacts() -> None:
    prepared, run, profile_id, hypothesis_id, task_id = _make_prepared_and_run(
        p_value_threshold=0.001
    )
    observation_only = _make_completed_executor_result(p_value=0.5)
    first = _build_plan(prepared, observation_only, run, profile_id, hypothesis_id, task_id)
    second = _build_plan(prepared, observation_only, run, profile_id, hypothesis_id, task_id)

    assert first.analysis_frame_id == second.analysis_frame_id
    assert first.evidence_id == second.evidence_id
    assert first.analysis_frame_fingerprint == second.analysis_frame_fingerprint
    assert first.evidence_fingerprint == second.evidence_fingerprint
    assert first.operations == second.operations


def test_caller_mutation_after_construction_cannot_change_plan_or_fingerprints() -> None:
    prepared, run, profile_id, hypothesis_id, task_id = _make_prepared_and_run()
    result = _make_completed_executor_result()
    plan = _build_plan(prepared, result, run, profile_id, hypothesis_id, task_id)
    frame_fingerprint = plan.analysis_frame_fingerprint
    evidence_fingerprint = plan.evidence_fingerprint
    operation_payloads = [operation.model_dump(mode="python") for operation in plan.operations]

    prepared.specification.variable_bindings.append("caller_mutation")
    prepared.specification.method_parameters[0].value = "caller_mutation"
    result.analysis_frame.column_refs.append("caller_mutation")
    assert result.evidence_observation is not None
    result.evidence_observation.artifact_refs.append("caller_mutation")
    result.evidence_observation.result_summary.metric_value = 0.99

    assert plan.analysis_frame.column_refs == ["x", "y"]
    assert plan.evidence.parameters[0].value == "pearson"
    assert plan.evidence.artifact_refs == ["chart.png"]
    assert plan.evidence.result_summary.metric_value == 0.01
    assert plan.analysis_frame_fingerprint == frame_fingerprint
    assert plan.evidence_fingerprint == evidence_fingerprint
    assert [operation.model_dump(mode="python") for operation in plan.operations] == (
        operation_payloads
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("execution_run_id", "identity mismatch"),
        ("task_id", "identity mismatch"),
        ("hypothesis_id", "identity mismatch"),
        ("profile_id", "identity mismatch"),
        ("executor_id", "approved execution contract"),
        ("method_id", "approved execution contract"),
        ("parameter_payload", "approved execution contract"),
        ("bindings", "approved execution contract"),
        ("dispatch_key", "identity mismatch"),
        ("lease_epoch", "identity mismatch"),
        ("inbox_run", "inbox does not match"),
        ("inbox_status", "inbox does not match"),
        ("result_payload", "authoritative inbox payload"),
        ("hypothesis_task_lineage", "identity mismatch"),
        ("hypothesis_profile_lineage", "identity mismatch"),
        ("task_profile_lineage", "identity mismatch"),
        ("profile_state", "not eligible"),
        ("hypothesis_state", "not eligible"),
    ],
)
def test_admission_rejects_each_identity_and_contract_mismatch_independently(
    mutation: str,
    message: str,
) -> None:
    prepared, run, profile_id, hypothesis_id, task_id = _make_prepared_and_run()
    result = _make_completed_executor_result()
    inbox = _make_inbox(result, run)
    admitted_profile_id = profile_id
    admitted_hypothesis_id = hypothesis_id
    admitted_task_id = task_id
    records = _make_durable_authority(
        prepared,
        profile_id=profile_id,
        hypothesis_id=hypothesis_id,
        task_id=task_id,
    )
    profile, hypothesis, task = records

    if mutation == "execution_run_id":
        prepared.execution_run_id = uuid4()
    elif mutation == "task_id":
        task.task_id = uuid4()
    elif mutation == "hypothesis_id":
        hypothesis.hypothesis_id = uuid4()
    elif mutation == "profile_id":
        profile.profile_id = uuid4()
    elif mutation == "executor_id":
        prepared.specification.executor_id = "other_executor"
    elif mutation == "method_id":
        result.evidence_observation.method = "other_method"
        inbox.serialized_observations = result.model_dump(mode="json")
    elif mutation == "parameter_payload":
        assert result.evidence_observation is not None
        result.evidence_observation.parameters[0].value = "spearman"
        inbox.serialized_observations = result.model_dump(mode="json")
    elif mutation == "bindings":
        result.analysis_frame.column_refs = ["x"]
        inbox.serialized_observations = result.model_dump(mode="json")
    elif mutation == "dispatch_key":
        prepared.dispatch_idempotency_key = "other-key"
    elif mutation == "lease_epoch":
        prepared.lease_epoch += 1
    elif mutation == "inbox_run":
        inbox.execution_run_id = uuid4()
    elif mutation == "inbox_status":
        inbox.status = "processed"
    elif mutation == "result_payload":
        assert result.evidence_observation is not None
        result.evidence_observation.limitations.append("not in inbox")
    elif mutation == "hypothesis_task_lineage":
        hypothesis.task_id = uuid4()
    elif mutation == "hypothesis_profile_lineage":
        hypothesis.profile_id = uuid4()
    elif mutation == "task_profile_lineage":
        task.profile_id = uuid4()
    elif mutation == "profile_state":
        profile.accepted_as_ground_truth = False
    elif mutation == "hypothesis_state":
        hypothesis.status = "approved"
    if mutation in {"method_id", "parameter_payload", "bindings"}:
        inbox.result_digest = result_payload_digest(inbox.serialized_observations)

    with pytest.raises(ValueError, match=message):
        _build_plan(
            prepared,
            result,
            run,
            admitted_profile_id,
            admitted_hypothesis_id,
            admitted_task_id,
            inbox=inbox,
            records=records,
        )


def test_admission_rejects_failure_incompatible_version_and_unclaimed_run() -> None:
    prepared, run, profile_id, hypothesis_id, task_id = _make_prepared_and_run()
    failed = DataExplorerFailureResult(
        failure_reason=DataExplorerFailureReason.METHOD_EXECUTION_FAILURE,
        message="Technical failure",
    )
    with pytest.raises(ValueError, match="technically successful"):
        _build_plan(prepared, failed, run, profile_id, hypothesis_id, task_id)

    completed = _make_completed_executor_result()
    with pytest.raises(ValueError, match="Unsupported Evidence-admission contract version"):
        _build_plan(
            prepared,
            completed,
            run,
            profile_id,
            hypothesis_id,
            task_id,
            contract_version="evidence-admission/v2",
        )
    run.status = ExecutionRunStatus.RESULT_RECEIVED
    with pytest.raises(ValueError, match="attempt authority"):
        _build_plan(prepared, completed, run, profile_id, hypothesis_id, task_id)


def test_active_execution_to_evidence_modules_import_no_scientific_authority() -> None:
    root = Path(__file__).parents[3]
    source_paths = (
        root / "src" / "agents" / "executor" / "dispatcher.py",
        root / "src" / "agents" / "executor" / "executor.py",
        root / "src" / "application" / "orchestrator" / "evidence_admission.py",
        root / "src" / "application" / "orchestrator" / "execution_contracts.py",
        root / "src" / "application" / "orchestrator" / "execution_identity.py",
        root / "src" / "application" / "orchestrator" / "finalizer.py",
    )
    forbidden_symbols = {
        "Discovery",
        "DiscoveryRepository",
        "DiscoveryClaim",
        "ValidityBasis",
        "DiscoveryEpistemicStatus",
        "HypothesisEvidenceOutcome",
        "_evaluate_deterministically",
        "_evaluate_result_summary_deterministically",
        "_discovery_conclusion",
        "_discovery_from_evaluation",
        "SessionFrameBuilder",
    }
    forbidden_modules = {
        "application.orchestrator.scientific_processing",
        "application.orchestrator.finalizer",
        "schemas.specialist_contracts",
    }

    for path in source_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_symbols: set[str] = set()
        imported_modules: set[str] = set()
        referenced_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules.add(node.module or "")
                imported_symbols.update(alias.name for alias in node.names)
        assert not (forbidden_symbols & (imported_symbols | referenced_names))
        assert not (forbidden_modules & imported_modules)


def test_production_finalizer_is_sole_call_site_invoking_evidence_admission() -> None:
    root = Path(__file__).parents[3] / "src"
    call_sites: list[Path] = []
    for path in root.rglob("*.py"):
        if path.name == "evidence_admission.py":
            continue
        text = path.read_text(encoding="utf-8")
        if (
            "validate_and_build_evidence_admission_plan" in text
            or "execute_evidence_admission_plan" in text
        ):
            call_sites.append(path)
    assert len(call_sites) == 1
    assert call_sites[0].name == "finalizer.py"
    finalizer_text = call_sites[0].read_text(encoding="utf-8")
    assert "process_scientific_result" not in finalizer_text
    assert "DiscoveryRecord" not in finalizer_text


def test_full_path_repeated_technical_failures_succeed_and_leave_hypothesis_testing(
    db_session,
) -> None:
    """Verify repeated technical failure path through receipt and finalization."""

    from application.orchestrator.cancellation import authorize_retry
    from application.orchestrator.finalizer import finalize_attempt
    from application.orchestrator.transition_service import ExecutionAttemptTransitionService

    prepared, run, profile_id, hypothesis_id, task_id = _make_prepared_and_run(finalizing=False)
    db_session.add(
        DataProfileRecord(
            profile_id=profile_id,
            dataset_path="data.csv",
            dvc_hash="hash",
            schema_summary={},
            baseline_summary={},
            row_count=10,
            column_count=2,
            method="test",
        )
    )
    db_session.flush()
    db_session.add(
        TaskRecord(
            task_id=task_id,
            profile_id=profile_id,
            title="Test Task",
            description="desc",
            variables=["x", "y"],
            task_kind="analytical",
        )
    )
    db_session.flush()
    hypothesis = HypothesisRecord(
        hypothesis_id=hypothesis_id,
        task_id=task_id,
        profile_id=profile_id,
        statement="X correlates with Y",
        scope="test_scope",
        validation_method="deterministic_test",
        evidence_expectation="p_value < 0.05",
        status="testing",
    )
    db_session.add(hypothesis)
    db_session.flush()
    db_session.add(run)
    db_session.flush()
    db_session.add(
        ExecutionOutboxRecord(
            execution_run_id=run.execution_run_id,
            dispatch_idempotency_key=run.dispatch_idempotency_key or "",
            executor_type=run.executor_type or "",
            method_id=run.method_id or "",
            parameter_hash=run.parameter_hash or "",
            prepared_payload=prepared.model_dump(mode="json"),
            status="dispatching",
        )
    )
    db_session.commit()

    transition = ExecutionAttemptTransitionService(db_session)
    first_failure = DataExplorerFailureResult(
        failure_reason=DataExplorerFailureReason.METHOD_EXECUTION_FAILURE,
        message="Technical failure",
    ).model_dump(mode="json")
    first_inbox = transition.accept_authoritative_result(
        execution_run_id=run.execution_run_id,
        dispatch_idempotency_key=run.dispatch_idempotency_key or "",
        worker_id="worker_1",
        lease_epoch=run.lease_epoch,
        result_digest=result_payload_digest(first_failure),
        executor_status="failed",
        serialized_observations=first_failure,
        error_message="Technical failure",
        method_id=run.method_id or "",
        producer_identity="test",
    )
    assert first_inbox is not None
    assert finalize_attempt(db_session, run.execution_run_id) is True
    db_session.refresh(hypothesis)
    assert hypothesis.status == "testing"

    retry_id = authorize_retry(db_session, run.execution_run_id, "technical_failure_retry")
    assert retry_id is not None
    transition = ExecutionAttemptTransitionService(db_session)
    claimed = transition.claim_dispatch(
        retry_id,
        "worker_2",
        datetime.now(UTC) + timedelta(minutes=5),
    )
    assert claimed is not None
    assert transition.mark_running(retry_id, "worker_2", claimed.lease_epoch)

    retry = db_session.get(ExecutionRunRecord, retry_id)
    assert retry is not None
    second_failure = DataExplorerFailureResult(
        failure_reason=DataExplorerFailureReason.METHOD_EXECUTION_FAILURE,
        message="Technical failure again",
    ).model_dump(mode="json")
    second_inbox = transition.accept_authoritative_result(
        execution_run_id=retry_id,
        dispatch_idempotency_key=retry.dispatch_idempotency_key or "",
        worker_id="worker_2",
        lease_epoch=retry.lease_epoch,
        result_digest=result_payload_digest(second_failure),
        executor_status="failed",
        serialized_observations=second_failure,
        error_message="Technical failure again",
        method_id=retry.method_id or "",
        producer_identity="test",
    )
    assert second_inbox is not None

    assert finalize_attempt(db_session, retry_id, finalizer_owner_id="second-finalizer") is True
    db_session.expire_all()
    retry = db_session.get(ExecutionRunRecord, retry_id)
    second_inbox = db_session.get(ExecutionInboxRecord, second_inbox.inbox_id)
    hypothesis = db_session.get(type(hypothesis), hypothesis_id)
    assert retry is not None and retry.status == ExecutionRunStatus.EXECUTION_FAILED
    assert second_inbox is not None and second_inbox.status == "processed"
    assert hypothesis is not None and hypothesis.status == "testing"
    for record_type in (
        AnalysisFrameRecord,
        EvidenceRecord,
        DiscoveryRecord,
        SessionFrameRecord,
    ):
        assert db_session.exec(select(record_type)).all() == []
