"""Append-only SQLite persistence for exact immutable Plan snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlmodel import Session, select

from cognieda.infrastructure.persistence.models import (
    AssumptionRecord,
    ObjectiveRecord,
    PlanAssumptionRecord,
    PlanDependencyRecord,
    PlanRecord,
    PlanTaskRecord,
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
    Task,
    TaskKind,
)


def _persisted_bundle(
    session: Session,
) -> tuple[Objective, tuple[Assumption, ...], tuple[Task, ...]]:
    objective = ObjectiveRepository(session).create(Objective(text="Understand retention."))
    assumptions = (
        AssumptionRepository(session).create(Assumption(text="Dates are reliable.")),
        AssumptionRepository(session).create(Assumption(text="Rows are customers.")),
    )
    tasks = (
        TaskRepository(session).create(
            Task(
                objective_id=objective.objective_id,
                kind=TaskKind.DATA,
                instruction="Profile retention data.",
            )
        ),
        TaskRepository(session).create(
            Task(
                objective_id=objective.objective_id,
                kind=TaskKind.GRAPH,
                instruction="Inspect admitted graph state.",
            )
        ),
    )
    return objective, assumptions, tasks


def _plan(
    objective: Objective,
    assumptions: Iterable[Assumption],
    tasks: Iterable[Task],
    *,
    plan_id: UUID | None = None,
) -> Plan:
    task_tuple = tuple(tasks)
    data: dict[str, object] = {
        "objective": objective,
        "assumptions": tuple(assumptions),
        "dependencies": (
            (
                PlanDependency(
                    prerequisite_task_id=task_tuple[0].task_id,
                    dependent_task_ids=tuple(task.task_id for task in task_tuple[1:]),
                ),
            )
            if len(task_tuple) > 1
            else ()
        ),
        "tasks": task_tuple,
    }
    if plan_id is not None:
        data["plan_id"] = plan_id
    return Plan.model_validate(data)


def _persist(session: Session, plan: Plan) -> Plan:
    PlanRepository(session).add(plan)
    session.commit()
    loaded = PlanRepository(session).get_by_id(plan.plan_id)
    assert loaded is not None
    return loaded


def test_exact_plan_round_trip_includes_normalized_content(db_session: Session) -> None:
    objective, assumptions, tasks = _persisted_bundle(db_session)
    plan = _plan(objective, reversed(assumptions), reversed(tasks))

    loaded = _persist(db_session, plan)

    assert loaded == plan
    assert loaded.tasks == tuple(sorted(tasks, key=lambda task: str(task.task_id)))
    assert loaded.task_ids == tuple(task.task_id for task in loaded.tasks)
    assert loaded.fingerprint == plan.fingerprint
    assert db_session.get(PlanRecord, plan.plan_id) is not None
    assert len(db_session.exec(select(PlanAssumptionRecord)).all()) == 2
    assert len(db_session.exec(select(PlanTaskRecord)).all()) == 2
    assert len(db_session.exec(select(PlanDependencyRecord)).all()) == 1


def test_grouped_dependency_flattens_and_reconstructs_exactly(
    db_session: Session,
) -> None:
    objective, assumptions, tasks = _persisted_bundle(db_session)
    third = TaskRepository(db_session).create(
        Task(
            objective_id=objective.objective_id,
            kind=TaskKind.DATA,
            instruction="Inspect a second dependent view.",
        )
    )
    all_tasks = (*tasks, third)
    plan = _plan(objective, assumptions, all_tasks)

    loaded = _persist(db_session, plan)
    edge_rows = db_session.exec(select(PlanDependencyRecord)).all()

    assert loaded == plan
    assert len(loaded.dependencies) == 1
    assert loaded.dependencies[0].dependent_task_ids == tuple(
        sorted((tasks[1].task_id, third.task_id), key=str)
    )
    assert {
        (row.prerequisite_task_id, row.dependent_task_id) for row in edge_rows
    } == {
        (tasks[0].task_id, tasks[1].task_id),
        (tasks[0].task_id, third.task_id),
    }


@pytest.mark.parametrize("missing", ["objective", "assumption", "task"])
def test_add_rejects_missing_referenced_fco(db_session: Session, missing: str) -> None:
    objective, assumptions, tasks = _persisted_bundle(db_session)
    if missing == "objective":
        objective = Objective(text="Not admitted.")
        tasks = tuple(
            task.model_copy(update={"objective_id": objective.objective_id}) for task in tasks
        )
    elif missing == "assumption":
        assumptions = (Assumption(text="Not admitted."),)
    else:
        tasks = (tasks[0].model_copy(update={"task_id": uuid4()}),)
    plan = _plan(objective, assumptions, tasks)

    with pytest.raises(ValueError, match=f"missing {missing.title()}"):
        PlanRepository(db_session).add(plan)
    db_session.rollback()
    assert db_session.get(PlanRecord, plan.plan_id) is None


@pytest.mark.parametrize("mismatch", ["objective", "assumption"])
def test_add_rejects_counterfeit_fco_content(db_session: Session, mismatch: str) -> None:
    objective, assumptions, tasks = _persisted_bundle(db_session)
    if mismatch == "objective":
        objective = Objective(
            objective_id=objective.objective_id,
            text="Counterfeit Objective.",
        )
    else:
        assumptions = (
            Assumption(
                assumption_id=assumptions[0].assumption_id,
                text="Counterfeit Assumption.",
            ),
        )
    plan = _plan(objective, assumptions, tasks)

    with pytest.raises(ValueError, match=f"Plan {mismatch.title()} differs"):
        PlanRepository(db_session).add(plan)
    db_session.rollback()


@pytest.mark.parametrize(
    ("missing_type", "message"),
    [
        (ObjectiveRecord, "missing Objective"),
        (AssumptionRecord, "missing Assumption"),
        (TaskRecord, "missing Task"),
    ],
)
def test_reload_fails_closed_when_referenced_fco_is_missing(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    missing_type: type,
    message: str,
) -> None:
    objective, assumptions, tasks = _persisted_bundle(db_session)
    plan = _plan(objective, assumptions, tasks)
    _persist(db_session, plan)
    session_get = db_session.get

    def get_with_missing(entity: Any, ident: Any) -> Any:
        if entity is missing_type:
            return None
        return session_get(entity, ident)

    monkeypatch.setattr(db_session, "get", get_with_missing)
    with pytest.raises(ValueError, match=message):
        PlanRepository(db_session).get_by_id(plan.plan_id)


def test_historical_reconstruction_uses_exact_objective_and_assumption_snapshots(
    db_session: Session,
) -> None:
    objective, assumptions, tasks = _persisted_bundle(db_session)
    plan = _plan(objective, assumptions, tasks)
    _persist(db_session, plan)
    original_fingerprint = plan.fingerprint

    objective_row = db_session.get(ObjectiveRecord, objective.objective_id)
    assumption_row = db_session.get(AssumptionRecord, assumptions[0].assumption_id)
    assert objective_row is not None and assumption_row is not None
    objective_row.text = "Later mutable Objective content."
    assumption_row.text = "Later mutable Assumption content."
    db_session.add(objective_row)
    db_session.add(assumption_row)
    db_session.commit()

    loaded = PlanRepository(db_session).get_by_id(plan.plan_id)

    assert loaded == plan
    assert loaded is not None and loaded.fingerprint == original_fingerprint
    assert loaded.objective.text == "Understand retention."
    loaded_assumption = next(
        item for item in loaded.assumptions if item.assumption_id == assumptions[0].assumption_id
    )
    assert loaded_assumption.text == "Dates are reliable."


@pytest.mark.parametrize("failed_table", ["plan_assumptions", "plan_tasks", "plan_dependencies"])
def test_child_write_failure_rolls_back_complete_plan(
    db_session: Session,
    failed_table: str,
) -> None:
    objective, assumptions, tasks = _persisted_bundle(db_session)
    plan = _plan(objective, assumptions, tasks)
    engine = db_session.get_bind()

    def fail_target_insert(
        _conn: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _many: Any,
    ) -> None:
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
    assert db_session.exec(select(PlanAssumptionRecord)).all() == []
    assert db_session.exec(select(PlanTaskRecord)).all() == []
    assert db_session.exec(select(PlanDependencyRecord)).all() == []


def test_append_only_identity_rejects_identical_and_conflicting_replay(
    db_session: Session,
) -> None:
    objective, assumptions, tasks = _persisted_bundle(db_session)
    plan_id = uuid4()
    original = _plan(objective, assumptions, tasks, plan_id=plan_id)
    conflicting = _plan(objective, assumptions[:1], tasks[:1], plan_id=plan_id)
    _persist(db_session, original)

    for replay in (original, conflicting):
        with pytest.raises(ValueError, match="append-only"):
            PlanRepository(db_session).add(replay)
        db_session.rollback()

    assert PlanRepository(db_session).get_by_id(plan_id) == original


def test_distinct_plan_ids_may_share_one_semantic_fingerprint(db_session: Session) -> None:
    objective, assumptions, tasks = _persisted_bundle(db_session)
    first = _plan(objective, assumptions, tasks)
    second = _plan(objective, assumptions, tasks)
    assert first.plan_id != second.plan_id
    assert first.fingerprint == second.fingerprint

    _persist(db_session, first)
    _persist(db_session, second)


def test_corrupt_fingerprint_fails_closed(db_session: Session) -> None:
    objective, assumptions, tasks = _persisted_bundle(db_session)
    plan = _plan(objective, assumptions, tasks)
    _persist(db_session, plan)
    row = db_session.get(PlanRecord, plan.plan_id)
    assert row is not None
    row.fingerprint = "sha256:" + "0" * 64
    db_session.add(row)
    db_session.commit()
    with pytest.raises(ValueError, match="fingerprint does not match"):
        PlanRepository(db_session).get_by_id(plan.plan_id)


def test_snapshot_identity_corruption_fails_closed(db_session: Session) -> None:
    objective, assumptions, tasks = _persisted_bundle(db_session)
    plan = _plan(objective, assumptions, tasks)
    _persist(db_session, plan)
    row = db_session.get(PlanRecord, plan.plan_id)
    assert row is not None
    row.objective_snapshot = {**row.objective_snapshot, "objective_id": str(uuid4())}
    db_session.add(row)
    db_session.commit()

    with pytest.raises(ValueError, match="snapshot identity"):
        PlanRepository(db_session).get_by_id(plan.plan_id)


def test_unknown_plan_returns_none_and_repository_has_no_crud_mutation(
    db_session: Session,
) -> None:
    assert PlanRepository(db_session).get_by_id(uuid4()) is None
    assert {"create", "save", "update", "patch", "delete"}.isdisjoint(vars(PlanRepository))


def test_plan_storage_schema_uses_only_plan_identity_and_snapshot_content() -> None:
    assert PlanRecord.__tablename__ == "plans"
    assert PlanAssumptionRecord.__tablename__ == "plan_assumptions"
    assert PlanTaskRecord.__tablename__ == "plan_tasks"
    assert set(PlanTaskRecord.model_fields) == {"plan_id", "task_id"}
    assert "plan_id" in PlanDependencyRecord.model_fields
    prohibited = {
        "approval_status",
        "activation_status",
        "provider",
        "capability",
        "tool",
        "contract_version",
        "priority",
        "order_rank",
    }
    for record in (PlanRecord, PlanAssumptionRecord, PlanTaskRecord, PlanDependencyRecord):
        assert prohibited.isdisjoint(record.model_fields)
