"""Exact transactional SQLite persistence for immutable Plan snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from cognieda.infrastructure.persistence.models import (
    PlanAssumptionRecord,
    PlanDependencyRecord,
    PlanRecord,
    PlanTaskBindingRecord,
    TaskRecord,
)
from cognieda.infrastructure.persistence.repositories import (
    AssumptionRepository,
    ObjectiveRepository,
    PlanRepository,
    TaskRepository,
)
from cognieda.schemas import (
    Assumption,
    Objective,
    Plan,
    PlanDependency,
    PlanPriority,
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


def _plan(
    objective: Objective,
    tasks: Iterable[Task],
    *,
    bindings: Iterable[PlanTaskBinding] | None = None,
    dependencies: Iterable[PlanDependency] = (),
    assumptions: Iterable[Assumption] = (),
    plan_id: UUID | None = None,
) -> Plan:
    task_tuple = tuple(tasks)
    return Plan.create(
        plan_id=plan_id,
        objective=objective,
        assumptions=assumptions,
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


def _persist_plan(session: Session, plan: Plan) -> Plan:
    repository = PlanRepository(session)
    repository.add(plan)
    session.commit()
    loaded = repository.get_by_id(plan.plan_id)
    assert loaded is not None
    return loaded


def test_one_task_plan_round_trips_exactly(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Plan one task"))
    task = _persisted_task(db_session, objective.objective_id)
    plan = _plan(objective, [task])

    loaded = _persist_plan(db_session, plan)

    assert loaded == plan
    assert loaded.model_dump(mode="json") == plan.model_dump(mode="json")
    assert loaded.contract_version == plan.contract_version
    assert loaded.fingerprint == plan.fingerprint


def test_exact_planning_assumption_basis_round_trips(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Plan with a premise"))
    assumption = AssumptionRepository(db_session).create(
        Assumption(text="Exact Human-authored planning premise")
    )
    task = _persisted_task(db_session, objective.objective_id)
    plan = _plan(objective, [task], assumptions=(assumption,))

    loaded = _persist_plan(db_session, plan)

    assert loaded.assumptions == (assumption,)
    assert db_session.get(
        PlanAssumptionRecord,
        (plan.plan_id, assumption.assumption_id),
    ) is not None


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
    plan = _plan(
        objective,
        tasks,
        bindings=bindings,
        dependencies=dependencies,
    )

    loaded = _persist_plan(db_session, plan)

    assert loaded == plan
    assert loaded.task_bindings == plan.task_bindings
    assert loaded.dependencies == plan.dependencies
    assert [binding.order_rank for binding in loaded.task_bindings].count(1) == 2
    assert {binding.priority for binding in loaded.task_bindings} == {
        PlanPriority.LOW,
        PlanPriority.NORMAL,
        PlanPriority.HIGH,
    }
    prohibited = {
        "required_capability",
        "capability",
        "assigned_role",
        "provider",
        "provider_id",
        "specialist",
        "worker",
        "worker_id",
        "tool",
        "tool_id",
        "executor",
        "executor_id",
        "data_profile_id",
    }
    assert prohibited.isdisjoint(PlanRecord.model_fields)
    assert prohibited.isdisjoint(PlanTaskBindingRecord.model_fields)
    assert prohibited.isdisjoint(PlanDependencyRecord.model_fields)
    assert all(field not in loaded.model_dump_json() for field in prohibited)


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
    plan = _plan(
        objective,
        [first, second],
        bindings=(_binding(first, order_rank=1), _binding(second, order_rank=1)),
        dependencies=(_edge(first, second),),
    )
    _persist_plan(db_session, plan)
    rows = db_session.exec(
        select(PlanTaskBindingRecord).where(
            PlanTaskBindingRecord.plan_id == plan.plan_id
        )
    ).all()
    db_session.exec(
        delete(PlanTaskBindingRecord).where(
            PlanTaskBindingRecord.plan_id == plan.plan_id
        )
    )
    for row in reversed(rows):
        db_session.add(PlanTaskBindingRecord(**row.model_dump()))
    db_session.commit()

    loaded = PlanRepository(db_session).get_by_id(plan.plan_id)

    assert loaded == plan
    assert loaded is not None and loaded.fingerprint == plan.fingerprint


@pytest.mark.parametrize("failed_table", ["plan_task_bindings", "plan_dependencies"])
def test_child_write_failure_rolls_back_complete_plan(
    db_session: Session,
    failed_table: str,
) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Atomic plan"))
    first = _persisted_task(db_session, objective.objective_id)
    second = _persisted_task(db_session, objective.objective_id)
    plan = _plan(
        objective,
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
            PlanRepository(db_session).add(plan)
            db_session.commit()
        db_session.rollback()
    finally:
        event.remove(engine, "before_cursor_execute", fail_target_insert)

    assert db_session.get(PlanRecord, plan.plan_id) is None
    assert db_session.exec(select(PlanTaskBindingRecord)).all() == []
    assert db_session.exec(select(PlanDependencyRecord)).all() == []


def test_unknown_plan_returns_none(db_session: Session) -> None:
    assert PlanRepository(db_session).get_by_id(uuid4()) is None


def test_missing_persisted_task_fails_closed(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Missing Task"))
    transient_task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="This Task was not persisted.",
    )
    plan = _plan(objective, [transient_task])

    with pytest.raises(IntegrityError):
        PlanRepository(db_session).add(plan)
    db_session.rollback()

    assert db_session.get(PlanRecord, plan.plan_id) is None


def test_identity_collision_never_overwrites_existing_plan(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Collision"))
    first = _persisted_task(db_session, objective.objective_id)
    second = _persisted_task(db_session, objective.objective_id)
    plan_id = uuid4()
    original = _plan(objective, [first], plan_id=plan_id)
    conflicting = _plan(objective, [second], plan_id=plan_id)
    _persist_plan(db_session, original)

    with pytest.raises(IntegrityError):
        PlanRepository(db_session).add(conflicting)
        db_session.commit()
    db_session.rollback()

    assert PlanRepository(db_session).get_by_id(plan_id) == original


def test_same_identity_identical_replay_is_rejected_without_overwrite(
    db_session: Session,
) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Exact replay"))
    task = _persisted_task(db_session, objective.objective_id)
    plan = _plan(objective, [task])
    _persist_plan(db_session, plan)

    with pytest.raises(IntegrityError):
        PlanRepository(db_session).add(plan)
        db_session.commit()
    db_session.rollback()

    assert PlanRepository(db_session).get_by_id(plan.plan_id) == plan


def test_different_identities_with_same_fingerprint_remain_distinct(
    db_session: Session,
) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Distinct plans"))
    task = _persisted_task(db_session, objective.objective_id)
    first = _plan(objective, [task])
    second = _plan(objective, [task])
    assert first.plan_id != second.plan_id
    assert first.fingerprint == second.fingerprint

    _persist_plan(db_session, first)
    _persist_plan(db_session, second)

    assert PlanRepository(db_session).get_by_id(first.plan_id) == first
    assert PlanRepository(db_session).get_by_id(second.plan_id) == second


def test_corrupt_stored_fingerprint_fails_closed(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Corrupt fingerprint"))
    task = _persisted_task(db_session, objective.objective_id)
    plan = _plan(objective, [task])
    _persist_plan(db_session, plan)
    record = db_session.get(PlanRecord, plan.plan_id)
    assert record is not None
    record.fingerprint = "sha256:" + "0" * 64
    db_session.add(record)
    db_session.commit()

    with pytest.raises(ValueError, match="fingerprint does not match"):
        PlanRepository(db_session).get_by_id(plan.plan_id)


def test_malformed_stored_contract_fails_closed(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Malformed contract"))
    task = _persisted_task(db_session, objective.objective_id)
    plan = _plan(objective, [task])
    _persist_plan(db_session, plan)
    record = db_session.get(PlanRecord, plan.plan_id)
    assert record is not None
    record.contract_version = "plan/v2"
    db_session.add(record)
    db_session.commit()

    with pytest.raises(ValidationError, match="plan/v1"):
        PlanRepository(db_session).get_by_id(plan.plan_id)


def test_missing_task_during_reconstruction_fails_closed(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Missing load Task"))
    task = _persisted_task(db_session, objective.objective_id)
    plan = _plan(objective, [task])
    _persist_plan(db_session, plan)
    session_get = db_session.get

    def get_without_tasks(entity, ident):
        if entity is TaskRecord:
            return None
        return session_get(entity, ident)

    monkeypatch.setattr(db_session, "get", get_without_tasks)

    with pytest.raises(ValueError, match="missing Task"):
        PlanRepository(db_session).get_by_id(plan.plan_id)


def test_repository_exposes_no_mutating_plan_api() -> None:
    prohibited = {"create", "save", "update", "patch", "delete"}

    assert prohibited.isdisjoint(vars(PlanRepository))
