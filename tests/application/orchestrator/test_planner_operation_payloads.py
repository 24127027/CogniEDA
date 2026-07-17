from uuid import uuid4

import pytest
from pydantic import ValidationError

from application.orchestrator.planner_commit import commit_planner_operations
from repositories import PlannerOperationRepository, TaskRepository
from schemas.artifacts import Task
from schemas.enums import (
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskKind,
    TaskLifecycleState,
)
from schemas.planner_operations import PlannerOperation, TaskUpdateOperationPayload


def _task() -> Task:
    return Task(
        title="Investigate churn signal",
        description="Evaluate whether spend is associated with churn.",
        lifecycle_state=TaskLifecycleState.ACTIVE,
        task_kind=TaskKind.ANALYTICAL,
        variables=["monthly_spend", "churned"],
        evidence_expectation="A scoped statistical test result.",
    )


def test_typed_payload_updates_target_without_legacy_target_field(db_session) -> None:
    task = TaskRepository(db_session).create(_task())
    payload = TaskUpdateOperationPayload(
        task_id=task.task_id,
        title="Investigate retained customers",
    )
    operation = PlannerOperationRepository(db_session).create(
        PlannerOperation(
            operation_type=PlannerOperationType.UPDATE_TASK,
            payload=payload.model_dump(mode="json"),
            produced_by_node=PlannerNodeName.MANAGE_TASKS,
            approval_state=PlannerOperationApprovalState.APPROVED,
        )
    )

    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])

    updated = TaskRepository(db_session).get_by_id(task.task_id)
    persisted = PlannerOperationRepository(db_session).get_by_id(operation.operation_id)
    assert result.committed_operation_ids == [operation.operation_id]
    assert updated is not None
    assert updated.title == "Investigate retained customers"
    assert persisted is not None
    assert persisted.approval_state == PlannerOperationApprovalState.COMMITTED


def test_typed_payload_rejects_unknown_fields(db_session) -> None:
    task = TaskRepository(db_session).create(_task())
    operation = PlannerOperationRepository(db_session).create(
        PlannerOperation(
            operation_type=PlannerOperationType.UPDATE_TASK,
            payload={
                "task_id": str(task.task_id),
                "title": "This update must not apply.",
                "unexpected": True,
            },
            produced_by_node=PlannerNodeName.MANAGE_TASKS,
            approval_state=PlannerOperationApprovalState.APPROVED,
        )
    )

    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])

    unchanged = TaskRepository(db_session).get_by_id(task.task_id)
    assert result.failed_operation_ids == [operation.operation_id]
    assert unchanged is not None
    assert unchanged.title == task.title


def test_typed_payload_rejects_mismatched_legacy_target(db_session) -> None:
    target_task = TaskRepository(db_session).create(_task())
    payload_task = TaskRepository(db_session).create(_task())
    operation = PlannerOperationRepository(db_session).create(
        PlannerOperation(
            operation_type=PlannerOperationType.UPDATE_TASK,
            target_object_id=target_task.task_id,
            payload=TaskUpdateOperationPayload(
                task_id=payload_task.task_id,
                title="This update must not apply.",
            ).model_dump(mode="json"),
            produced_by_node=PlannerNodeName.MANAGE_TASKS,
            approval_state=PlannerOperationApprovalState.APPROVED,
        )
    )

    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])

    assert result.failed_operation_ids == [operation.operation_id]
    assert TaskRepository(db_session).get_by_id(target_task.task_id) == target_task
    assert TaskRepository(db_session).get_by_id(payload_task.task_id) == payload_task


def test_payload_models_forbid_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="unexpected"):
        TaskUpdateOperationPayload(task_id=uuid4(), unexpected=True)
