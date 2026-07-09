from __future__ import annotations

from uuid import UUID, uuid4

from agents.planner.nodes import manage_tasks
from agents.planner.types import (
    ConflictFlagDraft,
    ConflictFlagOperationPayload,
    State,
    TaskUpdateDraft,
    TaskUpdateOperationPayload,
)
from application.orchestrator.planner_commit import commit_planner_operations
from repositories import (
    AssumptionRepository,
    ObjectiveRepository,
    ObjectiveRevisionRepository,
    PlannerOperationRepository,
    SessionFrameRepository,
    TaskRepository,
)
from schemas.artifacts import Assumption, Objective, SessionFrame, Task
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
from schemas.planner_operations import PlannerOperation


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
    return Task(**payload).model_dump(mode="json")


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
    produced_by_node: PlannerNodeName = PlannerNodeName.MANAGE_TASKS,
) -> PlannerOperation:
    return PlannerOperation(
        operation_type=operation_type,
        payload=payload,
        produced_by_node=produced_by_node,
        approval_state=approval_state,
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
    assert "target_object_id" not in PlannerOperation.model_fields


def test_pending_operation_does_not_mutate_target_state(db_session) -> None:
    task_id = uuid4()
    operation = PlannerOperationRepository(db_session).create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_TASK,
            payload=build_task_payload(task_id),
        )
    )

    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])

    assert result.committed_operation_ids == []
    assert result.skipped_operation_ids == [operation.operation_id]
    assert TaskRepository(db_session).get_by_id(task_id) is None


def test_approved_create_task_operation_dispatches_through_commit(db_session) -> None:
    task_id = uuid4()
    repository = PlannerOperationRepository(db_session)
    operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_TASK,
            payload=build_task_payload(task_id),
            approval_state=PlannerOperationApprovalState.APPROVED,
        )
    )

    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])
    committed_operation = repository.get_by_id(operation.operation_id)

    assert result.committed_operation_ids == [operation.operation_id]
    assert TaskRepository(db_session).get_by_id(task_id) is not None
    assert committed_operation is not None
    assert committed_operation.approval_state == PlannerOperationApprovalState.COMMITTED
    assert committed_operation.committed_at is not None


def test_commit_reports_handler_failures_without_rollback_contract(db_session) -> None:
    operation = PlannerOperationRepository(db_session).create(
        build_operation(
            operation_type=PlannerOperationType.UPDATE_TASK,
            payload={"title": "Missing task id."},
            approval_state=PlannerOperationApprovalState.APPROVED,
        )
    )

    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])
    reloaded = PlannerOperationRepository(db_session).get_by_id(operation.operation_id)

    assert result.committed_operation_ids == []
    assert result.failed_operation_ids == [operation.operation_id]
    assert operation.operation_id in result.errors
    assert "task_id" in result.errors[operation.operation_id]
    assert reloaded is not None
    assert reloaded.approval_state == PlannerOperationApprovalState.APPROVED


def test_rejected_operation_is_not_committed(db_session) -> None:
    task_id = uuid4()
    operation = PlannerOperationRepository(db_session).create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_TASK,
            payload=build_task_payload(task_id),
            approval_state=PlannerOperationApprovalState.REJECTED,
        )
    )

    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])

    assert result.committed_operation_ids == []
    assert result.skipped_operation_ids == [operation.operation_id]
    assert TaskRepository(db_session).get_by_id(task_id) is None


def test_manage_tasks_produces_planner_operation_not_direct_mutation(db_session) -> None:
    task_payload = build_task_payload()
    state = State(query="create task", task_create_payloads=[task_payload])

    result_state = manage_tasks(state, None)

    assert isinstance(result_state.task_create_payloads[0], Task)
    assert len(result_state.planner_operations) == 1
    operation = result_state.planner_operations[0]
    assert operation.operation_type == PlannerOperationType.CREATE_TASK
    assert operation.approval_state == PlannerOperationApprovalState.PENDING
    assert "task_id" in operation.payload
    assert TaskRepository(db_session).list() == []


def test_operation_payload_methods_return_named_payload_models() -> None:
    task_id = uuid4()
    assumption_id = uuid4()

    task_payload = TaskUpdateDraft(
        task_id=task_id,
        title="Refine churn task",
    ).operation_payload()
    flag_payload = ConflictFlagDraft(
        assumption_id=assumption_id,
        reason="Discovery contradicts assumption.",
    ).operation_payload()

    assert isinstance(task_payload, TaskUpdateOperationPayload)
    assert task_payload.task_id == task_id
    assert task_payload.title == "Refine churn task"
    assert isinstance(flag_payload, ConflictFlagOperationPayload)
    assert flag_payload.assumption_id == assumption_id
    assert flag_payload.target_object_type == "assumption"


def test_commit_updates_session_frame_after_task_change(db_session) -> None:
    task_id = uuid4()
    frame_id = uuid4()
    repository = PlannerOperationRepository(db_session)
    task_operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_TASK,
            payload=build_task_payload(task_id),
            approval_state=PlannerOperationApprovalState.APPROVED,
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
            payload={
                "objective_id": str(objective.objective_id),
                "statement": "Understand churn drivers.",
                "revision_reason": "Refine objective from planner operation.",
            },
            approval_state=PlannerOperationApprovalState.APPROVED,
            produced_by_node=PlannerNodeName.MANAGE_OBJECTIVE,
        )
    )
    assumption_operation = repository.create(
        build_operation(
            operation_type=PlannerOperationType.UPDATE_ASSUMPTION_STATE,
            payload={
                "assumption_id": str(assumption.assumption_id),
                "status": AssumptionStatus.FLAGGED.value,
            },
            approval_state=PlannerOperationApprovalState.APPROVED,
            produced_by_node=PlannerNodeName.MANAGE_ASSUMPTIONS,
        )
    )

    result = commit_planner_operations(
        db_session,
        operation_ids=[objective_operation.operation_id, assumption_operation.operation_id],
    )

    updated_objective = ObjectiveRepository(db_session).get_by_id(objective.objective_id)
    updated_assumption = AssumptionRepository(db_session).get_by_id(assumption.assumption_id)
    objective_revisions = ObjectiveRevisionRepository(db_session).list_for_objective(
        objective.objective_id
    )
    assert result.failed_operation_ids == []
    assert updated_objective is not None
    assert updated_objective.statement == "Understand churn drivers."
    assert len(objective_revisions) == 1
    assert objective_revisions[0].previous_title == "Churn Investigation"
    assert objective_revisions[0].previous_description == "Understand churn."
    assert objective_revisions[0].new_description == "Understand churn drivers."
    assert objective_revisions[0].changed_fields == ["statement"]
    assert objective_revisions[0].revision_reason == (
        "Refine objective from planner operation."
    )
    assert objective_revisions[0].planner_operation_id == str(
        objective_operation.operation_id
    )
    assert updated_assumption is not None
    assert updated_assumption.status == AssumptionStatus.FLAGGED
