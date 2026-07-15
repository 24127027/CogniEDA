from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlmodel import Session

from agents.planner.types import TaskUpdateDraft
from application.orchestrator.planner_commit import commit_planner_operations
from db.migrations import downgrade_task_motivation_schema, upgrade_task_motivation_schema
from db.models import DataProfileRecord, DiscoveryRecord, HypothesisRecord, TaskRecord
from db.session import create_db_engine, get_session
from repositories import PlannerOperationRepository, TaskRepository, TaskUpdate
from schemas.artifacts import Hypothesis, Task
from schemas.enums import (
    DataProfileMethod,
    DiscoveryEpistemicStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskKind,
    TaskLifecycleState,
)
from schemas.planner_operations import PlannerOperation, TaskUpdateOperationPayload


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


def build_operation(
    operation_type: PlannerOperationType,
    payload: dict[str, object],
) -> PlannerOperation:
    return PlannerOperation(
        operation_type=operation_type,
        approval_state=PlannerOperationApprovalState.APPROVED,
        produced_by_node=PlannerNodeName.MANAGE_TASKS,
        payload=payload,
    )


def persist_discovery(session: Session) -> UUID:
    """Persist the minimum valid relational chain for a motivation reference."""

    profile = DataProfileRecord(
        dataset_path=f"data/motivation-{uuid4()}.csv",
        method=DataProfileMethod.BASELINE_SUMMARY,
        row_count=1,
        column_count=1,
    )
    session.add(profile)
    session.flush()

    task = TaskRecord(
        title="Source task",
        description="Produces the source hypothesis.",
        profile_id=profile.profile_id,
    )
    session.add(task)
    session.flush()

    hypothesis = HypothesisRecord(
        task_id=task.task_id,
        profile_id=profile.profile_id,
        statement="Source hypothesis.",
        scope="Test scope.",
        validation_method="test_method",
        evidence_expectation="Test evidence.",
    )
    session.add(hypothesis)
    session.flush()

    discovery = DiscoveryRecord(
        hypothesis_id=hypothesis.hypothesis_id,
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="Test scope.",
    )
    session.add(discovery)
    session.commit()
    return discovery.discovery_id


def test_create_round_trip_preserves_multiple_motivating_discoveries(db_session: Session) -> None:
    first_discovery_id = persist_discovery(db_session)
    second_discovery_id = persist_discovery(db_session)
    task_id = uuid4()

    result = commit_planner_operations(
        db_session,
        [
            build_operation(
                PlannerOperationType.CREATE_TASK,
                build_task_payload(
                    task_id,
                    motivated_by_discovery_ids=[second_discovery_id, first_discovery_id],
                ),
            )
        ],
    )

    task = TaskRepository(db_session).get_by_id(task_id)
    assert result.succeeded
    assert task is not None
    assert task.motivated_by_discovery_ids == [second_discovery_id, first_discovery_id]


def test_empty_and_legacy_task_payloads_remain_compatible(db_session: Session) -> None:
    task_id = uuid4()
    result = commit_planner_operations(
        db_session,
        [build_operation(PlannerOperationType.CREATE_TASK, build_task_payload(task_id))],
    )

    task = TaskRepository(db_session).get_by_id(task_id)
    assert result.succeeded
    assert task is not None
    assert task.motivated_by_discovery_ids == []


def test_duplicate_motivation_is_rejected_for_create_and_update() -> None:
    discovery_id = uuid4()

    with pytest.raises(ValueError, match="must not contain duplicates"):
        Task(**build_task_payload(motivated_by_discovery_ids=[discovery_id, discovery_id]))
    with pytest.raises(ValueError, match="must not contain duplicates"):
        TaskUpdate(motivated_by_discovery_ids=[discovery_id, discovery_id])


def test_unknown_discovery_rejects_create_without_partial_task_mutation(
    db_session: Session,
) -> None:
    task_id = uuid4()
    operation = build_operation(
        PlannerOperationType.CREATE_TASK,
        build_task_payload(task_id, motivated_by_discovery_ids=[uuid4()]),
    )

    result = commit_planner_operations(db_session, [operation])

    assert not result.succeeded
    assert result.failed_operation_ids == [operation.operation_id]
    assert "Referenced Discovery does not exist" in result.errors[operation.operation_id]
    assert TaskRepository(db_session).get_by_id(task_id) is None


def test_unknown_discovery_rejects_update_and_preserves_existing_motivation(
    db_session: Session,
) -> None:
    discovery_id = persist_discovery(db_session)
    task = TaskRepository(db_session).create(
        Task(**build_task_payload(motivated_by_discovery_ids=[discovery_id]))
    )
    operation = build_operation(
        PlannerOperationType.UPDATE_TASK,
        TaskUpdateOperationPayload(
            task_id=task.task_id,
            motivated_by_discovery_ids=[uuid4()],
        ).model_dump(mode="json", exclude_none=True),
    )

    result = commit_planner_operations(db_session, [operation])

    reloaded = TaskRepository(db_session).get_by_id(task.task_id)
    assert not result.succeeded
    assert reloaded is not None
    assert reloaded.motivated_by_discovery_ids == [discovery_id]


def test_update_replaces_clears_and_omits_motivation_explicitly(db_session: Session) -> None:
    first_discovery_id = persist_discovery(db_session)
    second_discovery_id = persist_discovery(db_session)
    task = TaskRepository(db_session).create(
        Task(**build_task_payload(motivated_by_discovery_ids=[first_discovery_id]))
    )
    repository = TaskRepository(db_session)

    replaced = repository.update(
        task.task_id,
        TaskUpdate(motivated_by_discovery_ids=[second_discovery_id]),
    )
    cleared = repository.update(task.task_id, TaskUpdate(motivated_by_discovery_ids=[]))
    unchanged = repository.update(task.task_id, TaskUpdate(title="Renamed task"))

    assert replaced is not None
    assert replaced.motivated_by_discovery_ids == [second_discovery_id]
    assert cleared is not None
    assert cleared.motivated_by_discovery_ids == []
    assert unchanged is not None
    assert unchanged.motivated_by_discovery_ids == []


def test_direct_task_repository_rejects_unknown_motivation(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Referenced Discovery does not exist"):
        TaskRepository(db_session).create(
            Task(**build_task_payload(motivated_by_discovery_ids=[uuid4()]))
        )


def test_planner_update_draft_and_operation_round_trip_preserve_uuid_list(
    db_session: Session,
) -> None:
    discovery_id = persist_discovery(db_session)
    task = TaskRepository(db_session).create(Task(**build_task_payload()))
    draft = TaskUpdateDraft(
        task_ref="task:local",
        motivated_by_discovery_ids=[discovery_id],
    )
    payload = draft.operation_payload(task_id=task.task_id)
    operation = PlannerOperationRepository(db_session).create(
        build_operation(
            PlannerOperationType.UPDATE_TASK,
            payload.model_dump(mode="json", exclude_unset=True),
        )
    )

    persisted = PlannerOperationRepository(db_session).get_by_id(operation.operation_id)
    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])
    reloaded_task = TaskRepository(db_session).get_by_id(task.task_id)
    clear_payload = TaskUpdateDraft(
        task_ref="task:local",
        motivated_by_discovery_ids=[],
    ).operation_payload(task_id=task.task_id)
    clear_operation = build_operation(
        PlannerOperationType.UPDATE_TASK,
        clear_payload.model_dump(mode="json", exclude_unset=True),
    )
    clear_result = commit_planner_operations(db_session, [clear_operation])
    cleared_task = TaskRepository(db_session).get_by_id(task.task_id)

    assert persisted is not None
    assert persisted.payload["motivated_by_discovery_ids"] == [str(discovery_id)]
    assert result.succeeded
    assert reloaded_task is not None
    assert reloaded_task.motivated_by_discovery_ids == [discovery_id]
    assert clear_payload.motivated_by_discovery_ids == []
    assert clear_result.succeeded
    assert cleared_task is not None
    assert cleared_task.motivated_by_discovery_ids == []


def test_batch_failure_rolls_back_prior_task_mutations(db_session: Session) -> None:
    valid_task_id = uuid4()
    invalid_task_id = uuid4()
    valid_operation = build_operation(
        PlannerOperationType.CREATE_TASK,
        build_task_payload(valid_task_id),
    )
    invalid_operation = build_operation(
        PlannerOperationType.CREATE_TASK,
        build_task_payload(invalid_task_id, motivated_by_discovery_ids=[uuid4()]),
    )

    result = commit_planner_operations(db_session, [valid_operation, invalid_operation])

    assert not result.succeeded
    assert result.committed_operation_ids == []
    assert result.failed_operation_ids == [invalid_operation.operation_id]
    assert TaskRepository(db_session).get_by_id(valid_task_id) is None
    assert TaskRepository(db_session).get_by_id(invalid_task_id) is None


def test_discovery_motivation_cannot_cross_workspace_databases(
    tmp_path,
    db_session: Session,
) -> None:
    discovery_id = persist_discovery(db_session)
    database_url = f"sqlite:///{(tmp_path / 'other-workspace.sqlite3').as_posix()}"
    create_db_engine.cache_clear()
    from db.init_db import init_db

    init_db(database_url)
    other_session = get_session(database_url)
    try:
        task_id = uuid4()
        result = commit_planner_operations(
            other_session,
            [
                build_operation(
                    PlannerOperationType.CREATE_TASK,
                    build_task_payload(task_id, motivated_by_discovery_ids=[discovery_id]),
                )
            ],
        )

        assert not result.succeeded
        assert TaskRepository(other_session).get_by_id(task_id) is None
    finally:
        other_session.close()
        create_db_engine.cache_clear()


def test_child_task_does_not_inherit_parent_motivation(db_session: Session) -> None:
    discovery_id = persist_discovery(db_session)
    parent_id = uuid4()
    child_id = uuid4()

    result = commit_planner_operations(
        db_session,
        [
            build_operation(
                PlannerOperationType.CREATE_TASK,
                build_task_payload(parent_id, motivated_by_discovery_ids=[discovery_id]),
            ),
            build_operation(
                PlannerOperationType.CREATE_TASK,
                build_task_payload(child_id, parent_task_id=parent_id),
            ),
        ],
    )

    child = TaskRepository(db_session).get_by_id(child_id)
    assert result.succeeded
    assert child is not None
    assert child.motivated_by_discovery_ids == []


def test_motivation_does_not_change_hypothesis_admission() -> None:
    motivated = Task(
        **build_task_payload(
            profile_id=uuid4(),
            motivated_by_discovery_ids=[uuid4()],
        )
    )
    unmotivated = Task(**build_task_payload(profile_id=motivated.profile_id))

    assert motivated.can_generate_hypothesis() is unmotivated.can_generate_hypothesis()
    assert "motivated_by_discovery_ids" not in Hypothesis.model_fields


def test_task_motivation_migration_preserves_legacy_rows_and_downgrades() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE tasks ("
                "task_id CHAR(32) PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO tasks (task_id, title, description) VALUES "
                "('legacy-task', 'Legacy task', 'Created before motivation support')"
            )
        )

    upgrade_task_motivation_schema(engine)
    upgrade_task_motivation_schema(engine)
    with engine.begin() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(tasks)")).fetchall()
        }
        motivation = connection.execute(
            text("SELECT motivated_by_discovery_ids FROM tasks WHERE task_id = 'legacy-task'")
        ).scalar_one()

    assert "motivated_by_discovery_ids" in columns
    assert motivation == "[]"

    downgrade_task_motivation_schema(engine)
    with engine.begin() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(tasks)")).fetchall()
        }
    assert "motivated_by_discovery_ids" not in columns
