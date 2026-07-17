from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from agents.planner.nodes import manage_tasks
from agents.planner.types import State, TaskCreateDraft
from application.orchestrator.planner_commit import commit_planner_operations
from repositories import (
    AssumptionRepository,
    ObjectiveRepository,
    PlannerOperationRepository,
    SessionFrameRepository,
    TaskRepository,
)
from schemas.artifacts import Assumption, Objective, SessionFrame
from schemas.common import TaskContextSummary
from schemas.enums import (
    AssumptionSource,
    AssumptionStatus,
    AssumptionTestability,
    ConfidenceLevel,
    ObjectiveStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskKind,
    TaskLifecycleState,
)
from schemas.planner_operations import PlannerOperation, TaskCreateOperationPayload


def build_task_payload(task_id: UUID | None = None, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": task_id or uuid4(),
        "title": "Investigate churn signal",
        "description": "Evaluate whether spend is associated with churn.",
        "lifecycle_state": TaskLifecycleState.ACTIVE,
        "task_kind": TaskKind.ANALYTICAL,
        "variables": ["monthly_spend", "churned"],
        "evidence_expectation": "A scoped statistical test result.",
    }
    payload.update(overrides)
    return TaskCreateOperationPayload(**payload).model_dump(mode="json", exclude_none=True)


def build_assumption_payload(
    assumption_id: UUID | None = None,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "assumption_id": assumption_id or uuid4(),
        "statement": "Rows represent customers.",
        "scope": "Customer churn analysis.",
        "source": AssumptionSource.USER,
        "testability": AssumptionTestability.UNTESTABLE_IN_PROJECT,
        "basis": "User supplied dataset contract.",
        "confidence": ConfidenceLevel.MEDIUM,
        "status": AssumptionStatus.ACTIVE,
    }
    payload.update(overrides)
    return Assumption(**payload).model_dump(mode="json")


def build_operation(
    *,
    operation_type: PlannerOperationType,
    payload: dict[str, object],
    approval_state: PlannerOperationApprovalState = PlannerOperationApprovalState.PENDING,
    target_object_id: UUID | None = None,
    target_object_type: str | None = None,
    produced_by_node: PlannerNodeName = PlannerNodeName.MANAGE_TASKS,
) -> PlannerOperation:
    return PlannerOperation(
        operation_type=operation_type,
        target_object_id=target_object_id,
        target_object_type=target_object_type,
        payload=payload,
        produced_by_node=produced_by_node,
        approval_state=approval_state,
        approved_at=(
            datetime.now(UTC)
            if approval_state == PlannerOperationApprovalState.APPROVED
            else None
        ),
    )


def test_planner_operation_can_be_persisted_and_loaded(db_session) -> None:
    repository = PlannerOperationRepository(db_session)
    operation = build_operation(
        operation_type=PlannerOperationType.CREATE_TASK,
        payload=build_task_payload(),
    )

    persisted = repository.create(operation)
    loaded = repository.get_by_id(persisted.operation_id)

    assert loaded is not None
    assert loaded.operation_type == PlannerOperationType.CREATE_TASK
    assert loaded.payload["title"] == "Investigate churn signal"
    assert loaded.approval_state == PlannerOperationApprovalState.PENDING
    assert loaded.produced_by_node == PlannerNodeName.MANAGE_TASKS


def test_pending_operation_does_not_mutate_target_state(db_session) -> None:
    task_id = uuid4()
    operation = PlannerOperationRepository(db_session).create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_TASK,
            payload=build_task_payload(task_id),
            target_object_id=task_id,
            target_object_type="task",
        )
    )

    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])

    assert result.committed_operation_ids == []
    assert result.skipped_operation_ids == [operation.operation_id]
    assert TaskRepository(db_session).get_by_id(task_id) is None


def test_approved_create_task_operation_commits_atomically(db_session) -> None:
    task_id = uuid4()
    repository = PlannerOperationRepository(db_session)
    operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_TASK,
            payload=build_task_payload(task_id),
            approval_state=PlannerOperationApprovalState.APPROVED,
            target_object_id=task_id,
            target_object_type="task",
        )
    )

    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])
    committed_operation = repository.get_by_id(operation.operation_id)

    assert result.committed_operation_ids == [operation.operation_id]
    assert TaskRepository(db_session).get_by_id(task_id) is not None
    assert committed_operation is not None
    assert committed_operation.approval_state == PlannerOperationApprovalState.COMMITTED
    assert committed_operation.committed_at is not None


def test_commit_rolls_back_all_operations_if_one_operation_fails(db_session) -> None:
    task_id = uuid4()
    repository = PlannerOperationRepository(db_session)
    valid_operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_TASK,
            payload=build_task_payload(task_id),
            approval_state=PlannerOperationApprovalState.APPROVED,
            target_object_id=task_id,
            target_object_type="task",
        )
    )
    invalid_operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.UPDATE_TASK,
            payload={"title": "This target does not exist."},
            approval_state=PlannerOperationApprovalState.APPROVED,
            target_object_id=uuid4(),
            target_object_type="task",
        )
    )

    result = commit_planner_operations(
        db_session,
        operation_ids=[valid_operation.operation_id, invalid_operation.operation_id],
    )

    assert result.committed_operation_ids == []
    assert result.failed_operation_ids == [invalid_operation.operation_id]
    assert TaskRepository(db_session).get_by_id(task_id) is None
    assert repository.get_by_id(valid_operation.operation_id).approval_state == (
        PlannerOperationApprovalState.APPROVED
    )
    assert repository.get_by_id(invalid_operation.operation_id).approval_state == (
        PlannerOperationApprovalState.FAILED
    )


def test_rejected_operation_is_not_committed(db_session) -> None:
    task_id = uuid4()
    operation = PlannerOperationRepository(db_session).create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_TASK,
            payload=build_task_payload(task_id),
            approval_state=PlannerOperationApprovalState.REJECTED,
            target_object_id=task_id,
            target_object_type="task",
        )
    )

    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])

    assert result.committed_operation_ids == []
    assert result.skipped_operation_ids == [operation.operation_id]
    assert TaskRepository(db_session).get_by_id(task_id) is None


def test_commit_result_reports_committed_and_failed_operations(db_session) -> None:
    repository = PlannerOperationRepository(db_session)
    successful_operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_TASK,
            payload=build_task_payload(uuid4()),
            approval_state=PlannerOperationApprovalState.APPROVED,
            target_object_type="task",
        )
    )
    success = commit_planner_operations(
        db_session,
        operation_ids=[successful_operation.operation_id],
    )
    failed_operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.UPDATE_TASK,
            payload={"title": "Missing target"},
            approval_state=PlannerOperationApprovalState.APPROVED,
            target_object_id=uuid4(),
            target_object_type="task",
        )
    )

    failure = commit_planner_operations(db_session, operation_ids=[failed_operation.operation_id])

    assert success.committed_operation_ids == [successful_operation.operation_id]
    assert failure.failed_operation_ids == [failed_operation.operation_id]
    assert failed_operation.operation_id in failure.error_details
    assert "Task not found" in failure.error_details[failed_operation.operation_id]


def test_manage_tasks_produces_planner_operation_not_direct_mutation(db_session) -> None:
    task_draft = TaskCreateDraft(
        title="Investigate churn signal",
        description="Evaluate whether spend is associated with churn.",
        variables=["monthly_spend", "churned"],
        evidence_expectation="A scoped statistical test result.",
    )
    state = State(query="create task", task_create_payloads=[task_draft])

    result_state = manage_tasks(state, None)

    assert isinstance(result_state.task_create_payloads[0], TaskCreateDraft)
    assert len(result_state.planner_operations) == 1
    operation = result_state.planner_operations[0]
    assert operation.operation_type == PlannerOperationType.CREATE_TASK
    assert operation.approval_state == PlannerOperationApprovalState.PENDING
    assert operation.target_object_id is None
    assert "task_id" not in operation.payload
    assert TaskRepository(db_session).list() == []


def test_task_create_payload_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        TaskCreateOperationPayload.model_validate(
            {
                "title": "Investigate churn signal",
                "description": "Evaluate whether spend is associated with churn.",
                "unexpected": "not a Task field",
            }
        )


def test_approved_task_create_without_id_allocates_id_only_at_commit(db_session) -> None:
    operation = PlannerOperationRepository(db_session).create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_TASK,
            payload=TaskCreateOperationPayload(
                title="Investigate churn signal",
                description="Evaluate whether spend is associated with churn.",
            ).model_dump(mode="json", exclude_none=True),
            approval_state=PlannerOperationApprovalState.APPROVED,
        )
    )

    assert operation.target_object_id is None
    assert "task_id" not in operation.payload
    assert TaskRepository(db_session).list() == []

    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])
    committed = PlannerOperationRepository(db_session).get_by_id(operation.operation_id)

    assert result.committed_operation_ids == [operation.operation_id]
    assert committed is not None
    assert committed.target_object_id is not None
    assert TaskRepository(db_session).get_by_id(committed.target_object_id) is not None


def test_commit_updates_session_frame_after_task_change(db_session) -> None:
    task_id = uuid4()
    frame_id = uuid4()
    repository = PlannerOperationRepository(db_session)
    task_operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_TASK,
            payload=build_task_payload(task_id),
            approval_state=PlannerOperationApprovalState.APPROVED,
            target_object_id=task_id,
            target_object_type="task",
        )
    )
    frame_payload = SessionFrame(
        session_frame_id=frame_id,
        frame_topic="task-frame",
        objective_snapshot="Understand churn drivers.",
        active_tasks=[
            TaskContextSummary(
                task_id=task_id,
                title="Investigate churn signal",
                lifecycle_state=TaskLifecycleState.ACTIVE.value,
            )
        ],
        active_task_refs=[task_id],
    ).model_dump(mode="json")
    frame_operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.UPDATE_SESSION_FRAME,
            payload=frame_payload,
            approval_state=PlannerOperationApprovalState.APPROVED,
            target_object_id=frame_id,
            target_object_type="session_frame",
            produced_by_node=PlannerNodeName.PROCESS_DECISION,
        )
    )

    result = commit_planner_operations(
        db_session,
        operation_ids=[task_operation.operation_id, frame_operation.operation_id],
    )

    assert result.committed_operation_ids == [
        task_operation.operation_id,
        frame_operation.operation_id,
    ]
    assert TaskRepository(db_session).get_by_id(task_id) is not None
    frame = SessionFrameRepository(db_session).get_by_id(frame_id)
    assert frame is not None
    assert frame.active_task_refs == [task_id]


def test_commit_updates_objective_and_assumption_through_operations(db_session) -> None:
    objective = ObjectiveRepository(db_session).create(
        Objective(
            title="Churn Investigation",
            statement="Understand churn.",
            status=ObjectiveStatus.ACTIVE,
        )
    )
    assumption = AssumptionRepository(db_session).create(
        Assumption(**build_assumption_payload())
    )
    repository = PlannerOperationRepository(db_session)
    objective_operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.UPDATE_OBJECTIVE,
            payload={"statement": "Understand churn drivers."},
            approval_state=PlannerOperationApprovalState.APPROVED,
            target_object_id=objective.objective_id,
            target_object_type="objective",
            produced_by_node=PlannerNodeName.MANAGE_OBJECTIVE,
        )
    )
    assumption_operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.UPDATE_ASSUMPTION_STATE,
            payload={"status": AssumptionStatus.FLAGGED.value},
            approval_state=PlannerOperationApprovalState.APPROVED,
            target_object_id=assumption.assumption_id,
            target_object_type="assumption",
            produced_by_node=PlannerNodeName.MANAGE_ASSUMPTIONS,
        )
    )

    result = commit_planner_operations(
        db_session,
        operation_ids=[objective_operation.operation_id, assumption_operation.operation_id],
    )

    updated_objective = ObjectiveRepository(db_session).get_by_id(objective.objective_id)
    updated_assumption = AssumptionRepository(db_session).get_by_id(assumption.assumption_id)
    assert result.failed_operation_ids == []
    assert updated_objective is not None
    assert updated_objective.statement == "Understand churn drivers."
    assert updated_assumption is not None
    assert updated_assumption.status == AssumptionStatus.FLAGGED
