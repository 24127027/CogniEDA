from __future__ import annotations

from uuid import UUID, uuid4

from agents.planner.nodes import manage_tasks
from agents.planner.types import (
    ConflictFlagDraft,
    State,
    TaskCreateDraft,
    TaskUpdateDraft,
)
from application.orchestrator.planner_commit import commit_planner_operations
from repositories import (
    AssumptionRepository,
    ObjectiveRepository,
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
from schemas.planner_operations import (
    ConflictFlagOperationPayload,
    PlannerOperation,
    TaskUpdateOperationPayload,
)


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


def test_commit_does_not_report_staged_operations_as_durable(db_session) -> None:
    task_id = uuid4()
    operation = build_operation(
        operation_type=PlannerOperationType.CREATE_TASK,
        payload=build_task_payload(task_id),
        approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
    )

    result = commit_planner_operations(db_session, [operation], commit=False)

    assert result.committed_operation_ids == []
    assert TaskRepository(db_session).get_by_id(task_id) is not None
    db_session.rollback()
    assert TaskRepository(db_session).get_by_id(task_id) is None


def test_commit_rejects_unknown_or_cross_session_operation_ids(db_session) -> None:
    unknown_id = uuid4()
    unknown = commit_planner_operations(
        db_session,
        session_id="review-session",
        operation_ids=[unknown_id],
    )
    assert unknown.failed_operation_ids == [unknown_id]
    assert "Unknown PlannerOperation" in unknown.errors[unknown_id]

    operation = build_operation(
        operation_type=PlannerOperationType.CREATE_TASK,
        payload=build_task_payload(),
        approval_state=PlannerOperationApprovalState.APPROVED,
    )
    operation.session_id = "another-session"
    persisted = PlannerOperationRepository(db_session).create(operation)
    cross_session = commit_planner_operations(
        db_session,
        session_id="review-session",
        operation_ids=[persisted.operation_id],
    )
    assert cross_session.failed_operation_ids == [persisted.operation_id]
    assert "belongs to another session" in cross_session.errors[persisted.operation_id]


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
    task_payload = TaskCreateDraft(
        title="Investigate churn signal",
        description="Evaluate whether spend is associated with churn.",
    )
    state = State(query="create task", task_create_payloads=[task_payload])

    result_state = manage_tasks(state, None)

    assert isinstance(result_state.task_create_payloads[0], TaskCreateDraft)
    assert len(result_state.planner_operations) == 1
    operation = result_state.planner_operations[0]
    assert operation.operation_type == PlannerOperationType.CREATE_TASK
    assert operation.approval_state == PlannerOperationApprovalState.PENDING
    assert "task_id" not in operation.payload
    assert TaskRepository(db_session).list() == []


def test_manage_tasks_resolves_create_and_supersession_references() -> None:
    parent_task_id = uuid4()
    profile_id = uuid4()
    target_task_id = uuid4()
    replacement_task_id = uuid4()
    state = State(query="manage tasks")
    parent_ref = state.bind_object_reference("task", str(parent_task_id))
    profile_ref = state.bind_object_reference("data_profile", str(profile_id))
    target_ref = state.bind_object_reference("task", str(target_task_id))
    replacement_ref = state.bind_object_reference("task", str(replacement_task_id))
    state.task_create_payloads = [
        TaskCreateDraft(
            title="Child task",
            description="Inspect one bounded signal.",
            parent_task_ref=parent_ref,
            data_profile_ref=profile_ref,
        )
    ]
    state.task_update_payloads = [
        TaskUpdateDraft(
            task_ref=target_ref,
            superseded_by_task_ref=replacement_ref,
        )
    ]

    result = manage_tasks(state, None)

    assert result.controlled_error is None
    assert result.planner_operations[0].payload["parent_task_id"] == str(parent_task_id)
    assert result.planner_operations[0].payload["profile_id"] == str(profile_id)
    assert result.planner_operations[1].payload["task_id"] == str(target_task_id)
    assert result.planner_operations[1].payload["superseded_by_task_id"] == str(replacement_task_id)


def test_operation_payload_methods_return_named_payload_models() -> None:
    task_id = uuid4()
    assumption_id = uuid4()
    state = State(query="local references")
    task_ref = state.bind_object_reference("task", str(task_id))
    assumption_ref = state.bind_object_reference("assumption", str(assumption_id))

    task_payload = TaskUpdateDraft(
        task_ref=task_ref,
        title="Refine churn task",
    ).operation_payload(task_id=UUID(state.resolve_object_reference(task_ref)))
    flag_payload = ConflictFlagDraft(
        assumption_ref=assumption_ref,
        reason="Discovery contradicts assumption.",
    ).operation_payload(assumption_id=UUID(state.resolve_object_reference(assumption_ref)))

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
    assert result.failed_operation_ids == []
    assert updated_objective is not None
    assert updated_objective.statement == "Understand churn drivers."
    assert objective_operation.operation_id in result.committed_operation_ids
    assert updated_assumption is not None
    assert updated_assumption.status == AssumptionStatus.FLAGGED


def test_commit_execution_bundle_validation_fails_outbox_only(db_session) -> None:
    repository = PlannerOperationRepository(db_session)
    outbox_op = repository.create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_EXECUTION_OUTBOX,
            payload={
                "execution_run_id": str(uuid4()),
                "dispatch_idempotency_key": str(uuid4()),
                "executor_type": "test",
                "method_id": "method",
                "parameter_hash": "hash",
                "prepared_payload": {},
            },
            approval_state=PlannerOperationApprovalState.APPROVED,
            produced_by_node=PlannerNodeName.PREPARE_EXECUTION,
        )
    )

    result = commit_planner_operations(
        db_session,
        operation_ids=[outbox_op.operation_id],
    )

    assert result.failed_operation_ids == [outbox_op.operation_id]
    assert (
        "Execution admission requires exactly one ExecutionRun and one outbox."
        in result.errors[outbox_op.operation_id]
    )
    outbox_op_db = repository.get_by_id(outbox_op.operation_id)
    assert outbox_op_db.approval_state == PlannerOperationApprovalState.APPROVED  # unchanged


def test_commit_execution_bundle_validation_fails_mismatched_ids(db_session) -> None:
    repository = PlannerOperationRepository(db_session)
    run_id1 = str(uuid4())
    run_id2 = str(uuid4())
    dispatch_key = str(uuid4())
    run_op = repository.create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_EXECUTION_RUN,
            payload={
                "execution_run_id": run_id1,
                "task_id": str(uuid4()),
                "hypothesis_id": str(uuid4()),
                "executor_type": "test",
                "method_id": "method",
                "parameter_hash": "hash",
                "status": "admitted",
                "dispatch_idempotency_key": dispatch_key,
            },
            approval_state=PlannerOperationApprovalState.APPROVED,
            produced_by_node=PlannerNodeName.PREPARE_EXECUTION,
        )
    )
    outbox_op = repository.create(
        build_operation(
            operation_type=PlannerOperationType.CREATE_EXECUTION_OUTBOX,
            payload={
                "execution_run_id": run_id2,
                "dispatch_idempotency_key": dispatch_key,
                "executor_type": "test",
                "method_id": "method",
                "parameter_hash": "hash",
                "prepared_payload": {},
            },
            approval_state=PlannerOperationApprovalState.APPROVED,
            produced_by_node=PlannerNodeName.PREPARE_EXECUTION,
        )
    )

    result = commit_planner_operations(
        db_session,
        operation_ids=[run_op.operation_id, outbox_op.operation_id],
    )

    assert len(result.failed_operation_ids) == 2
    assert (
        "ExecutionRun and outbox must have matching execution_run_id"
        in result.errors[run_op.operation_id]
    )
