"""Exact transactional SQLite persistence for immutable PlanRevision snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from cognieda.infrastructure.persistence.models import (
    PlanDependencyRecord,
    PlanRevisionRecord,
    PlanTaskBindingRecord,
)
from cognieda.infrastructure.persistence.repositories import (
    ObjectiveRepository,
    PlanRevisionRepository,
    TaskRepository,
)
from cognieda.schemas import (
    Objective,
    PlanDependency,
    PlanPriority,
    PlanRevision,
    PlanTaskBinding,
    Task,
    TaskKind,
)


def _persisted_task(
    session: Session,
    objective_id: UUID,
    *,
    task_id: UUID | None = None,
    kind: TaskKind = TaskKind.DATA,
) -> Task:
    return TaskRepository(session).create(
        Task(
            task_id=task_id or uuid4(),
            objective_id=objective_id,
            kind=kind,
            instruction=f"Perform {kind.value} work.",
        )
    )


def _binding(
    task: Task,
    *,
    order_rank: int = 0,
    priority: PlanPriority = PlanPriority.NORMAL,
) -> PlanTaskBinding:
    return PlanTaskBinding(
        task_id=task.task_id,
        order_rank=order_rank,
        priority=priority,
    )


def _revision(
    objective_id: UUID,
    tasks: Iterable[Task],
    *,
    bindings: Iterable[PlanTaskBinding] | None = None,
    dependencies: Iterable[PlanDependency] = (),
    plan_revision_id: UUID | None = None,
) -> PlanRevision:
    task_tuple = tuple(tasks)
    return PlanRevision.create(
        plan_revision_id=plan_revision_id,
        objective_id=objective_id,
        task_bindings=(
            tuple(_binding(task, order_rank=index) for index, task in enumerate(task_tuple))
            if bindings is None
            else tuple(bindings)
        ),
        dependencies=dependencies,
        tasks=task_tuple,
    )


def _edge(prerequisite: Task, dependent: Task) -> PlanDependency:
    return PlanDependency(
        prerequisite_task_id=prerequisite.task_id,
        dependent_task_id=dependent.task_id,
    )


def _persist_revision(session: Session, revision: PlanRevision) -> PlanRevision:
    repository = PlanRevisionRepository(session)
    repository.add(revision)
    session.commit()
    loaded = repository.get_by_id(revision.plan_revision_id)
    assert loaded is not None
    return loaded


def test_one_task_revision_round_trips_exactly(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Plan one task"))
    task = _persisted_task(db_session, objective.objective_id)
    revision = _revision(objective.objective_id, [task])

    loaded = _persist_revision(db_session, revision)

    assert loaded == revision
    assert loaded.model_dump(mode="json") == revision.model_dump(mode="json")
    assert loaded.contract_version == revision.contract_version
    assert loaded.fingerprint == revision.fingerprint


def test_multi_root_multi_leaf_dag_round_trips_all_content(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Plan a DAG"))
    tasks = tuple(_persisted_task(db_session, objective.objective_id) for _ in range(4))
    first_root, second_root, first_leaf, second_leaf = tasks
    bindings = (
        _binding(first_root, order_rank=1, priority=PlanPriority.HIGH),
        _binding(second_root, order_rank=1, priority=PlanPriority.LOW),
        _binding(first_leaf, order_rank=2),
        _binding(second_leaf, order_rank=2),
    )
    dependencies = (
        _edge(first_root, first_leaf),
        _edge(second_root, first_leaf),
        _edge(second_root, second_leaf),
    )
    revision = _revision(
        objective.objective_id,
        tasks,
        bindings=bindings,
        dependencies=dependencies,
    )

    loaded = _persist_revision(db_session, revision)

    assert loaded == revision
    assert loaded.task_bindings == revision.task_bindings
    assert loaded.dependencies == revision.dependencies
    assert [binding.order_rank for binding in loaded.task_bindings].count(1) == 2
    assert {binding.priority for binding in loaded.task_bindings} == {
        PlanPriority.LOW,
        PlanPriority.NORMAL,
        PlanPriority.HIGH,
    }
    assert "required_capability" not in PlanTaskBindingRecord.model_fields
    assert "required_capability" not in loaded.model_dump_json()


def test_storage_order_does_not_change_reconstructed_content(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Canonical storage"))
    first = _persisted_task(
        db_session,
        objective.objective_id,
        task_id=UUID("00000000-0000-0000-0000-000000000001"),
    )
    second = _persisted_task(
        db_session,
        objective.objective_id,
        task_id=UUID("00000000-0000-0000-0000-000000000002"),
    )
    revision = _revision(
        objective.objective_id,
        [first, second],
        bindings=(_binding(first, order_rank=1), _binding(second, order_rank=1)),
        dependencies=(_edge(first, second),),
    )
    _persist_revision(db_session, revision)
    rows = db_session.exec(
        select(PlanTaskBindingRecord).where(
            PlanTaskBindingRecord.plan_revision_id == revision.plan_revision_id
        )
    ).all()
    db_session.exec(
        delete(PlanTaskBindingRecord).where(
            PlanTaskBindingRecord.plan_revision_id == revision.plan_revision_id
        )
    )
    for row in reversed(rows):
        db_session.add(PlanTaskBindingRecord(**row.model_dump()))
    db_session.commit()

    loaded = PlanRevisionRepository(db_session).get_by_id(revision.plan_revision_id)

    assert loaded == revision
    assert loaded is not None and loaded.fingerprint == revision.fingerprint


@pytest.mark.parametrize("failed_table", ["plan_task_bindings", "plan_dependencies"])
def test_child_write_failure_rolls_back_complete_revision(
    db_session: Session,
    failed_table: str,
) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Atomic plan"))
    first = _persisted_task(db_session, objective.objective_id)
    second = _persisted_task(db_session, objective.objective_id)
    revision = _revision(
        objective.objective_id,
        [first, second],
        dependencies=(_edge(first, second),),
    )
    engine = db_session.get_bind()

    def fail_target_insert(_conn, _cursor, statement, _parameters, _context, _many):
        if f"INSERT INTO {failed_table}" in statement:
            raise RuntimeError(f"forced {failed_table} failure")

    event.listen(engine, "before_cursor_execute", fail_target_insert)
    try:
        with pytest.raises(RuntimeError, match="forced"):
            PlanRevisionRepository(db_session).add(revision)
            db_session.commit()
        db_session.rollback()
    finally:
        event.remove(engine, "before_cursor_execute", fail_target_insert)

    assert db_session.get(PlanRevisionRecord, revision.plan_revision_id) is None
    assert db_session.exec(select(PlanTaskBindingRecord)).all() == []
    assert db_session.exec(select(PlanDependencyRecord)).all() == []


def test_unknown_revision_returns_none(db_session: Session) -> None:
    assert PlanRevisionRepository(db_session).get_by_id(uuid4()) is None


def test_identity_collision_never_overwrites_existing_revision(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Collision"))
    first = _persisted_task(db_session, objective.objective_id)
    second = _persisted_task(db_session, objective.objective_id)
    revision_id = uuid4()
    original = _revision(objective.objective_id, [first], plan_revision_id=revision_id)
    conflicting = _revision(objective.objective_id, [second], plan_revision_id=revision_id)
    _persist_revision(db_session, original)

    with pytest.raises(IntegrityError):
        PlanRevisionRepository(db_session).add(conflicting)
        db_session.commit()
    db_session.rollback()

    assert PlanRevisionRepository(db_session).get_by_id(revision_id) == original


def test_same_identity_identical_replay_is_rejected_without_overwrite(
    db_session: Session,
) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Exact replay"))
    task = _persisted_task(db_session, objective.objective_id)
    revision = _revision(objective.objective_id, [task])
    _persist_revision(db_session, revision)

    with pytest.raises(IntegrityError):
        PlanRevisionRepository(db_session).add(revision)
        db_session.commit()
    db_session.rollback()

    assert PlanRevisionRepository(db_session).get_by_id(revision.plan_revision_id) == revision


def test_different_identities_with_same_fingerprint_remain_distinct(
    db_session: Session,
) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Distinct revisions"))
    task = _persisted_task(db_session, objective.objective_id)
    first = _revision(objective.objective_id, [task])
    second = _revision(objective.objective_id, [task])
    assert first.plan_revision_id != second.plan_revision_id
    assert first.fingerprint == second.fingerprint

    _persist_revision(db_session, first)
    _persist_revision(db_session, second)

    assert PlanRevisionRepository(db_session).get_by_id(first.plan_revision_id) == first
    assert PlanRevisionRepository(db_session).get_by_id(second.plan_revision_id) == second


def test_corrupt_stored_fingerprint_fails_closed(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Corrupt fingerprint"))
    task = _persisted_task(db_session, objective.objective_id)
    revision = _revision(objective.objective_id, [task])
    _persist_revision(db_session, revision)
    record = db_session.get(PlanRevisionRecord, revision.plan_revision_id)
    assert record is not None
    record.fingerprint = "sha256:" + "0" * 64
    db_session.add(record)
    db_session.commit()

    with pytest.raises(ValueError, match="fingerprint does not match"):
        PlanRevisionRepository(db_session).get_by_id(revision.plan_revision_id)


def test_repository_exposes_no_mutating_revision_api() -> None:
    prohibited = {"create", "save", "update", "patch", "delete"}

    assert prohibited.isdisjoint(vars(PlanRevisionRepository))
