"""Atomic Plan admission and active selection invariants."""

from __future__ import annotations

import inspect
from typing import Any, Literal, cast

import pytest
from sqlmodel import Session, select

import cognieda.application.services as application_services
from cognieda.application.services import PlanAdmissionService
from cognieda.infrastructure.persistence.models import (
    ActivePlanRecord,
    AssumptionRecord,
    ObjectiveRecord,
    PlanRecord,
    TaskRecord,
)
from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRepository,
    AssumptionRepository,
    ObjectiveRepository,
    PlanRepository,
    TaskRepository,
)
from cognieda.schemas import Assumption, Objective, Plan, Task, TaskKind, TaskStatus


def _task(objective: Objective, *, instruction: str = "Profile retention data.") -> Task:
    return Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction=instruction,
    )


def _plan(
    objective: Objective,
    tasks: tuple[Task, ...],
    *,
    assumptions: tuple[Assumption, ...] = (),
) -> Plan:
    return Plan.create(
        objective=objective,
        assumptions=assumptions,
        task_ids=(task.task_id for task in tasks),
        tasks=tasks,
    )


def _admit(session: Session, plan: Plan, tasks: tuple[Task, ...]) -> None:
    assert PlanAdmissionService(session).admit(plan, tasks=tasks) == plan


def test_review_contracts_are_deleted_and_admission_preserves_authority_boundaries() -> None:
    assert not hasattr(application_services, "PlanReviewAction")
    assert not hasattr(application_services, "PlanReviewDecision")
    source = inspect.getsource(PlanAdmissionService)
    assert "pydantic_ai" not in source
    assert "Capability" not in source
    assert "Executor" not in source
    assert "DataProfile" not in source


def test_candidate_is_transient_until_exact_approval(db_session: Session) -> None:
    objective = Objective(text="Understand retention.")
    task = _task(objective)
    _plan(objective, (task,))

    assert db_session.exec(select(ObjectiveRecord)).all() == []
    assert db_session.exec(select(TaskRecord)).all() == []
    assert db_session.exec(select(PlanRecord)).all() == []
    assert db_session.exec(select(ActivePlanRecord)).all() == []


def test_admission_atomically_persists_exact_new_bundle_and_active_selection(
    db_session: Session,
) -> None:
    assumption = AssumptionRepository(db_session).create(
        Assumption(text="Dates are reliable.")
    )
    objective = Objective(text="Understand retention.")
    tasks = (_task(objective), _task(objective, instruction="Count renewal events."))
    plan = _plan(objective, tasks, assumptions=(assumption,))

    _admit(db_session, plan, tasks)

    assert ObjectiveRepository(db_session).get_by_id(objective.objective_id) == objective
    assert tuple(TaskRepository(db_session).get_by_id(task.task_id) for task in tasks) == tasks
    assert PlanRepository(db_session).get_by_id(plan.plan_id) == plan
    assert ActivePlanRepository(db_session).get_by_objective_id(objective.objective_id) == plan


def test_existing_exact_objective_and_task_are_reused_without_status_replacement(
    db_session: Session,
) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Understand retention."))
    persisted_task = TaskRepository(db_session).create(_task(objective))
    candidate_task = persisted_task.model_copy(update={"status": TaskStatus.COMPLETED})
    plan = _plan(objective, (candidate_task,))

    _admit(db_session, plan, (candidate_task,))

    assert len(db_session.exec(select(ObjectiveRecord)).all()) == 1
    assert len(db_session.exec(select(TaskRecord)).all()) == 1
    assert TaskRepository(db_session).get_by_id(persisted_task.task_id) == persisted_task


def test_objective_identity_collision_fails_without_plan_or_task_writes(
    db_session: Session,
) -> None:
    persisted = ObjectiveRepository(db_session).create(Objective(text="Original objective."))
    counterfeit = Objective(
        objective_id=persisted.objective_id,
        text="Counterfeit objective.",
    )
    task = _task(counterfeit)
    plan = _plan(counterfeit, (task,))

    with pytest.raises(ValueError, match="Objective identity collision"):
        _admit(db_session, plan, (task,))

    assert TaskRepository(db_session).get_by_id(task.task_id) is None
    assert PlanRepository(db_session).get_by_id(plan.plan_id) is None
    assert ActivePlanRepository(db_session).get_by_objective_id(persisted.objective_id) is None


@pytest.mark.parametrize("case", ["missing", "changed"])
def test_assumption_must_already_exist_with_exact_content(
    db_session: Session,
    case: str,
) -> None:
    admitted = Assumption(text="Dates are reliable.")
    if case == "changed":
        admitted = AssumptionRepository(db_session).create(admitted)
        candidate = Assumption(
            assumption_id=admitted.assumption_id,
            text="Changed premise.",
        )
    else:
        candidate = admitted
    objective = Objective(text="Understand retention.")
    task = _task(objective)
    plan = _plan(objective, (task,), assumptions=(candidate,))

    with pytest.raises(ValueError, match="Assumption"):
        _admit(db_session, plan, (task,))

    persisted_assumption = db_session.get(AssumptionRecord, candidate.assumption_id)
    if case == "missing":
        assert persisted_assumption is None
    else:
        assert persisted_assumption is not None
    assert ObjectiveRepository(db_session).get_by_id(objective.objective_id) is None
    assert TaskRepository(db_session).get_by_id(task.task_id) is None
    assert PlanRepository(db_session).get_by_id(plan.plan_id) is None


def test_task_identity_collision_fails_without_plan_write(db_session: Session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Understand retention."))
    persisted = TaskRepository(db_session).create(_task(objective))
    counterfeit = persisted.model_copy(update={"instruction": "Different semantics."})
    plan = _plan(objective, (counterfeit,))

    with pytest.raises(ValueError, match="Task identity collision"):
        _admit(db_session, plan, (counterfeit,))

    assert TaskRepository(db_session).get_by_id(persisted.task_id) == persisted
    assert PlanRepository(db_session).get_by_id(plan.plan_id) is None
    assert ActivePlanRepository(db_session).get_by_objective_id(objective.objective_id) is None


class _FingerprintMismatchCandidate:
    def __init__(self, plan: Plan) -> None:
        self._plan = plan

    def __getattr__(self, name: str) -> object:
        return getattr(self._plan, name)

    @property
    def fingerprint(self) -> str:
        return "sha256:" + "0" * 64

    def model_dump(
        self,
        *,
        mode: Literal["json"],
        exclude: set[str],
    ) -> dict[str, Any]:
        return self._plan.model_dump(mode=mode, exclude=exclude)


def test_fingerprint_failure_rolls_back_new_objective_and_task(
    db_session: Session,
) -> None:
    objective = Objective(text="Understand retention.")
    task = _task(objective)
    valid = _plan(objective, (task,))
    counterfeit = cast(Plan, _FingerprintMismatchCandidate(valid))

    with pytest.raises(ValueError, match="fingerprint"):
        _admit(db_session, counterfeit, (task,))

    assert ObjectiveRepository(db_session).get_by_id(objective.objective_id) is None
    assert TaskRepository(db_session).get_by_id(task.task_id) is None
    assert PlanRepository(db_session).get_by_id(valid.plan_id) is None
    assert db_session.exec(select(ActivePlanRecord)).all() == []


def test_failed_successor_leaves_existing_active_plan_unchanged(
    db_session: Session,
) -> None:
    objective = Objective(text="Understand retention.")
    first_task = _task(objective)
    active = _plan(objective, (first_task,))
    _admit(db_session, active, (first_task,))

    successor_task = _task(objective, instruction="Inspect a successor scope.")
    missing_assumption = Assumption(text="This premise is not admitted.")
    successor = _plan(
        objective,
        (successor_task,),
        assumptions=(missing_assumption,),
    )

    with pytest.raises(ValueError, match="Assumption"):
        _admit(db_session, successor, (successor_task,))

    assert PlanRepository(db_session).get_by_id(successor.plan_id) is None
    assert TaskRepository(db_session).get_by_id(successor_task.task_id) is None
    assert ActivePlanRepository(db_session).get_by_objective_id(
        objective.objective_id
    ) == active


def test_failure_after_staging_rolls_back_entire_bundle(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    objective = Objective(text="Understand retention.")
    task = _task(objective)
    plan = _plan(objective, (task,))

    def fail_activation(self: ActivePlanRepository, candidate: Plan) -> None:
        del self, candidate
        raise RuntimeError("injected activation failure")

    monkeypatch.setattr(ActivePlanRepository, "activate", fail_activation)

    with pytest.raises(RuntimeError, match="injected activation failure"):
        _admit(db_session, plan, (task,))

    assert ObjectiveRepository(db_session).get_by_id(objective.objective_id) is None
    assert TaskRepository(db_session).get_by_id(task.task_id) is None
    assert PlanRepository(db_session).get_by_id(plan.plan_id) is None
    assert db_session.exec(select(ActivePlanRecord)).all() == []


def test_successor_activation_is_objective_scoped_and_preserves_old_plan(
    db_session: Session,
) -> None:
    first_objective = Objective(text="Understand retention.")
    first_task = _task(first_objective)
    first_plan = _plan(first_objective, (first_task,))
    _admit(db_session, first_plan, (first_task,))

    successor = _plan(first_objective, (first_task,))
    _admit(db_session, successor, (first_task,))

    second_objective = Objective(text="Understand acquisition.")
    second_task = _task(second_objective)
    second_plan = _plan(second_objective, (second_task,))
    _admit(db_session, second_plan, (second_task,))

    assert PlanRepository(db_session).get_by_id(first_plan.plan_id) == first_plan
    assert ActivePlanRepository(db_session).get_by_objective_id(
        first_objective.objective_id
    ) == successor
    assert ActivePlanRepository(db_session).get_by_objective_id(
        second_objective.objective_id
    ) == second_plan
    assert len(db_session.exec(select(ActivePlanRecord)).all()) == 2
    assert {"update", "delete", "remove", "save"}.isdisjoint(vars(PlanRepository))


def test_plan_identity_can_be_persisted_only_once(db_session: Session) -> None:
    objective = Objective(text="Understand retention.")
    task = _task(objective)
    plan = _plan(objective, (task,))
    _admit(db_session, plan, (task,))

    with pytest.raises(ValueError, match="Plan identity already exists"):
        _admit(db_session, plan, (task,))

    assert PlanRepository(db_session).get_by_id(plan.plan_id) == plan
    assert ActivePlanRepository(db_session).get_by_objective_id(objective.objective_id) == plan
