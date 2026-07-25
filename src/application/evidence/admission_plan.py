"""Pure deterministic Evidence-admission plan and contract validation logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Literal
from uuid import UUID, uuid5

from pydantic import BaseModel

from application.execution.identity import method_parameter_hash, result_payload_digest
from db.models import (
    DataProfileRecord,
    ExecutionInboxRecord,
    ExecutionRunRecord,
    HypothesisRecord,
    TaskRecord,
)
from schemas.artifacts import Evidence
from schemas.canonical import canonical_sha256
from schemas.common import EvidenceProvenance
from schemas.enums import (
    DataProfileLifecycleState,
    ExecutionRunStatus,
    HypothesisStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskKind,
    TaskLifecycleState,
)
from schemas.execution.observations import AnalysisFrameObservation, EvidenceObservation
from schemas.planner_operations import PlannerOperation
from schemas.provenance import AnalysisFrame

if TYPE_CHECKING:
    from schemas.execution.contracts import (
        ExecutionReceiptEnvelope,
        PreparedExecution,
    )


EVIDENCE_ADMISSION_NAMESPACE = UUID("14cbaf0b-3df7-4cba-8eb3-47b615bb6554")
CONTRACT_VERSION = "evidence-admission/v1"
ANALYSIS_FRAME_ORDINAL = 0
EVIDENCE_ORDINAL = 0
RESOLVED_POST_ADMISSION_STATUS = (
    "execution_run:evidence_admitted+hypothesis:ready_for_evaluation"
)
EVIDENCE_ADMISSION_WRITE_SET = (
    "analysis_frame_insert",
    "evidence_insert",
    "fenced_execution_run_evidence_admitted_and_analysis_frame_assignment",
    "hypothesis_ready_for_evaluation_transition",
    "authoritative_inbox_consumption",
)


class EvidenceAdmissionReplayDisposition(StrEnum):
    """Content-equivalence result used inside the future fenced transaction."""

    NEW = "new"
    IDEMPOTENT = "idempotent"
    CONFLICT = "conflict"


class EvidenceAdmissionConflictError(ValueError):
    """Raised when durable inbox authority conflicts with the claimed attempt."""


def generate_deterministic_analysis_frame_id(
    execution_run_id: UUID,
    ordinal: int = ANALYSIS_FRAME_ORDINAL,
    *,
    contract_version: str = CONTRACT_VERSION,
) -> UUID:
    """Derive one versioned AnalysisFrame identity from the durable attempt."""

    return _deterministic_artifact_id(
        execution_run_id,
        artifact_kind="analysis_frame",
        ordinal=ordinal,
        contract_version=contract_version,
    )


def generate_deterministic_evidence_id(
    execution_run_id: UUID,
    ordinal: int = EVIDENCE_ORDINAL,
    *,
    contract_version: str = CONTRACT_VERSION,
) -> UUID:
    """Derive one versioned Evidence identity from the durable attempt."""

    return _deterministic_artifact_id(
        execution_run_id,
        artifact_kind="evidence",
        ordinal=ordinal,
        contract_version=contract_version,
    )


def _deterministic_artifact_id(
    execution_run_id: UUID,
    *,
    artifact_kind: Literal["analysis_frame", "evidence"],
    ordinal: int,
    contract_version: str,
) -> UUID:
    if not contract_version:
        raise ValueError("Deterministic identity requires a non-empty contract version.")
    if ordinal < 0:
        raise ValueError("Artifact ordinal must be non-negative.")
    name = f"{contract_version}:{execution_run_id}:{artifact_kind}:{ordinal}"
    return uuid5(EVIDENCE_ADMISSION_NAMESPACE, name)


def compute_analysis_frame_fingerprint(
    analysis_frame: AnalysisFrame,
    *,
    contract_version: str = CONTRACT_VERSION,
) -> str:
    """Fingerprint all stored AnalysisFrame content except its creation timestamp."""

    return canonical_sha256(
        {
            "contract_version": contract_version,
            "analysis_frame": analysis_frame.model_dump(
                mode="python",
                exclude={"created_at"},
            ),
        }
    )


def compute_evidence_fingerprint(
    evidence: Evidence,
    *,
    contract_version: str = CONTRACT_VERSION,
) -> str:
    """Fingerprint all stored immutable Evidence content except its creation timestamp."""

    return canonical_sha256(
        {
            "contract_version": contract_version,
            "evidence": evidence.model_dump(
                mode="python",
                exclude={"created_at"},
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class EvidenceAdmissionPlan:
    """Complete authority and write-set contract for a future atomic admission."""

    contract_version: str
    execution_run_id: UUID
    task_id: UUID
    hypothesis_id: UUID
    data_profile_id: UUID
    dispatch_idempotency_key: str
    lease_epoch: int
    finalization_owner: str
    finalization_fencing_epoch: int
    expected_attempt_version: int
    inbox_id: UUID
    inbox_result_digest: str
    analysis_frame_id: UUID
    evidence_id: UUID
    analysis_frame_fingerprint: str
    evidence_fingerprint: str
    analysis_frame: AnalysisFrame
    evidence: Evidence
    operations: tuple[PlannerOperation, ...] = field(default_factory=tuple)
    required_run_status: ExecutionRunStatus = ExecutionRunStatus.EVIDENCE_ADMITTING
    required_inbox_status: Literal["pending"] = "pending"
    atomic_write_set: tuple[str, ...] = EVIDENCE_ADMISSION_WRITE_SET
    post_admission_status_dependency: str = RESOLVED_POST_ADMISSION_STATUS


def classify_evidence_admission_replay(
    plan: EvidenceAdmissionPlan,
    *,
    existing_analysis_frame_id: UUID | None,
    existing_analysis_frame_fingerprint: str | None,
    existing_evidence_id: UUID | None,
    existing_evidence_fingerprint: str | None,
) -> EvidenceAdmissionReplayDisposition:
    """Classify replay content; the future fenced transaction remains concurrency authority."""

    existing_values = (
        existing_analysis_frame_id,
        existing_analysis_frame_fingerprint,
        existing_evidence_id,
        existing_evidence_fingerprint,
    )
    if all(value is None for value in existing_values):
        return EvidenceAdmissionReplayDisposition.NEW
    if any(value is None for value in existing_values):
        return EvidenceAdmissionReplayDisposition.CONFLICT
    if (
        existing_analysis_frame_id == plan.analysis_frame_id
        and existing_analysis_frame_fingerprint == plan.analysis_frame_fingerprint
        and existing_evidence_id == plan.evidence_id
        and existing_evidence_fingerprint == plan.evidence_fingerprint
    ):
        return EvidenceAdmissionReplayDisposition.IDEMPOTENT
    return EvidenceAdmissionReplayDisposition.CONFLICT


def _execution_operation(
    session_id: str | None,
    operation_type: PlannerOperationType,
    payload: BaseModel,
    produced_by_node: PlannerNodeName,
    *,
    operation_id: UUID,
    created_at: datetime,
) -> PlannerOperation:
    return PlannerOperation(
        operation_id=operation_id,
        session_id=session_id,
        operation_type=operation_type,
        payload=payload.model_dump(mode="json"),
        produced_by_node=produced_by_node,
        approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
        created_at=created_at,
    )


def validate_and_build_evidence_admission_plan(
    *,
    prepared: PreparedExecution,
    result: ExecutionReceiptEnvelope,
    run: ExecutionRunRecord,
    inbox: ExecutionInboxRecord,
    profile: DataProfileRecord,
    hypothesis: HypothesisRecord,
    task: TaskRecord,
    session_id: str | None = None,
    contract_version: str = CONTRACT_VERSION,
) -> EvidenceAdmissionPlan:
    """Validate authoritative success and build a detached, scientifically inert plan."""

    if contract_version != CONTRACT_VERSION:
        raise ValueError(f"Unsupported Evidence-admission contract version: {contract_version}.")
    if result.status != "success":
        raise ValueError("Evidence admission requires a technically successful observation.")

    frame_observation = AnalysisFrameObservation.model_validate(
        result.analysis_frame.model_dump(mode="python")
    )
    evidence_observation = EvidenceObservation.model_validate(
        result.evidence_observation.model_dump(mode="python")
    )

    _validate_transaction_authority(run=run, inbox=inbox, result=result)
    _validate_durable_lineage(
        prepared=prepared,
        run=run,
        profile=profile,
        hypothesis=hypothesis,
        task=task,
    )
    _validate_approved_contract(
        prepared=prepared,
        result=result,
        run=run,
        frame_observation=frame_observation,
        evidence_observation=evidence_observation,
    )

    frame_id = generate_deterministic_analysis_frame_id(run.execution_run_id)
    evidence_id = generate_deterministic_evidence_id(run.execution_run_id)
    analysis_frame = AnalysisFrame(
        analysis_frame_id=frame_id,
        data_profile_id=profile.profile_id,
        frame_hash=frame_observation.frame_hash,
        frame_ref=frame_observation.frame_ref,
        column_refs=list(frame_observation.column_refs),
        row_filter_description=frame_observation.row_filter_description,
        created_at=run.created_at,
    )
    evidence = Evidence(
        evidence_id=evidence_id,
        hypothesis_id=hypothesis.hypothesis_id,
        profile_id=profile.profile_id,
        analysis_frame_ref=str(frame_id),
        execution_run_ref=str(run.execution_run_id),
        evidence_type=evidence_observation.evidence_type,
        method=evidence_observation.method,
        parameters=[
            parameter.model_copy(deep=True) for parameter in evidence_observation.parameters
        ],
        provenance=EvidenceProvenance(
            analysis_frame_ref=str(frame_id),
            execution_run_ref=str(run.execution_run_id),
            code_reference=evidence_observation.code_reference,
            environment_reference=evidence_observation.environment_reference,
            artifact_paths=list(evidence_observation.artifact_refs),
        ),
        result_summary=evidence_observation.result_summary.model_copy(deep=True),
        artifact_refs=list(evidence_observation.artifact_refs),
        limitations=list(evidence_observation.limitations),
        created_at=run.created_at,
    )
    frame_fingerprint = compute_analysis_frame_fingerprint(analysis_frame)
    evidence_fingerprint = compute_evidence_fingerprint(evidence)
    operations = (
        _execution_operation(
            session_id,
            PlannerOperationType.CREATE_ANALYSIS_FRAME,
            analysis_frame,
            PlannerNodeName.REVIEW_EXECUTION,
            operation_id=uuid5(
                EVIDENCE_ADMISSION_NAMESPACE,
                f"{contract_version}:{run.execution_run_id}:analysis_frame_operation:0",
            ),
            created_at=run.created_at,
        ),
        _execution_operation(
            session_id,
            PlannerOperationType.CREATE_EVIDENCE,
            evidence,
            PlannerNodeName.VALIDATE_EVIDENCE,
            operation_id=uuid5(
                EVIDENCE_ADMISSION_NAMESPACE,
                f"{contract_version}:{run.execution_run_id}:evidence_operation:0",
            ),
            created_at=run.created_at,
        ),
    )

    return EvidenceAdmissionPlan(
        contract_version=contract_version,
        execution_run_id=run.execution_run_id,
        task_id=task.task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        data_profile_id=profile.profile_id,
        dispatch_idempotency_key=run.dispatch_idempotency_key or "",
        lease_epoch=run.lease_epoch,
        finalization_owner=run.finalizer_owner_id or "",
        finalization_fencing_epoch=run.finalization_fencing_epoch or 0,
        expected_attempt_version=run.attempt_version,
        inbox_id=inbox.inbox_id,
        inbox_result_digest=inbox.result_digest,
        analysis_frame_id=frame_id,
        evidence_id=evidence_id,
        analysis_frame_fingerprint=frame_fingerprint,
        evidence_fingerprint=evidence_fingerprint,
        analysis_frame=analysis_frame,
        evidence=evidence,
        operations=operations,
    )


def _validate_transaction_authority(
    *,
    run: ExecutionRunRecord,
    inbox: ExecutionInboxRecord,
    result: ExecutionReceiptEnvelope,
) -> None:
    if (
        run.status != ExecutionRunStatus.EVIDENCE_ADMITTING
        or not run.dispatch_idempotency_key
        or run.finalizer_owner_id is None
        or run.finalization_fencing_epoch is None
        or run.finalization_claimed_at is None
        or run.finalization_expires_at is None
        or run.attempt_version < 1
    ):
        raise ValueError(
            "Evidence admission requires a complete EVIDENCE_ADMITTING attempt authority."
        )
    if (
        inbox.status != "pending"
        or inbox.executor_status != "completed"
        or inbox.execution_run_id != run.execution_run_id
        or inbox.dispatch_idempotency_key != run.dispatch_idempotency_key
        or inbox.lease_epoch != run.lease_epoch
        or inbox.method_id != run.method_id
    ):
        raise EvidenceAdmissionConflictError(
            "Evidence admission inbox does not match the claimed durable attempt."
        )
    if canonical_sha256(inbox.serialized_observations) != canonical_sha256(
        result.model_dump(mode="json")
    ) or inbox.result_digest != result_payload_digest(inbox.serialized_observations):
        raise EvidenceAdmissionConflictError(
            "Evidence admission result does not match the authoritative inbox payload."
        )


def _validate_durable_lineage(
    *,
    prepared: PreparedExecution,
    run: ExecutionRunRecord,
    profile: DataProfileRecord,
    hypothesis: HypothesisRecord,
    task: TaskRecord,
) -> None:
    try:
        prepared_task_id = UUID(prepared.task_ref)
        prepared_hypothesis_id = UUID(prepared.hypothesis_ref or "")
        prepared_profile_id = UUID(prepared.data_profile_ref)
        prepared_run_ref = UUID(prepared.execution_run_ref or "")
    except ValueError as exc:
        raise ValueError("Prepared execution references must be canonical UUID strings.") from exc
    if (
        run.task_id != task.task_id
        or run.hypothesis_id != hypothesis.hypothesis_id
        or hypothesis.task_id != task.task_id
        or hypothesis.profile_id != profile.profile_id
        or task.profile_id != profile.profile_id
        or prepared_task_id != task.task_id
        or prepared_hypothesis_id != hypothesis.hypothesis_id
        or prepared_profile_id != profile.profile_id
        or prepared_run_ref != run.execution_run_id
        or prepared.execution_run_id != run.execution_run_id
        or prepared.dispatch_idempotency_key != run.dispatch_idempotency_key
        or prepared.lease_epoch != run.lease_epoch
    ):
        raise ValueError("Authoritative context identity mismatch during evidence admission.")
    if (
        profile.lifecycle_state != DataProfileLifecycleState.ACTIVE
        or not profile.accepted_as_ground_truth
        or task.lifecycle_state != TaskLifecycleState.ACTIVE
        or task.task_kind != TaskKind.ANALYTICAL
        or hypothesis.status != HypothesisStatus.TESTING
    ):
        raise ValueError("Durable analytical lineage is not eligible for Evidence admission.")
    if (
        hypothesis.variables != prepared.specification.variable_bindings
        or hypothesis.scope != prepared.specification.scope
        or hypothesis.validation_method != prepared.specification.validation_method
        or hypothesis.evidence_expectation != prepared.specification.evidence_expectation
        or task.variables != prepared.specification.variable_bindings
        or task.evidence_expectation != prepared.specification.evidence_expectation
    ):
        raise ValueError("Durable Task/Hypothesis contract disagrees with approved execution.")


def _validate_approved_contract(
    *,
    prepared: PreparedExecution,
    result: ExecutionReceiptEnvelope,
    run: ExecutionRunRecord,
    frame_observation: AnalysisFrameObservation,
    evidence_observation: EvidenceObservation,
) -> None:
    approved_parameters = prepared.specification.method_parameters
    approved_bindings = prepared.specification.variable_bindings
    if (
        prepared.specification.executor_id != run.executor_type
        or prepared.specification.validation_method != run.method_id
        or prepared.hypothesis.validation_method != run.method_id
        or prepared.hypothesis.variables != approved_bindings
        or prepared.hypothesis.scope != prepared.specification.scope
        or evidence_observation.method != run.method_id
        or method_parameter_hash(approved_parameters) != run.parameter_hash
        or method_parameter_hash(evidence_observation.parameters) != run.parameter_hash
        or frame_observation.column_refs != approved_bindings
    ):
        raise ValueError("Result observation does not match the approved execution contract.")
