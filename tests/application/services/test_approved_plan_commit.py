from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session, select

from cognieda.application.services import ApprovedPlanCommitError, commit_approved_plan
from cognieda.infrastructure.persistence.models import (
    ActivePlanRevisionRecord,
    ObjectiveRecord,
    PlanRevisionRecord,
    TaskRecord,
)
from cognieda.infrastructure.persistence.repositories import PlanRevisionRepository
from cognieda.schemas import (
    Objective,
    PlanDependency,
    PlanPriority,
    PlanRevision,
    PlanTaskBinding,
    Task,
    TaskKind,
    TaskStatus,
)


def _plan(
    *,
    objective: Objective | None = None,
    task_count: int = 1,
) -> tuple[Objective, tuple[Task, ...], PlanRevision]:
    objective = objective or Objective(text="Understand dataset size.")
    tasks = tuple(
        Task(
            objective_id=objective.objective_id,
            kind=TaskKind.DATA,
            instruction=f"Bounded data work {index}.",
        )
        for index in range(task_count)
    )
    dependencies = (
        (
            PlanDependency(
                prerequisite_task_id=tasks[0].task_id,
                dependent_task_id=tasks[1].task_id,
            ),
        )
        if task_count == 2
        else ()
    )
    revision = PlanRevision.create(
        objective_id=objective.objective_id,
        task_bindings=(
            PlanTaskBinding(
                task_id=task.task_id,
                order_rank=index,
                priority=PlanPriority.HIGH if index == 0 else PlanPriority.NORMAL,
            )
            for index, task in enumerate(tasks)
        ),
        dependencies=dependencies,
        tasks=tasks,
    )
    return objective, tasks, revision


def _commit(
    session: Session,
    plan: tuple[Objective, tuple[Task, ...], PlanRevision],
) -> None:
    objective, tasks, revision = plan
    commit_approved_plan(
        session,
        objective=objective,
        tasks=tasks,
        plan_revision=revision,
    )


def _counts(session: Session) -> tuple[int, int, int, int]:
    return (
        len(session.exec(select(ObjectiveRecord)).all()),
        len(session.exec(select(TaskRecord)).all()),
        len(session.exec(select(PlanRevisionRecord)).all()),
        len(session.exec(select(ActivePlanRevisionRecord)).all()),
    )


def test_approval_atomically_admits_exact_tasks_revision_and_active_selection(
    db_session: Session,
) -> None:
    objective, tasks, revision = _plan(task_count=2)

    _commit(db_session, (objective, tasks, revision))

    assert all(task.status is TaskStatus.PENDING for task in tasks)
    assert revision.dependencies[0].prerequisite_task_id == tasks[0].task_id
    assert PlanRevisionRepository(db_session).get_by_id(revision.plan_revision_id) == revision
    task_rows = db_session.exec(select(TaskRecord)).all()
    assert {row.task_id for row in task_rows} == {task.task_id for task in tasks}
    selection = db_session.exec(select(ActivePlanRevisionRecord)).one()
    assert selection.plan_revision_id == revision.plan_revision_id
    assert _counts(db_session) == (1, 2, 1, 1)


def test_mismatched_canonical_objects_create_no_authoritative_state(
    db_session: Session,
) -> None:
    objective, _, revision = _plan()
    mismatched_task = Task(
        task_id=uuid4(),
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Different task identity.",
    )

    with pytest.raises(ApprovedPlanCommitError, match="membership must match"):
        commit_approved_plan(
            db_session,
            objective=objective,
            tasks=(mismatched_task,),
            plan_revision=revision,
        )

    assert _counts(db_session) == (0, 0, 0, 0)


def test_failed_commit_rolls_back_staged_objective_and_tasks(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan()

    def fail_revision_add(self: PlanRevisionRepository, revision: object) -> None:
        del self, revision
        raise RuntimeError("injected revision persistence failure")

    monkeypatch.setattr(PlanRevisionRepository, "add", fail_revision_add)

    with pytest.raises(RuntimeError, match="injected revision persistence failure"):
        _commit(db_session, plan)

    assert _counts(db_session) == (0, 0, 0, 0)


def test_existing_active_revision_blocks_replanning_without_orphan_task(
    db_session: Session,
) -> None:
    first = _plan()
    _commit(db_session, first)
    second = _plan(objective=first[0])

    with pytest.raises(ApprovedPlanCommitError, match="Replanning"):
        _commit(db_session, second)

    assert _counts(db_session) == (1, 1, 1, 1)
