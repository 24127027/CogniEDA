"""Domain logic for scientific finalization of execution attempts."""

from __future__ import annotations

import json
from hashlib import sha256
from math import isfinite
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

from application.orchestrator.execution_contracts import (
    AnalysisFrameObservation,
    ExecutorResult,
    PreparedExecution,
)
from db.models import ExecutionRunRecord
from memory.session_frame import SessionFrameBuilder
from repositories import (
    DataProfileRepository,
    EvidenceRepository,
    HypothesisRepository,
    TaskRepository,
)
from schemas.artifacts import Discovery, Evidence, Hypothesis, SessionFrame
from schemas.common import DiscoveryClaim, EvaluationThresholds, EvidenceProvenance, ValidityBasis
from schemas.enums import (
    DiscoveryEpistemicStatus,
    HypothesisEvidenceOutcome,
    HypothesisStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskLifecycleState,
)
from schemas.planner_operations import PlannerOperation
from schemas.provenance import AnalysisFrame


def _method_parameter_hash(parameters: list[Any]) -> str:
    """Hash typed method parameters deterministically for contract/result comparison."""
    payload = [
        parameter.model_dump(mode="json") if isinstance(parameter, BaseModel) else parameter
        for parameter in parameters
    ]
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _materialize_analysis_frame(
    observation: AnalysisFrameObservation,
    profile_id: UUID,
) -> AnalysisFrame:
    """Create immutable provenance only when executor output crosses into commit work."""
    return AnalysisFrame(
        data_profile_id=profile_id,
        frame_hash=observation.frame_hash,
        frame_ref=observation.frame_ref,
        column_refs=observation.column_refs,
        row_filter_description=observation.row_filter_description,
    )


def _execution_operation(
    session_id: str | None,
    operation_type: PlannerOperationType,
    payload: BaseModel,
    produced_by_node: PlannerNodeName,
) -> PlannerOperation:
    """Serialize a typed draft only at the PlannerOperation persistence boundary."""
    return PlannerOperation(
        session_id=session_id,
        operation_type=operation_type,
        payload=payload.model_dump(mode="json"),
        produced_by_node=produced_by_node,
        approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
    )


def _evaluate_deterministically(
    evidence: Evidence,
    rule: EvaluationThresholds,
    *,
    validation_method: str,
) -> HypothesisEvidenceOutcome:
    """Evaluate the only supported method from admitted metrics, never executor advice."""
    if validation_method != "deterministic_test":
        return HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE
    if rule.p_value is None or rule.effect_size is not None or rule.metric_thresholds:
        return HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE
    metric_name = evidence.result_summary.metric_name
    metric_value = evidence.result_summary.metric_value

    if (
        metric_name != "p_value"
        or not isinstance(metric_value, (int, float))
        or isinstance(metric_value, bool)
    ):
        return HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE

    if not isfinite(metric_value) or not 0.0 <= metric_value <= 1.0:
        return HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE
    if not 0.0 < rule.p_value <= 1.0:
        return HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE
    if metric_value < rule.p_value:
        return HypothesisEvidenceOutcome.SUPPORTS
    return HypothesisEvidenceOutcome.INCONCLUSIVE


def _discovery_conclusion(
    hypothesis: Hypothesis,
    evaluation: HypothesisEvidenceOutcome,
) -> tuple[DiscoveryEpistemicStatus, str]:
    if evaluation == HypothesisEvidenceOutcome.SUPPORTS:
        return DiscoveryEpistemicStatus.SUPPORTED, hypothesis.statement
    if evaluation == HypothesisEvidenceOutcome.CONTRADICTS:
        return (
            DiscoveryEpistemicStatus.CONTRADICTED,
            "Available evidence contradicts the stated hypothesis within scope "
            f"{hypothesis.scope}.",
        )
    if evaluation == HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE:
        return (
            DiscoveryEpistemicStatus.INSUFFICIENT_EVIDENCE,
            "Available evidence is insufficient to evaluate the stated hypothesis "
            f"within scope {hypothesis.scope}.",
        )
    return (
        DiscoveryEpistemicStatus.INCONCLUSIVE,
        "Available evidence is inconclusive for the stated hypothesis within scope "
        f"{hypothesis.scope}.",
    )


def _discovery_from_evaluation(
    *,
    hypothesis: Hypothesis,
    evidence: Evidence,
    analysis_frame_ref: str,
    decision_rule: EvaluationThresholds,
    evaluation: HypothesisEvidenceOutcome,
    evaluation_note: str | None,
    code_reference: str | None,
    environment_reference: str | None,
) -> Discovery:
    """Produce a bounded Discovery without interpreting free text or Assumptions."""
    status, statement = _discovery_conclusion(hypothesis, evaluation)

    return Discovery(
        hypothesis_id=hypothesis.hypothesis_id,
        evidence_ids=[evidence.evidence_id],
        claim=DiscoveryClaim(
            statement=statement,
            scope=hypothesis.scope,
            result=evaluation.value,
        ),
        epistemic_status=status,
        scope=hypothesis.scope,
        validity_basis=ValidityBasis(
            data_profile_id=hypothesis.profile_id,
            analysis_frame_refs=[analysis_frame_ref],
            hypothesis_id=hypothesis.hypothesis_id,
            evidence_ids=[evidence.evidence_id],
            method=evidence.method,
            parameters=evidence.parameters,
            code_reference=code_reference,
            environment_reference=environment_reference,
            decision_rule=decision_rule,
            strength=evaluation.value,
            uncertainty=evaluation_note,
            assumptions_excluded_from_inference=True,
            invalidators=["DataProfile, method, parameter, code, or environment change."],
        ),
    )


def process_scientific_result(
    session: Session,
    session_id: str | None,
    prepared: PreparedExecution,
    result: ExecutorResult,
    run: ExecutionRunRecord,
    profile_id: UUID,
    hypothesis_id: UUID,
    task_id: UUID,
) -> tuple[bool, list[PlannerOperation]]:
    """
    Validate and evaluate an executor result, returning operations to commit.
    Returns (success, operations).
    """
    operations: list[PlannerOperation] = []

    analysis_frame = _materialize_analysis_frame(result.analysis_frame, profile_id)
    operations.append(
        _execution_operation(
            session_id,
            PlannerOperationType.CREATE_ANALYSIS_FRAME,
            analysis_frame,
            PlannerNodeName.REVIEW_EXECUTION,
        )
    )

    if result.status == "failed":
        operations.extend(
            _execution_failure_operations(session_id, run.execution_run_id, hypothesis_id)
        )
        return False, operations

    # Validate Evidence
    observation = result.evidence_observation
    if observation is None:
        operations.extend(
            _execution_failure_operations(session_id, run.execution_run_id, hypothesis_id)
        )
        return False, operations

    if (
        result.execution_run.executor_type != run.executor_type
        or prepared.specification.executor_id != run.executor_type
        or prepared.specification.validation_method != run.method_id
        or _method_parameter_hash(prepared.specification.method_parameters) != run.parameter_hash
        or observation.method != prepared.specification.validation_method
        or result.execution_run.method_id != prepared.specification.validation_method
        or observation.parameters != prepared.specification.method_parameters
        or result.analysis_frame.column_refs != prepared.specification.variable_bindings
        or result.execution_run.parameter_hash
        != _method_parameter_hash(prepared.specification.method_parameters)
    ):
        operations.extend(
            _execution_failure_operations(session_id, run.execution_run_id, hypothesis_id)
        )
        return False, operations

    evidence = Evidence(
        hypothesis_id=hypothesis_id,
        profile_id=profile_id,
        analysis_frame_ref=str(analysis_frame.analysis_frame_id),
        execution_run_ref=str(run.execution_run_id),
        evidence_type=observation.evidence_type,
        method=observation.method,
        parameters=observation.parameters,
        provenance=EvidenceProvenance(
            analysis_frame_ref=str(analysis_frame.analysis_frame_id),
            execution_run_ref=str(run.execution_run_id),
            code_reference=observation.code_reference,
            environment_reference=observation.environment_reference,
            artifact_paths=observation.artifact_refs,
        ),
        result_summary=observation.result_summary,
        artifact_refs=observation.artifact_refs,
        limitations=observation.limitations,
    )
    operations.append(
        _execution_operation(
            session_id,
            PlannerOperationType.CREATE_EVIDENCE,
            evidence,
            PlannerNodeName.VALIDATE_EVIDENCE,
        )
    )
    operations.append(
        PlannerOperation(
            session_id=session_id,
            operation_type=PlannerOperationType.UPDATE_EXECUTION_RUN,
            payload={"execution_run_id": str(run.execution_run_id), "status": "completed"},
            produced_by_node=PlannerNodeName.VALIDATE_EVIDENCE,
            approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
        )
    )

    # Evaluate Hypothesis
    evaluation = result.evaluation
    if evaluation is None:
        return True, operations

    hypothesis = HypothesisRepository(session).get_by_id(hypothesis_id)
    task = TaskRepository(session).get_by_id(task_id)
    profile = DataProfileRepository(session).get_by_id(profile_id) if hypothesis else None

    if hypothesis is None or task is None or profile is None:
        return True, operations

    if not evaluation.finalize:
        operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
                payload={
                    "hypothesis_id": str(hypothesis_id),
                    "status": HypothesisStatus.AWAITING_ADDITIONAL_EVIDENCE.value,
                },
                produced_by_node=PlannerNodeName.EVALUATE_HYPOTHESIS,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            )
        )
        return True, operations

    computed_outcome = _evaluate_deterministically(
        evidence,
        prepared.specification.decision_rule,
        validation_method=prepared.specification.validation_method,
    )
    if evaluation.outcome != computed_outcome:
        operations = [
            op
            for op in operations
            if op.operation_type
            not in (PlannerOperationType.CREATE_EVIDENCE, PlannerOperationType.UPDATE_EXECUTION_RUN)
        ]
        operations.extend(
            _execution_failure_operations(session_id, run.execution_run_id, hypothesis_id)
        )
        return False, operations

    admitted_evidence = EvidenceRepository(session).list_for_hypothesis(hypothesis_id)
    discovery = _discovery_from_evaluation(
        hypothesis=hypothesis,
        evidence=evidence,
        analysis_frame_ref=str(analysis_frame.analysis_frame_id),
        decision_rule=prepared.specification.decision_rule,
        evaluation=computed_outcome,
        evaluation_note=evaluation.note,
        code_reference=observation.code_reference,
        environment_reference=observation.environment_reference,
    )
    evidence_ids = [
        *(e.evidence_id for e in admitted_evidence),
        evidence.evidence_id,
    ]
    discovery = discovery.model_copy(
        update={
            "evidence_ids": evidence_ids,
            "validity_basis": discovery.validity_basis.model_copy(
                update={"evidence_ids": evidence_ids}
            ),
        }
    )
    status_by_outcome = {
        HypothesisEvidenceOutcome.SUPPORTS: HypothesisStatus.CONFIRMED,
        HypothesisEvidenceOutcome.CONTRADICTS: HypothesisStatus.CONTRADICTED,
        HypothesisEvidenceOutcome.INCONCLUSIVE: HypothesisStatus.INCONCLUSIVE,
        HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE: HypothesisStatus.INSUFFICIENT_EVIDENCE,
    }
    final_status = status_by_outcome[computed_outcome]
    completed_task = task.model_copy(update={"lifecycle_state": TaskLifecycleState.COMPLETED})
    frame = SessionFrame(
        frame_topic="Execution Result",
        objective_snapshot="Ad-hoc execution",
        frame_outcome=discovery.claim.statement,
        data_profile_summaries=[SessionFrameBuilder._profile_summary(profile)],
        active_data_profile_refs=[profile.profile_id],
        active_task_refs=[completed_task.task_id],
        relevant_discoveries=[SessionFrameBuilder._discovery_summary(discovery)],
        relevant_discovery_refs=[discovery.discovery_id],
        supporting_evidence=[SessionFrameBuilder._evidence_summary(evidence)],
        supporting_evidence_refs=[evidence.evidence_id],
        inclusion_reasons={
            str(profile.profile_id): "accepted DataProfile for the completed execution",
            str(completed_task.task_id): "completed analytical Task audit reference",
            str(discovery.discovery_id): "new evidence-bound Discovery",
            str(evidence.evidence_id): "admitted Evidence for the new Discovery",
        },
        key_warnings=[
            "Assumptions are excluded from execution-result conclusion context.",
            "Completed Task and Hypothesis summaries are not active planning context.",
        ],
    )
    operations.extend(
        [
            _execution_operation(
                session_id,
                PlannerOperationType.CREATE_DISCOVERY,
                discovery,
                PlannerNodeName.EVALUATE_HYPOTHESIS,
            ),
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
                payload={
                    "hypothesis_id": str(hypothesis_id),
                    "status": final_status.value,
                },
                produced_by_node=PlannerNodeName.EVALUATE_HYPOTHESIS,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            ),
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_TASK_STATE,
                payload={
                    "task_id": str(task_id),
                    "lifecycle_state": TaskLifecycleState.COMPLETED.value,
                },
                produced_by_node=PlannerNodeName.EVALUATE_HYPOTHESIS,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            ),
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_SESSION_FRAME,
                payload=frame.model_dump(mode="json"),
                produced_by_node=PlannerNodeName.EVALUATE_HYPOTHESIS,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            ),
        ]
    )
    return True, operations


def _execution_failure_operations(
    session_id: str | None,
    execution_run_id: UUID,
    hypothesis_id: UUID,
) -> list[PlannerOperation]:
    return [
        PlannerOperation(
            session_id=session_id,
            operation_type=PlannerOperationType.UPDATE_EXECUTION_RUN,
            payload={"execution_run_id": str(execution_run_id), "status": "execution_failed"},
            produced_by_node=PlannerNodeName.REVIEW_EXECUTION,
            approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
        ),
        PlannerOperation(
            session_id=session_id,
            operation_type=PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
            payload={
                "hypothesis_id": str(hypothesis_id),
                "status": HypothesisStatus.APPROVED.value,
            },
            produced_by_node=PlannerNodeName.REVIEW_EXECUTION,
            approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
        ),
    ]
