"""Canonical minimal Plan domain and fingerprint invariants."""

from __future__ import annotations

import importlib.util
import inspect
from collections.abc import Iterable
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

import cognieda.schemas as schemas
import cognieda.schemas.plan as plan_module
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.types import PlannerOutput, PlannerResult
from cognieda.schemas import (
    Assumption,
    FirstClassObjectType,
    Objective,
    Plan,
    PlanDependency,
    Task,
    TaskKind,
    TaskStatus,
)

OBJECTIVE_ID = UUID("10000000-0000-0000-0000-000000000000")
FIRST_TASK_ID = UUID("20000000-0000-0000-0000-000000000001")
SECOND_TASK_ID = UUID("20000000-0000-0000-0000-000000000002")
THIRD_TASK_ID = UUID("20000000-0000-0000-0000-000000000003")


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


def _edge(prerequisite: Task, dependent: Task) -> PlanDependency:
    return PlanDependency(
        prerequisite_task_id=prerequisite.task_id,
        dependent_task_ids=(dependent.task_id,),
    )


def _plan(
    tasks: Iterable[Task],
    *,
    objective: Objective | None = None,
    assumptions: Iterable[Assumption] = (),
    task_ids: Iterable[UUID] | None = None,
    dependencies: Iterable[PlanDependency] = (),
    plan_id: UUID | None = None,
) -> Plan:
    task_tuple = tuple(tasks)
    return Plan.create(
        plan_id=plan_id,
        objective=objective or _objective(),
        assumptions=assumptions,
        task_ids=(tuple(task.task_id for task in task_tuple) if task_ids is None else task_ids),
        dependencies=dependencies,
        tasks=task_tuple,
    )


def test_plan_has_only_minimal_semantic_fields() -> None:
    task = _task()
    assumption = Assumption(text="Renewal dates are reliable.")
    plan = _plan([task], assumptions=[assumption])

    assert set(Plan.model_fields) == {
        "plan_id",
        "objective",
        "assumptions",
        "task_ids",
        "dependencies",
    }
    assert plan.objective == _objective()
    assert plan.assumptions == (assumption,)
    assert plan.task_ids == (task.task_id,)
    assert set(PlanDependency.model_fields) == {
        "prerequisite_task_id",
        "dependent_task_ids",
    }


def test_plan_rejects_duplicate_assumption_identity() -> None:
    task = _task()
    assumption = Assumption(text="Renewal dates are reliable.")

    with pytest.raises(ValidationError, match="duplicate Assumption"):
        _plan([task], assumptions=[assumption, assumption])


def test_plan_rejects_duplicate_task_ids() -> None:
    task = _task()

    with pytest.raises(ValidationError, match="duplicate Task IDs"):
        Plan(objective=_objective(), task_ids=(task.task_id, task.task_id))


@pytest.mark.parametrize("case", ["missing", "extra"])
def test_validate_tasks_requires_exact_set_equality(case: str) -> None:
    first = _task(task_id=FIRST_TASK_ID)
    second = _task(task_id=SECOND_TASK_ID)
    plan = _plan([first], task_ids=(first.task_id,))
    supplied = () if case == "missing" else (first, second)

    with pytest.raises(ValueError, match="exactly match task_ids membership"):
        plan.validate_tasks(supplied)


def test_validate_tasks_rejects_duplicate_task_objects() -> None:
    task = _task()
    plan = _plan([task])

    with pytest.raises(ValueError, match="duplicate Task objects"):
        plan.validate_tasks((task, task))


def test_validate_tasks_rejects_task_from_another_objective() -> None:
    task = _task(objective_id=uuid4())
    plan = Plan(objective=_objective(), task_ids=(task.task_id,))

    with pytest.raises(ValueError, match="Plan Objective"):
        plan.validate_tasks((task,))


def test_dependency_endpoint_outside_membership_fails() -> None:
    member, outsider = _task(), _task()

    with pytest.raises(ValidationError, match="outside membership"):
        Plan(
            objective=_objective(),
            task_ids=(member.task_id,),
            dependencies=(_edge(member, outsider),),
        )


def test_dependency_requires_dependents_and_rejects_duplicates() -> None:
    prerequisite, dependent = _task(), _task()

    with pytest.raises(ValidationError, match="at least 1 item"):
        PlanDependency(
            prerequisite_task_id=prerequisite.task_id,
            dependent_task_ids=(),
        )
    with pytest.raises(ValidationError, match="duplicate dependent"):
        PlanDependency(
            prerequisite_task_id=prerequisite.task_id,
            dependent_task_ids=(dependent.task_id, dependent.task_id),
        )


def test_dependency_rejects_self_edge() -> None:
    task = _task()

    with pytest.raises(ValidationError, match="self dependency"):
        PlanDependency(
            prerequisite_task_id=task.task_id,
            dependent_task_ids=(task.task_id,),
        )


def test_one_prerequisite_groups_many_canonical_dependents() -> None:
    prerequisite = _task(task_id=FIRST_TASK_ID)
    first_dependent = _task(task_id=SECOND_TASK_ID)
    second_dependent = _task(task_id=THIRD_TASK_ID)

    dependency = PlanDependency(
        prerequisite_task_id=prerequisite.task_id,
        dependent_task_ids=(second_dependent.task_id, first_dependent.task_id),
    )

    assert dependency.dependent_task_ids == (
        first_dependent.task_id,
        second_dependent.task_id,
    )


def test_plan_rejects_duplicate_prerequisite_groups() -> None:
    first, second, third = _task(), _task(), _task()

    with pytest.raises(ValidationError, match="duplicate prerequisite"):
        _plan(
            [first, second, third],
            dependencies=(_edge(first, second), _edge(first, third)),
        )


def test_plan_rejects_dependency_cycle() -> None:
    first, second, third = _task(), _task(), _task()

    with pytest.raises(ValidationError, match="acyclic"):
        _plan(
            [first, second, third],
            dependencies=(
                PlanDependency(
                    prerequisite_task_id=first.task_id,
                    dependent_task_ids=(second.task_id, third.task_id),
                ),
                _edge(second, third),
                _edge(third, first),
            ),
        )


def test_independent_tasks_are_unordered_and_deterministically_eligible() -> None:
    first = _task(task_id=FIRST_TASK_ID)
    second = _task(task_id=SECOND_TASK_ID)

    forward = _plan([first, second])
    reverse = _plan([second, first])

    assert forward.task_ids == reverse.task_ids == (FIRST_TASK_ID, SECOND_TASK_ID)
    assert forward.eligible_task_ids() == (FIRST_TASK_ID, SECOND_TASK_ID)


def test_dependency_controls_structural_eligibility() -> None:
    prerequisite = _task(task_id=FIRST_TASK_ID)
    dependent = _task(task_id=SECOND_TASK_ID)
    plan = _plan(
        [dependent, prerequisite],
        dependencies=(_edge(prerequisite, dependent),),
    )

    assert plan.eligible_task_ids() == (prerequisite.task_id,)
    assert plan.eligible_task_ids(completed_task_ids={prerequisite.task_id}) == (dependent.task_id,)
    with pytest.raises(ValueError, match="outside Plan membership"):
        plan.eligible_task_ids(completed_task_ids={uuid4()})


def test_many_to_one_dependency_requires_all_incoming_prerequisites() -> None:
    first = _task(task_id=FIRST_TASK_ID)
    second = _task(task_id=SECOND_TASK_ID)
    dependent = _task(task_id=THIRD_TASK_ID)
    plan = _plan(
        [first, second, dependent],
        dependencies=(_edge(first, dependent), _edge(second, dependent)),
    )

    assert plan.eligible_task_ids() == (first.task_id, second.task_id)
    assert plan.eligible_task_ids(completed_task_ids={first.task_id}) == (second.task_id,)
    assert plan.eligible_task_ids(
        completed_task_ids={first.task_id, second.task_id}
    ) == (dependent.task_id,)


def test_dependent_input_order_does_not_change_fingerprint() -> None:
    prerequisite = _task(task_id=FIRST_TASK_ID)
    first_dependent = _task(task_id=SECOND_TASK_ID)
    second_dependent = _task(task_id=THIRD_TASK_ID)
    tasks = (prerequisite, first_dependent, second_dependent)
    plan_id = uuid4()

    forward = _plan(
        tasks,
        plan_id=plan_id,
        dependencies=(
            PlanDependency(
                prerequisite_task_id=prerequisite.task_id,
                dependent_task_ids=(first_dependent.task_id, second_dependent.task_id),
            ),
        ),
    )
    reverse = _plan(
        tasks,
        plan_id=plan_id,
        dependencies=(
            PlanDependency(
                prerequisite_task_id=prerequisite.task_id,
                dependent_task_ids=(second_dependent.task_id, first_dependent.task_id),
            ),
        ),
    )

    assert forward.dependencies == reverse.dependencies
    assert forward.fingerprint == reverse.fingerprint


def test_canonical_input_order_does_not_change_serialization_or_fingerprint() -> None:
    first = _task(task_id=FIRST_TASK_ID)
    second = _task(task_id=SECOND_TASK_ID)
    third = _task(task_id=THIRD_TASK_ID)
    first_assumption = Assumption(
        assumption_id=UUID("30000000-0000-0000-0000-000000000001"),
        text="Dates are reliable.",
    )
    second_assumption = Assumption(
        assumption_id=UUID("30000000-0000-0000-0000-000000000002"),
        text="Rows are customers.",
    )
    dependencies = (_edge(first, third), _edge(second, third))
    plan_id = uuid4()

    forward = _plan(
        [first, second, third],
        plan_id=plan_id,
        assumptions=(first_assumption, second_assumption),
        dependencies=dependencies,
    )
    reverse = _plan(
        [third, second, first],
        plan_id=plan_id,
        assumptions=(second_assumption, first_assumption),
        dependencies=reversed(dependencies),
    )

    assert forward.model_dump_json() == reverse.model_dump_json()
    assert forward.fingerprint == reverse.fingerprint


@pytest.mark.parametrize("change", ["objective", "assumption", "membership", "edge"])
def test_each_plan_semantic_change_changes_fingerprint(change: str) -> None:
    first = _task(task_id=FIRST_TASK_ID)
    second = _task(task_id=SECOND_TASK_ID)
    assumption = Assumption(text="Dates are reliable.")
    original = _plan([first, second], assumptions=(assumption,))

    if change == "objective":
        changed = _plan(
            [first, second],
            objective=_objective(text="Understand churn."),
            assumptions=(assumption,),
        )
    elif change == "assumption":
        changed = _plan(
            [first, second],
            assumptions=(Assumption(text="Dates may be unreliable."),),
        )
    elif change == "membership":
        changed = _plan([first], assumptions=(assumption,))
    else:
        changed = _plan(
            [first, second],
            assumptions=(assumption,),
            dependencies=(_edge(first, second),),
        )

    assert changed.fingerprint != original.fingerprint


def test_fingerprint_payload_contains_only_current_plan_semantics() -> None:
    first, second = _task(), _task()
    assumption = Assumption(text="Dates are reliable.")
    plan = _plan(
        [first, second],
        assumptions=(assumption,),
        dependencies=(_edge(first, second),),
    )

    payload = plan._fingerprint_payload()

    assert set(payload) == {"objective", "assumptions", "task_ids", "dependencies"}
    assert "plan_id" not in payload
    task_ids = payload["task_ids"]
    assert isinstance(task_ids, list)
    assert all(isinstance(task_id, str) for task_id in task_ids)


def test_task_status_and_semantic_payload_are_not_fingerprint_content() -> None:
    pending = _task(task_id=FIRST_TASK_ID)
    changed = Task(
        task_id=pending.task_id,
        objective_id=pending.objective_id,
        kind=TaskKind.GRAPH,
        instruction="Ask a different bounded graph question.",
        status=TaskStatus.COMPLETED,
    )

    assert _plan([pending]).fingerprint == _plan([changed]).fingerprint


def test_obsolete_plan_abstractions_are_absent() -> None:
    source = inspect.getsource(plan_module)

    for symbol in (
        "PlanTaskBinding",
        "task_bindings",
        "PlanPriority",
        "order_rank",
        "PlanContractVersion",
        "PLAN_CONTRACT_VERSION",
        "contract_version",
    ):
        assert symbol not in source
        assert not hasattr(schemas, symbol)


def test_plan_contract_excludes_routing_data_and_lifecycle_fields() -> None:
    prohibited = {
        "priority",
        "order_rank",
        "capability",
        "executor",
        "provider",
        "tool",
        "data_profile",
        "data_profile_id",
        "status",
        "approval_state",
        "activation_state",
    }

    assert prohibited.isdisjoint(Plan.model_fields)
    assert prohibited.isdisjoint(PlanDependency.model_fields)


def test_plan_is_immutable_non_fco_and_has_explicit_planner_surfaces() -> None:
    task = _task()
    plan = _plan([task])

    with pytest.raises(ValidationError, match="frozen"):
        plan.task_ids = ()
    assert "PLAN" not in FirstClassObjectType.__members__
    assert "pending_plan" in PlannerContext.model_fields
    assert "pending_tasks" in PlannerContext.model_fields
    assert "active_plan" in PlannerContext.model_fields
    assert "plan" in PlannerResult.model_fields
    assert "plan" not in PlannerOutput.model_fields


def test_plan_revision_production_type_remains_removed() -> None:
    assert not hasattr(schemas, "PlanRevision")
    assert importlib.util.find_spec("cognieda.schemas.plan_revision") is None


def test_task_remains_independent_of_plan_coordination() -> None:
    assert FirstClassObjectType.TASK.value == "task"
    assert {
        "plan_id",
        "dependency_ids",
        "priority",
        "order_rank",
    }.isdisjoint(Task.model_fields)
