"""Bypass restriction tests for Package 3."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from application.orchestrator.planner_commit import commit_planner_operations
from package2_helpers import persist_package2_lineage
from schemas.enums import (
    HypothesisStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskLifecycleState,
)
from schemas.planner_operations import PlannerOperation


def test_generic_planner_operation_cannot_create_discovery(db_session: Session) -> None:
    lineage = persist_package2_lineage(db_session)

    op = PlannerOperation(
        operation_id=uuid4(),
        operation_type=PlannerOperationType.CREATE_DISCOVERY,
        produced_by_node=PlannerNodeName.EVALUATE_HYPOTHESIS,
        approval_state=PlannerOperationApprovalState.APPROVED,
        payload={
            "hypothesis_id": str(lineage.hypothesis_id),
            "evidence_ids": [str(lineage.evidence_id)],
            "claim": {"statement": "Bypass claim"},
            "epistemic_status": "supported",
            "scope": "Bypass scope",
            "validity_basis": {},
        },
    )

    result = commit_planner_operations(db_session, [op])
    assert op.operation_id in result.failed_operation_ids
    assert (
        "Discovery creation is owned by AtomicDiscoveryAdmissionService"
        in result.errors[op.operation_id]
    )


def test_generic_planner_operation_cannot_transition_hypothesis_evaluated(
    db_session: Session,
) -> None:
    lineage = persist_package2_lineage(db_session)

    op = PlannerOperation(
        operation_id=uuid4(),
        operation_type=PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
        produced_by_node=PlannerNodeName.EVALUATE_HYPOTHESIS,
        approval_state=PlannerOperationApprovalState.APPROVED,
        payload={
            "hypothesis_id": str(lineage.hypothesis_id),
            "status": HypothesisStatus.EVALUATED,
        },
    )

    result = commit_planner_operations(db_session, [op])
    assert op.operation_id in result.failed_operation_ids
    assert (
        "Hypothesis transition to EVALUATED is owned by Discovery Admission cutover"
        in result.errors[op.operation_id]
    )


def test_generic_planner_operation_cannot_complete_analytical_task(db_session: Session) -> None:
    lineage = persist_package2_lineage(db_session)

    op = PlannerOperation(
        operation_id=uuid4(),
        operation_type=PlannerOperationType.CHANGE_TASK_STATE,
        produced_by_node=PlannerNodeName.MANAGE_TASKS,
        approval_state=PlannerOperationApprovalState.APPROVED,
        payload={
            "task_id": str(lineage.task_id),
            "lifecycle_state": TaskLifecycleState.COMPLETED,
        },
    )

    result = commit_planner_operations(db_session, [op])
    assert op.operation_id in result.failed_operation_ids
    assert (
        "Terminal analytical Task completion is owned by Discovery Admission cutover"
        in result.errors[op.operation_id]
    )
