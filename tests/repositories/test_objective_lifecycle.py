"""Adversarial Objective lifecycle, revision, migration, and transaction tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from application.orchestrator import planner_commit as planner_commit_module
from application.orchestrator.planner_commit import commit_planner_operations
from db.init_db import init_db
from db.session import create_db_engine, get_session
from memory.retrieval_policy import is_allowed_in_context
from repositories.objective_repository import (
    ObjectiveMutationContext,
    ObjectiveRepository,
    ObjectiveUpdate,
)
from repositories.objective_revision_repository import ObjectiveRevisionRepository
from repositories.planner_operation_repository import PlannerOperationRepository
from repositories.session_frame_repository import SessionFrameRepository
from repositories.task_repository import TaskRepository
from repositories.user_decision_repository import UserDecisionRepository
from schemas.artifacts import Objective, SessionFrame, Task, UserDecision
from schemas.enums import (
    ContextMode,
    FirstClassObjectType,
    ObjectiveStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskLifecycleState,
    UserDecisionType,
)
from schemas.planner_operations import PlannerOperation


def _bootstrap_objective(
    session: Session,
    *,
    status: ObjectiveStatus = ObjectiveStatus.ACTIVE,
    title: str = "Objective",
) -> Objective:
    return ObjectiveRepository(session).create_for_bootstrap(
        Objective(title=title, statement=f"Statement for {title}", status=status)
    )


def _update_operation(
    objective: Objective,
    status: ObjectiveStatus | str | None = None,
    *,
    statement: str | None = None,
    expected_updated_at: datetime | None = None,
    approval_state: PlannerOperationApprovalState = PlannerOperationApprovalState.APPROVED,
) -> PlannerOperation:
    payload: dict[str, object] = {
        "objective_id": str(objective.objective_id),
        "revision_reason": "Explicit user-reviewed Objective change.",
        "expected_updated_at": (expected_updated_at or objective.updated_at).isoformat(),
        "actor": "test-user",
    }
    if status is not None:
        payload["status"] = status.value if isinstance(status, ObjectiveStatus) else status
    if statement is not None:
        payload["statement"] = statement
    return PlannerOperation(
        session_id="objective-session",
        operation_type=PlannerOperationType.UPDATE_OBJECTIVE,
        payload=payload,
        approval_state=approval_state,
        produced_by_node=PlannerNodeName.MANAGE_OBJECTIVE,
    )


def _persist_and_commit(session: Session, *operations: PlannerOperation):
    repository = PlannerOperationRepository(session)
    persisted = [repository.create(operation) for operation in operations]
    return persisted, commit_planner_operations(
        session,
        session_id="objective-session",
        operation_ids=[operation.operation_id for operation in persisted],
    )


def test_database_rejects_second_active_objective_and_allows_history(db_session: Session) -> None:
    _bootstrap_objective(db_session)
    ObjectiveRepository(db_session).create_for_bootstrap(
        Objective(title="Completed", statement="Done", status=ObjectiveStatus.COMPLETED)
    )
    ObjectiveRepository(db_session).create_for_bootstrap(
        Objective(title="Archived", statement="Stopped", status=ObjectiveStatus.ARCHIVED)
    )

    with pytest.raises(IntegrityError):
        _bootstrap_objective(db_session, title="Second active")


def test_objective_revision_is_non_fco_and_cannot_enter_retrieval_context() -> None:
    assert "objective_revision" not in {item.value for item in FirstClassObjectType}
    assert not is_allowed_in_context(
        "objective_revision",
        "active",
        ContextMode.PLANNING,
    )


def test_get_active_exposes_corrupt_legacy_cardinality(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'corrupt.sqlite3').as_posix()}"
    engine = create_db_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE objectives ("
                "objective_id CHAR(32) PRIMARY KEY, title TEXT NOT NULL, statement TEXT NOT NULL, "
                "analysis_intent VARCHAR NOT NULL, status VARCHAR NOT NULL, "
                "created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"
            )
        )
        for suffix in ("1", "2"):
            connection.execute(
                text(
                    "INSERT INTO objectives VALUES "
                    f"('{suffix * 32}', 'Obj {suffix}', 'Stmt', 'EXPLORATORY', 'ACTIVE', "
                    "'2026-07-17 00:00:00', '2026-07-17 00:00:00')"
                )
            )
    session = get_session(database_url)
    try:
        with pytest.raises(RuntimeError, match="multiple ACTIVE Objectives"):
            ObjectiveRepository(session).get_active()
    finally:
        session.close()
        create_db_engine.cache_clear()


@pytest.mark.parametrize(
    ("previous", "updated", "allowed"),
    [
        (ObjectiveStatus.ACTIVE, ObjectiveStatus.COMPLETED, True),
        (ObjectiveStatus.ACTIVE, ObjectiveStatus.ARCHIVED, True),
        (ObjectiveStatus.COMPLETED, ObjectiveStatus.ACTIVE, True),
        (ObjectiveStatus.ARCHIVED, ObjectiveStatus.ACTIVE, True),
        (ObjectiveStatus.COMPLETED, ObjectiveStatus.ARCHIVED, True),
        (ObjectiveStatus.ARCHIVED, ObjectiveStatus.COMPLETED, False),
        (ObjectiveStatus.ACTIVE, ObjectiveStatus.ACTIVE, False),
        (ObjectiveStatus.ACTIVE, ObjectiveStatus.PAUSED, True),
        (ObjectiveStatus.PAUSED, ObjectiveStatus.ACTIVE, True),
    ],
)
def test_transition_matrix_is_explicit(
    db_session: Session,
    previous: ObjectiveStatus,
    updated: ObjectiveStatus,
    allowed: bool,
) -> None:
    objective = _bootstrap_objective(db_session, status=previous)
    persisted, result = _persist_and_commit(db_session, _update_operation(objective, updated))

    if allowed:
        assert result.committed_operation_ids == [persisted[0].operation_id]
        assert ObjectiveRepository(db_session).get_by_id(objective.objective_id).status == updated
        revisions = ObjectiveRevisionRepository(db_session).list_for_objective(
            objective.objective_id
        )
        assert len(revisions) == 1
        assert revisions[0].previous_status == previous
        assert revisions[0].new_status == updated
        assert revisions[0].changed_fields == ["status"]
    else:
        assert result.failed_operation_ids == [persisted[0].operation_id]
        assert ObjectiveRepository(db_session).get_by_id(objective.objective_id).status == previous
        assert ObjectiveRevisionRepository(db_session).list_for_objective(
            objective.objective_id
        ) == []


def test_invalid_status_stale_update_and_another_active_are_rejected(db_session: Session) -> None:
    active = _bootstrap_objective(db_session)
    archived = _bootstrap_objective(
        db_session,
        status=ObjectiveStatus.ARCHIVED,
        title="Archived",
    )

    invalid, invalid_result = _persist_and_commit(
        db_session,
        _update_operation(active, "not-a-status"),
    )
    assert invalid_result.failed_operation_ids == [invalid[0].operation_id]

    stale, stale_result = _persist_and_commit(
        db_session,
        _update_operation(
            active,
            statement="Stale statement",
            expected_updated_at=datetime(2000, 1, 1, tzinfo=UTC),
        ),
    )
    assert stale_result.failed_operation_ids == [stale[0].operation_id]
    assert "stale" in stale_result.errors[stale[0].operation_id].lower()

    conflict, conflict_result = _persist_and_commit(
        db_session,
        _update_operation(archived, ObjectiveStatus.ACTIVE),
    )
    assert conflict_result.failed_operation_ids == [conflict[0].operation_id]
    assert "already ACTIVE" in conflict_result.errors[conflict[0].operation_id]


@pytest.mark.parametrize(
    "task_state",
    [
        TaskLifecycleState.PROPOSED,
        TaskLifecycleState.ACTIVE,
        TaskLifecycleState.PAUSED,
    ],
)
def test_unfinished_tasks_reject_terminal_transition_without_mutation(
    db_session: Session,
    task_state: TaskLifecycleState,
) -> None:
    objective = _bootstrap_objective(db_session)
    parent = TaskRepository(db_session).create(
        Task(
            title="Parent",
            description="Completed organizing parent",
            lifecycle_state=TaskLifecycleState.COMPLETED,
        )
    )
    task = TaskRepository(db_session).create(
        Task(
            title="Unfinished child",
            description="Must remain untouched",
            lifecycle_state=task_state,
            parent_task_id=parent.task_id,
            blocked_reason="blocked" if task_state == TaskLifecycleState.ACTIVE else None,
        )
    )

    persisted, result = _persist_and_commit(
        db_session,
        _update_operation(objective, ObjectiveStatus.ARCHIVED),
    )

    assert result.failed_operation_ids == [persisted[0].operation_id]
    assert "unfinished Tasks" in result.errors[persisted[0].operation_id]
    assert TaskRepository(db_session).get_by_id(task.task_id) == task
    assert ObjectiveRepository(db_session).get_by_id(objective.objective_id).status == (
        ObjectiveStatus.ACTIVE
    )
    assert ObjectiveRevisionRepository(db_session).list_for_objective(
        objective.objective_id
    ) == []


def test_not_required_objective_operation_cannot_bypass_user_authority(
    db_session: Session,
) -> None:
    objective = _bootstrap_objective(db_session)
    persisted, result = _persist_and_commit(
        db_session,
        _update_operation(
            objective,
            ObjectiveStatus.COMPLETED,
            approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
        ),
    )

    assert result.failed_operation_ids == [persisted[0].operation_id]
    assert "explicit user approval" in result.errors[persisted[0].operation_id]
    assert ObjectiveRepository(db_session).get_by_id(objective.objective_id).status == (
        ObjectiveStatus.ACTIVE
    )


def test_objective_revision_captures_exact_multi_field_change_and_is_append_only(
    db_session: Session,
) -> None:
    objective = _bootstrap_objective(db_session)
    operation = _update_operation(
        objective,
        ObjectiveStatus.COMPLETED,
        statement="Accepted final scope.",
    )
    operation.payload["title"] = "Accepted Objective"
    persisted, result = _persist_and_commit(db_session, operation)

    assert result.committed_operation_ids == [persisted[0].operation_id]
    revision = ObjectiveRevisionRepository(db_session).list_for_objective(
        objective.objective_id
    )[0]
    assert revision.previous_title == objective.title
    assert revision.previous_statement == objective.statement
    assert revision.new_title == "Accepted Objective"
    assert revision.new_statement == "Accepted final scope."
    assert revision.changed_fields == ["title", "statement", "status"]
    assert revision.planner_operation_id == persisted[0].operation_id
    assert revision.actor == "test-user"
    assert not hasattr(ObjectiveRevisionRepository(db_session), "update")
    assert not hasattr(ObjectiveRevisionRepository(db_session), "delete")
    assert not hasattr(ObjectiveRevisionRepository(db_session), "create")


@pytest.mark.parametrize(
    ("field_name", "new_value"),
    [
        ("title", "Refined title"),
        ("statement", "Refined statement"),
    ],
)
def test_single_field_revision_content_is_exact(
    db_session: Session,
    field_name: str,
    new_value: str,
) -> None:
    objective = _bootstrap_objective(db_session)
    operation = _update_operation(objective)
    operation.payload[field_name] = new_value
    _, result = _persist_and_commit(db_session, operation)

    assert result.succeeded
    revision = ObjectiveRevisionRepository(db_session).list_for_objective(
        objective.objective_id
    )[0]
    assert revision.changed_fields == [field_name]
    assert getattr(revision, f"new_{field_name}") == new_value


def test_failure_after_objective_create_rolls_back_the_entire_batch(db_session: Session) -> None:
    objective_id = uuid4()
    create = PlannerOperation(
        session_id="objective-session",
        operation_type=PlannerOperationType.CREATE_OBJECTIVE,
        payload={
            "objective_id": str(objective_id),
            "title": "New Objective",
            "statement": "Must roll back",
            "status": ObjectiveStatus.ACTIVE.value,
        },
        approval_state=PlannerOperationApprovalState.APPROVED,
        produced_by_node=PlannerNodeName.MANAGE_OBJECTIVE,
    )
    missing = Objective(
        title="Missing",
        statement="Missing",
        status=ObjectiveStatus.ARCHIVED,
    )
    update_missing = _update_operation(missing, ObjectiveStatus.ACTIVE)

    persisted, result = _persist_and_commit(db_session, create, update_missing)

    assert result.failed_operation_ids == [persisted[1].operation_id]
    assert ObjectiveRepository(db_session).get_by_id(objective_id) is None
    assert PlannerOperationRepository(db_session).get_by_id(
        persisted[0].operation_id
    ).approval_state == PlannerOperationApprovalState.APPROVED


def test_session_frame_failure_rolls_back_objective_revision_and_operation_state(
    db_session: Session,
) -> None:
    objective = _bootstrap_objective(db_session)
    existing_frame = SessionFrameRepository(db_session).create(
        SessionFrame(frame_topic="Existing", objective_snapshot=objective.statement)
    )
    update = _update_operation(objective, statement="Changed statement")
    duplicate_frame = PlannerOperation(
        session_id="objective-session",
        operation_type=PlannerOperationType.UPDATE_SESSION_FRAME,
        payload=existing_frame.model_dump(mode="json"),
        approval_state=PlannerOperationApprovalState.APPROVED,
        produced_by_node=PlannerNodeName.MANAGE_OBJECTIVE,
    )

    persisted, result = _persist_and_commit(db_session, update, duplicate_frame)

    assert result.failed_operation_ids == [persisted[1].operation_id]
    assert ObjectiveRepository(db_session).get_by_id(objective.objective_id) == objective
    assert ObjectiveRevisionRepository(db_session).list_for_objective(
        objective.objective_id
    ) == []
    assert SessionFrameRepository(db_session).list() == [existing_frame]
    assert all(
        PlannerOperationRepository(db_session).get_by_id(operation.operation_id).approval_state
        == PlannerOperationApprovalState.APPROVED
        for operation in persisted
    )


def test_revision_insert_failure_rolls_back_objective(monkeypatch, db_session: Session) -> None:
    objective = _bootstrap_objective(db_session)
    operation = PlannerOperationRepository(db_session).create(
        _update_operation(objective, statement="Must roll back")
    )

    def fail_revision(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("injected revision failure")

    monkeypatch.setattr(
        ObjectiveRevisionRepository,
        "stage_for_objective_mutation",
        fail_revision,
    )
    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])

    assert result.failed_operation_ids == [operation.operation_id]
    assert ObjectiveRepository(db_session).get_by_id(objective.objective_id) == objective
    assert ObjectiveRevisionRepository(db_session).list_for_objective(
        objective.objective_id
    ) == []


def test_operation_state_failure_rolls_back_objective_and_revision(
    monkeypatch,
    db_session: Session,
) -> None:
    objective = _bootstrap_objective(db_session)
    operation = PlannerOperationRepository(db_session).create(
        _update_operation(objective, statement="Must roll back")
    )

    def fail_operation_state(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("injected PlannerOperation state failure")

    monkeypatch.setattr(
        planner_commit_module,
        "_mark_persisted_operation_committed",
        fail_operation_state,
    )
    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])

    assert result.failed_operation_ids == [operation.operation_id]
    assert ObjectiveRepository(db_session).get_by_id(objective.objective_id) == objective
    assert ObjectiveRevisionRepository(db_session).list_for_objective(
        objective.objective_id
    ) == []


def test_final_commit_failure_rolls_back_objective_and_revision(
    monkeypatch,
    db_session: Session,
) -> None:
    objective = _bootstrap_objective(db_session)
    operation = PlannerOperationRepository(db_session).create(
        _update_operation(objective, statement="Must roll back")
    )

    def fail_commit() -> None:
        raise RuntimeError("injected final commit failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    result = commit_planner_operations(db_session, operation_ids=[operation.operation_id])

    assert result.failed_operation_ids == [operation.operation_id]
    assert ObjectiveRepository(db_session).get_by_id(objective.objective_id) == objective
    assert ObjectiveRevisionRepository(db_session).list_for_objective(
        objective.objective_id
    ) == []


def test_concurrent_first_creation_is_database_serialized(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'concurrent-create.sqlite3').as_posix()}"
    init_db(database_url)

    def create(title: str) -> bool:
        session = get_session(database_url)
        try:
            ObjectiveRepository(session).create_for_bootstrap(
                Objective(title=title, statement=title, status=ObjectiveStatus.ACTIVE)
            )
            return True
        except IntegrityError:
            return False
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(create, ["First", "Second"]))

    session = get_session(database_url)
    try:
        assert sorted(outcomes) == [False, True]
        assert len(ObjectiveRepository(session).list(status=ObjectiveStatus.ACTIVE)) == 1
    finally:
        session.close()
        create_db_engine.cache_clear()


def test_concurrent_reactivation_cannot_create_two_active_rows(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'concurrent-reactivate.sqlite3').as_posix()}"
    init_db(database_url)
    setup = get_session(database_url)
    first = _bootstrap_objective(
        setup,
        status=ObjectiveStatus.ARCHIVED,
        title="First archived",
    )
    second = _bootstrap_objective(
        setup,
        status=ObjectiveStatus.COMPLETED,
        title="Second completed",
    )
    decision_ids = [
        UserDecisionRepository(setup)
        .create(
            UserDecision(
                decision_type=UserDecisionType.OBJECTIVE_MANAGEMENT,
                decision=f"Reactivate {label}",
                rationale="Explicit concurrent authority test.",
            )
        )
        .decision_id
        for label in ("first", "second")
    ]
    setup.close()

    def reactivate(request) -> bool:
        objective_id, decision_id = request
        session = get_session(database_url)
        try:
            objective = ObjectiveRepository(session).get_by_id(objective_id)
            ObjectiveRepository(session).update(
                objective_id,
                ObjectiveUpdate(status=ObjectiveStatus.ACTIVE),
                context=ObjectiveMutationContext(
                    reason="Explicit concurrent reactivation.",
                    actor="test-user",
                    expected_updated_at=objective.updated_at,
                    user_decision_id=decision_id,
                ),
            )
            return True
        except (IntegrityError, ValueError):
            return False
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(
                reactivate,
                zip(
                    [first.objective_id, second.objective_id],
                    decision_ids,
                    strict=True,
                ),
            )
        )

    session = get_session(database_url)
    try:
        assert sorted(outcomes) == [False, True]
        assert len(ObjectiveRepository(session).list(status=ObjectiveStatus.ACTIVE)) == 1
    finally:
        session.close()
        create_db_engine.cache_clear()


def test_competing_active_switch_batches_leave_one_active_objective(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'switch-race.sqlite3').as_posix()}"
    init_db(database_url)
    setup = get_session(database_url)
    current = _bootstrap_objective(setup, title="Current")
    targets = [
        _bootstrap_objective(
            setup,
            status=ObjectiveStatus.ARCHIVED,
            title=f"Target {index}",
        )
        for index in (1, 2)
    ]
    batch_ids: list[tuple[str, list]] = []
    operation_repository = PlannerOperationRepository(setup)
    for index, target in enumerate(targets):
        session_id = f"switch-{index}"
        operations = [
            _update_operation(current, ObjectiveStatus.ARCHIVED),
            _update_operation(target, ObjectiveStatus.ACTIVE),
        ]
        for operation in operations:
            operation.session_id = session_id
        persisted = [operation_repository.create(operation) for operation in operations]
        batch_ids.append((session_id, [operation.operation_id for operation in persisted]))
    setup.close()

    def commit_batch(batch: tuple[str, list]) -> bool:
        session_id, operation_ids = batch
        session = get_session(database_url)
        try:
            return commit_planner_operations(
                session,
                session_id=session_id,
                operation_ids=operation_ids,
            ).succeeded
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(commit_batch, batch_ids))

    session = get_session(database_url)
    try:
        assert outcomes.count(True) == 1
        assert len(ObjectiveRepository(session).list(status=ObjectiveStatus.ACTIVE)) == 1
    finally:
        session.close()
        create_db_engine.cache_clear()


def test_objective_migration_is_idempotent_and_rejects_ambiguous_legacy_data(
    tmp_path,
) -> None:
    valid_url = f"sqlite:///{(tmp_path / 'valid-legacy.sqlite3').as_posix()}"
    engine = create_db_engine(valid_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE objectives ("
                "objective_id CHAR(32) PRIMARY KEY, title TEXT NOT NULL, statement TEXT NOT NULL, "
                "analysis_intent VARCHAR NOT NULL, status VARCHAR NOT NULL, "
                "created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO objectives VALUES "
                "('11111111111111111111111111111111', 'Objective', 'Statement', "
                "'EXPLORATORY', 'ACTIVE', '2026-07-17', '2026-07-17')"
            )
        )
    init_db(valid_url)
    init_db(valid_url)
    inspector = inspect(create_db_engine(valid_url))
    assert "uq_active_objective" in {
        index["name"] for index in inspector.get_indexes("objectives")
    }
    assert "objective_revisions" in inspector.get_table_names()

    invalid_url = f"sqlite:///{(tmp_path / 'invalid-legacy.sqlite3').as_posix()}"
    create_db_engine.cache_clear()
    engine = create_db_engine(invalid_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE objectives ("
                "objective_id CHAR(32) PRIMARY KEY, title TEXT NOT NULL, statement TEXT NOT NULL, "
                "analysis_intent VARCHAR NOT NULL, status VARCHAR NOT NULL, "
                "created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"
            )
        )
        for suffix in ("2", "3"):
            connection.execute(
                text(
                    "INSERT INTO objectives VALUES "
                    f"('{suffix * 32}', 'Objective', 'Statement', 'EXPLORATORY', 'ACTIVE', "
                    "'2026-07-17', '2026-07-17')"
                )
            )
    with pytest.raises(IntegrityError):
        init_db(invalid_url)
    create_db_engine.cache_clear()


def test_legacy_objective_revision_columns_are_upgraded_without_losing_history(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'legacy-revisions.sqlite3').as_posix()}"
    objective_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    revision_id = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    engine = create_db_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE objectives ("
                "objective_id CHAR(32) PRIMARY KEY, title TEXT NOT NULL, statement TEXT NOT NULL, "
                "analysis_intent VARCHAR NOT NULL, status VARCHAR NOT NULL, "
                "created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO objectives VALUES "
                f"('{objective_id}', 'Objective', 'New statement', 'EXPLORATORY', 'COMPLETED', "
                "'2026-07-17', '2026-07-17')"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE objective_revisions ("
                "objective_revision_id CHAR(32) PRIMARY KEY, objective_id CHAR(32) NOT NULL, "
                "previous_title TEXT NOT NULL, previous_description TEXT NOT NULL, "
                "previous_lifecycle_state VARCHAR, new_title TEXT NOT NULL, "
                "new_description TEXT NOT NULL, new_lifecycle_state VARCHAR, "
                "changed_fields JSON NOT NULL, revision_reason TEXT, "
                "planner_operation_id VARCHAR, user_decision_id VARCHAR, "
                "created_at DATETIME NOT NULL, created_by VARCHAR, "
                "FOREIGN KEY(objective_id) REFERENCES objectives(objective_id))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO objective_revisions VALUES "
                f"('{revision_id}', '{objective_id}', 'Objective', 'Old statement', 'ACTIVE', "
                "'Objective', 'New statement', 'COMPLETED', '[\"statement\", \"status\"]', "
                "'User accepted completion', NULL, NULL, '2026-07-17', 'legacy-user')"
            )
        )

    init_db(database_url)
    init_db(database_url)
    session = get_session(database_url)
    try:
        revisions = ObjectiveRevisionRepository(session).list_for_objective(
            UUID(objective_id)
        )
        assert len(revisions) == 1
        assert revisions[0].previous_statement == "Old statement"
        assert revisions[0].new_statement == "New statement"
        assert revisions[0].previous_status == ObjectiveStatus.ACTIVE
        assert revisions[0].new_status == ObjectiveStatus.COMPLETED
        assert revisions[0].reason == "User accepted completion"
        assert revisions[0].actor == "legacy-user"
    finally:
        session.close()
        create_db_engine.cache_clear()
