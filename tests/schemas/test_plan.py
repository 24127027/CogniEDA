"""Canonical Plan domain and fingerprint invariants."""

from __future__ import annotations

import importlib.util
import inspect
from collections.abc import Iterable
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

import cognieda.schemas as schemas
import cognieda.schemas.plan as plan_module
from cognieda.agents.planner.context import PlanningContext
from cognieda.agents.planner.types import PlannerOutput, State
from cognieda.schemas import (
    PLAN_CONTRACT_VERSION,
    Assumption,
    FirstClassObjectType,
    Objective,
    Plan,
    PlanDependency,
    PlanPriority,
    PlanTaskBinding,
    Task,
    TaskKind,
    TaskStatus,
)

OBJECTIVE_ID = UUID("10000000-0000-0000-0000-000000000000")


def _objective(*, text: str = "Understand retention.") -> Objective:
    return Objective(objective_id=OBJECTIVE_ID, text=text)


def _task(
    *,
    task_id: UUID | None = None,
    objective_id: UUID = OBJECTIVE_ID,
    status: TaskStatus = TaskStatus.PENDING,
) -> Task:
    return Task(
        task_id=task_id or uuid4(),
        objective_id=objective_id,
        kind=TaskKind.DATA,
        instruction="Profile retention data.",
        status=status,
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


def _edge(prerequisite: Task, dependent: Task) -> PlanDependency:
    return PlanDependency(
        prerequisite_task_id=prerequisite.task_id,
        dependent_task_id=dependent.task_id,
    )


def _plan(
    tasks: Iterable[Task],
    *,
    objective: Objective | None = None,
    assumptions: Iterable[Assumption] = (),
    bindings: Iterable[PlanTaskBinding] | None = None,
    dependencies: Iterable[PlanDependency] = (),
    plan_id: UUID | None = None,
) -> Plan:
    task_tuple = tuple(tasks)
    return Plan.create(
        plan_id=plan_id,
        objective=objective or _objective(),
        assumptions=assumptions,
        task_bindings=(
            tuple(_binding(task) for task in task_tuple) if bindings is None else bindings
        ),
        dependencies=dependencies,
        tasks=task_tuple,
    )


def test_plan_owns_exact_objective_and_assumption_basis() -> None:
    task = _task()
    assumption = Assumption(text="Renewal dates are reliable.")
    plan = _plan([task], assumptions=[assumption])

    assert plan.objective == _objective()
    assert plan.assumptions == (assumption,)
    assert plan.contract_version == PLAN_CONTRACT_VERSION
    assert plan.task_ids == frozenset({task.task_id})


def test_plan_rejects_duplicate_assumption_identity() -> None:
    task = _task()
    assumption = Assumption(text="Renewal dates are reliable.")

    with pytest.raises(ValidationError, match="duplicate Assumption"):
        _plan([task], assumptions=[assumption, assumption])


def test_plan_task_binding_is_routing_free_and_exact() -> None:
    assert set(PlanTaskBinding.model_fields) == {"task_id", "order_rank", "priority"}
    prohibited = {
        "capability",
        "required_capability",
        "executor",
        "executor_role",
        "provider",
        "tool",
        "data_profile_id",
        "dataset_path",
        "method",
        "protocol",
    }
    assert prohibited.isdisjoint(Plan.model_fields)
    assert prohibited.isdisjoint(PlanTaskBinding.model_fields)


def test_extra_routing_field_is_rejected() -> None:
    task = _task()
    payload = _binding(task).model_dump()
    payload["provider"] = "local"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PlanTaskBinding.model_validate(payload)


@pytest.mark.parametrize("case", ["outside", "self", "duplicate", "cycle"])
def test_invalid_dependencies_are_rejected(case: str) -> None:
    first, second, outsider = _task(), _task(), _task()
    if case == "outside":
        dependencies = (_edge(first, outsider),)
        match = "outside membership"
    elif case == "self":
        with pytest.raises(ValidationError, match="self dependency"):
            _edge(first, first)
        return
    elif case == "duplicate":
        dependencies = (_edge(first, second), _edge(first, second))
        match = "duplicate dependency"
    else:
        dependencies = (_edge(first, second), _edge(second, first))
        match = "acyclic"

    with pytest.raises(ValidationError, match=match):
        _plan([first, second], dependencies=dependencies)


@pytest.mark.parametrize("case", ["missing", "extra", "duplicate", "wrong_objective"])
def test_exact_task_bundle_is_enforced(case: str) -> None:
    first, second = _task(), _task()
    plan = _plan([first])
    if case == "missing":
        supplied = ()
        match = "exactly match"
    elif case == "extra":
        supplied = (first, second)
        match = "exactly match"
    elif case == "duplicate":
        supplied = (first, first)
        match = "duplicate member Task"
    else:
        supplied = (
            Task(
                task_id=first.task_id,
                objective_id=uuid4(),
                kind=first.kind,
                instruction=first.instruction,
            ),
        )
        match = "Plan Objective"

    with pytest.raises(ValueError, match=match):
        plan.validate_tasks(supplied)


def test_create_requires_exact_task_membership() -> None:
    bound, extra = _task(), _task()
    with pytest.raises(ValueError, match="exactly match"):
        Plan.create(
            objective=_objective(),
            task_bindings=(_binding(bound),),
            tasks=(bound, extra),
        )


def test_canonical_ordering_stabilizes_serialization_and_fingerprint() -> None:
    first = _task(task_id=UUID("00000000-0000-0000-0000-000000000001"))
    second = _task(task_id=UUID("00000000-0000-0000-0000-000000000002"))
    first_assumption = Assumption(
        assumption_id=UUID("00000000-0000-0000-0000-000000000011"), text="First."
    )
    second_assumption = Assumption(
        assumption_id=UUID("00000000-0000-0000-0000-000000000012"), text="Second."
    )
    plan_id = uuid4()
    forward = _plan(
        [first, second],
        assumptions=[first_assumption, second_assumption],
        bindings=[_binding(first, order_rank=1), _binding(second, order_rank=0)],
        dependencies=[_edge(second, first)],
        plan_id=plan_id,
    )
    reverse = _plan(
        [second, first],
        assumptions=[second_assumption, first_assumption],
        bindings=[_binding(second, order_rank=0), _binding(first, order_rank=1)],
        dependencies=[_edge(second, first)],
        plan_id=plan_id,
    )

    assert forward.model_dump_json() == reverse.model_dump_json()
    assert forward.fingerprint == reverse.fingerprint


@pytest.mark.parametrize(
    "change", ["objective", "assumption", "membership", "rank", "priority", "edge"]
)
def test_semantic_plan_changes_change_fingerprint(change: str) -> None:
    first, second = _task(), _task()
    assumption = Assumption(text="Renewal dates are reliable.")
    original = _plan([first], assumptions=[assumption])

    if change == "objective":
        changed = _plan(
            [first], objective=_objective(text="Understand churn."), assumptions=[assumption]
        )
    elif change == "assumption":
        changed = _plan(
            [first],
            assumptions=[
                Assumption(assumption_id=assumption.assumption_id, text="Dates are estimated.")
            ],
        )
    elif change == "membership":
        changed = _plan([first, second], assumptions=[assumption])
    elif change == "rank":
        changed = _plan([first], assumptions=[assumption], bindings=[_binding(first, order_rank=2)])
    elif change == "priority":
        changed = _plan(
            [first],
            assumptions=[assumption],
            bindings=[_binding(first, priority=PlanPriority.HIGH)],
        )
    else:
        original = _plan([first, second], assumptions=[assumption])
        changed = _plan(
            [first, second], assumptions=[assumption], dependencies=[_edge(first, second)]
        )

    assert changed.fingerprint != original.fingerprint


def test_task_runtime_status_does_not_change_fingerprint() -> None:
    pending = _task()
    completed = pending.model_copy(update={"status": TaskStatus.COMPLETED})

    assert _plan([pending]).fingerprint == _plan([completed]).fingerprint


def test_fingerprint_payload_is_version_bound_and_routing_free() -> None:
    task = _task()
    plan = _plan([task])
    payload = plan._fingerprint_payload()

    assert set(payload) == {
        "contract_version",
        "objective",
        "assumptions",
        "task_bindings",
        "dependencies",
    }
    assert set(payload["task_bindings"][0]) == {"task_id", "order_rank", "priority"}
    source = inspect.getsource(plan_module).lower()
    for term in ("capability", "provider", "executor", "dataset_path"):
        assert term not in source


def test_plan_is_immutable_non_fco_and_outside_semantic_graph() -> None:
    plan = _plan([_task()])
    with pytest.raises(ValidationError, match="frozen"):
        plan.dependencies = ()

    assert "PLAN" not in FirstClassObjectType.__members__
    semantic_members = {
        FirstClassObjectType.OBJECTIVE,
        FirstClassObjectType.HYPOTHESIS,
        FirstClassObjectType.EVIDENCE,
        FirstClassObjectType.DISCOVERY,
    }
    assert all(member.value != "plan" for member in semantic_members)


def test_plan_revision_production_type_is_removed() -> None:
    assert not hasattr(schemas, "PlanRevision")
    assert importlib.util.find_spec("cognieda.schemas.plan_revision") is None


def test_planner_contracts_receive_no_plan_behavior_in_phase_one() -> None:
    assert "plan" not in PlanningContext.model_fields
    assert "plan" not in PlannerOutput.model_fields
    assert "plan" not in State.model_fields


def test_task_remains_an_independent_fco_without_plan_coordination() -> None:
    assert FirstClassObjectType.TASK.value == "task"
    assert {"plan_id", "order_rank", "priority", "dependency_ids"}.isdisjoint(Task.model_fields)
