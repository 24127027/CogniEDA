"""Executable Plan V1 domain and architecture invariants."""

from __future__ import annotations

import inspect
from collections.abc import Iterable
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

import cognieda.schemas as schemas
import cognieda.schemas.plan as plan_module
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.contracts import PlannerOutput
from cognieda.agents.planner.state import PlannerState
from cognieda.schemas import (
    PLAN_CONTRACT_VERSION,
    Assumption,
    FirstClassObjectType,
    Objective,
    Plan,
    PlanDependency,
    PlanPriority,
    PlanTaskBinding,
    SessionFrame,
    Task,
    TaskKind,
    TaskStatus,
)
from cognieda.schemas import enums as schema_enums

OBJECTIVE_ID = UUID("10000000-0000-0000-0000-000000000000")


def _task(
    *,
    task_id: UUID | None = None,
    objective_id: UUID = OBJECTIVE_ID,
    kind: TaskKind = TaskKind.DATA,
    status: TaskStatus = TaskStatus.PENDING,
) -> Task:
    return Task(
        task_id=task_id or uuid4(),
        objective_id=objective_id,
        kind=kind,
        instruction=f"Perform bounded {kind.value} work.",
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


def _plan(
    tasks: Iterable[Task],
    *,
    bindings: Iterable[PlanTaskBinding] | None = None,
    dependencies: Iterable[PlanDependency] = (),
    objective_id: UUID = OBJECTIVE_ID,
    objective: Objective | None = None,
    assumptions: Iterable[Assumption] = (),
    plan_id: UUID | None = None,
) -> Plan:
    task_tuple = tuple(tasks)
    return Plan.create(
        plan_id=plan_id,
        objective=objective or Objective(objective_id=objective_id, text="Test objective"),
        assumptions=assumptions,
        task_bindings=(
            tuple(_binding(task) for task in task_tuple) if bindings is None else tuple(bindings)
        ),
        dependencies=dependencies,
        tasks=task_tuple,
    )


def _edge(prerequisite: Task, dependent: Task) -> PlanDependency:
    return PlanDependency(
        prerequisite_task_id=prerequisite.task_id,
        dependent_task_id=dependent.task_id,
    )


def test_valid_one_task_plan_has_derived_membership_and_versioned_digest() -> None:
    task = _task()

    plan = _plan([task])

    assert plan.task_ids == frozenset({task.task_id})
    assert len(plan.task_bindings) == 1
    assert plan.contract_version == PLAN_CONTRACT_VERSION
    assert plan.fingerprint.startswith("sha256:")
    assert len(plan.fingerprint) == len("sha256:") + 64


def test_valid_multi_root_dag_exposes_all_roots_as_eligible() -> None:
    first_root, second_root, leaf = _task(), _task(), _task()
    plan = _plan(
        [first_root, second_root, leaf],
        dependencies=(_edge(first_root, leaf), _edge(second_root, leaf)),
    )

    assert set(plan.eligible_task_ids()) == {first_root.task_id, second_root.task_id}


def test_valid_multi_leaf_dag_exposes_leaves_after_the_root_completes() -> None:
    root, first_leaf, second_leaf = _task(), _task(), _task()
    plan = _plan(
        [root, first_leaf, second_leaf],
        dependencies=(_edge(root, first_leaf), _edge(root, second_leaf)),
    )

    assert set(plan.eligible_task_ids(completed_task_ids={root.task_id})) == {
        first_leaf.task_id,
        second_leaf.task_id,
    }


def test_independent_tasks_may_share_order_rank() -> None:
    first, second = _task(), _task()
    plan = _plan(
        [first, second],
        bindings=(_binding(first, order_rank=1), _binding(second, order_rank=1)),
    )

    assert {binding.order_rank for binding in plan.task_bindings} == {1}
    assert plan.task_ids == frozenset({first.task_id, second.task_id})


def test_each_member_task_has_exactly_one_binding_source_of_truth() -> None:
    tasks = (_task(), _task())
    plan = _plan(tasks)

    assert plan.task_ids == frozenset(binding.task_id for binding in plan.task_bindings)
    assert "task_ids" not in Plan.model_fields


def test_duplicate_binding_is_rejected() -> None:
    task = _task()
    binding = _binding(task)

    with pytest.raises(ValidationError, match="duplicate PlanTaskBinding"):
        _plan([task], bindings=(binding, binding))


def test_binding_without_member_task_is_rejected() -> None:
    task = _task()

    with pytest.raises(ValidationError, match="exactly match binding membership"):
        Plan.create(
            objective=Objective(objective_id=OBJECTIVE_ID, text="Test objective"),
            task_bindings=(_binding(task),),
            tasks=(),
        )


def test_unbound_member_task_is_rejected() -> None:
    bound, unbound = _task(), _task()

    with pytest.raises(ValidationError, match="exactly match binding membership"):
        Plan.create(
            objective=Objective(objective_id=OBJECTIVE_ID, text="Test objective"),
            task_bindings=(_binding(bound),),
            tasks=(bound, unbound),
        )


def test_duplicate_member_task_is_rejected() -> None:
    task = _task()

    with pytest.raises(ValidationError, match="duplicate member Task"):
        Plan.create(
            objective=Objective(objective_id=OBJECTIVE_ID, text="Test objective"),
            task_bindings=(_binding(task),),
            tasks=(task, task),
        )


def test_task_from_another_objective_is_rejected() -> None:
    task = _task(objective_id=uuid4())

    with pytest.raises(ValidationError, match="Plan Objective"):
        _plan([task])


def test_dependency_endpoint_outside_membership_is_rejected() -> None:
    member, outsider = _task(), _task()

    with pytest.raises(ValidationError, match="outside membership"):
        _plan([member], dependencies=(_edge(member, outsider),))


def test_self_dependency_is_rejected() -> None:
    task = _task()

    with pytest.raises(ValidationError, match="self dependency"):
        PlanDependency(
            prerequisite_task_id=task.task_id,
            dependent_task_id=task.task_id,
        )


def test_duplicate_dependency_is_rejected() -> None:
    first, second = _task(), _task()
    edge = _edge(first, second)

    with pytest.raises(ValidationError, match="duplicate dependency"):
        _plan([first, second], dependencies=(edge, edge))


def test_direct_cycle_is_rejected() -> None:
    first, second = _task(), _task()

    with pytest.raises(ValidationError, match="acyclic"):
        _plan(
            [first, second],
            dependencies=(_edge(first, second), _edge(second, first)),
        )


def test_indirect_cycle_is_rejected() -> None:
    first, second, third = _task(), _task(), _task()

    with pytest.raises(ValidationError, match="acyclic"):
        _plan(
            [first, second, third],
            dependencies=(
                _edge(first, second),
                _edge(second, third),
                _edge(third, first),
            ),
        )


@pytest.mark.parametrize("kind", list(TaskKind))
def test_every_task_kind_is_structural_plan_membership_without_a_route(
    kind: TaskKind,
) -> None:
    task = _task(kind=kind)

    plan = _plan([task])

    assert plan.task_ids == frozenset({task.task_id})
    assert set(PlanTaskBinding.model_fields) == {
        "task_id",
        "order_rank",
        "priority",
    }


def test_binding_rejects_removed_assigned_role() -> None:
    task = _task(kind=TaskKind.DATA)
    payload = _binding(task).model_dump()
    payload["assigned_role"] = "data_explorer"

    assert "assigned_role" not in PlanTaskBinding.model_fields
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PlanTaskBinding.model_validate(payload)


def test_plan_contract_fields_exclude_execution_routing() -> None:
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

    assert prohibited.isdisjoint(Plan.model_fields)
    assert prohibited.isdisjoint(PlanTaskBinding.model_fields)


def test_plan_task_role_is_removed_from_schema_surfaces() -> None:
    assert not hasattr(schema_enums, "PlanTaskRole")
    assert not hasattr(schemas, "PlanTaskRole")


def test_negative_order_rank_is_rejected() -> None:
    task = _task()

    with pytest.raises(ValidationError):
        _binding(task, order_rank=-1)


def test_tied_order_rank_is_accepted() -> None:
    first, second = _task(), _task()

    assert _plan(
        [first, second],
        bindings=(_binding(first, order_rank=3), _binding(second, order_rank=3)),
    )


def test_priority_defaults_to_normal() -> None:
    task = _task()

    assert _binding(task).priority is PlanPriority.NORMAL


@pytest.mark.parametrize("priority", list(PlanPriority))
def test_all_finite_priorities_are_accepted(priority: PlanPriority) -> None:
    task = _task()

    assert _plan([task], bindings=(_binding(task, priority=priority),))


def test_invalid_priority_is_rejected() -> None:
    task = _task()
    values = _binding(task).model_dump()
    values["priority"] = "urgent"

    with pytest.raises(ValidationError):
        PlanTaskBinding.model_validate(values)


def test_plan_contracts_have_no_data_profile_fields() -> None:
    prohibited = {
        "data_profile_id",
        "data_profile_ids",
        "profile_id",
        "profile_refs",
        "dataset_path",
        "column_bindings",
        "row_filters",
        "cohort_bindings",
        "population_bindings",
        "variable_bindings",
    }

    assert prohibited.isdisjoint(Plan.model_fields)
    assert prohibited.isdisjoint(PlanTaskBinding.model_fields)


def test_task_schema_has_no_capability_or_plan_coordination_fields() -> None:
    prohibited = {
        "required_capability",
        "executor_role",
        "assigned_role",
        "dependency_ids",
        "parent_task_id",
        "order_rank",
        "order_index",
        "priority",
        "plan_id",
        "approval_state",
        "activation_state",
    }

    assert prohibited.isdisjoint(Task.model_fields)


def test_canonical_serialization_is_deterministic() -> None:
    first = _task(task_id=UUID("00000000-0000-0000-0000-000000000001"))
    second = _task(task_id=UUID("00000000-0000-0000-0000-000000000002"))
    plan_id = uuid4()
    forward = _plan(
        [first, second],
        bindings=(_binding(first, order_rank=1), _binding(second, order_rank=0)),
        dependencies=(_edge(first, second),),
        plan_id=plan_id,
    )
    reverse = _plan(
        [second, first],
        bindings=(_binding(second, order_rank=0), _binding(first, order_rank=1)),
        dependencies=(_edge(first, second),),
        plan_id=plan_id,
    )

    assert forward.model_dump_json() == reverse.model_dump_json()


def test_binding_input_order_does_not_change_fingerprint() -> None:
    first, second = _task(), _task()
    bindings = (_binding(first, order_rank=1), _binding(second, order_rank=1))

    assert (
        _plan([first, second], bindings=bindings).fingerprint
        == _plan([second, first], bindings=reversed(bindings)).fingerprint
    )


def test_dependency_input_order_does_not_change_fingerprint() -> None:
    root, first_leaf, second_leaf = _task(), _task(), _task()
    dependencies = (_edge(root, first_leaf), _edge(root, second_leaf))

    assert (
        _plan([root, first_leaf, second_leaf], dependencies=dependencies).fingerprint
        == _plan(
            [second_leaf, first_leaf, root], dependencies=reversed(dependencies)
        ).fingerprint
    )


def test_fingerprint_payload_has_only_plan_coordination_content() -> None:
    task = _task()
    plan = _plan([task])

    payload = plan._fingerprint_payload()
    binding_payload = payload["task_bindings"][0]
    assert set(binding_payload) == {"task_id", "order_rank", "priority"}
    serialized = plan.model_dump_json()
    assert "provider" not in serialized
    assert "capability" not in serialized


def test_plan_source_has_no_execution_routing_contract() -> None:
    source = inspect.getsource(plan_module)

    assert "required_capability" not in source
    assert "_COMPATIBLE_CAPABILITIES" not in source
    assert "Capability" not in source
    assert not hasattr(schema_enums, "Capability")
    assert not hasattr(schemas, "Capability")


@pytest.mark.parametrize(
    ("field", "changed_value"),
    [("order_rank", 2), ("priority", PlanPriority.HIGH)],
)
def test_changing_binding_coordination_changes_fingerprint(
    field: str,
    changed_value: object,
) -> None:
    task = _task()
    original = _plan([task])
    changed = _plan(
        [task],
        bindings=(_binding(task).model_copy(update={field: changed_value}),),
    )

    assert changed.fingerprint != original.fingerprint


def test_changing_dependency_changes_fingerprint() -> None:
    first, second = _task(), _task()

    assert (
        _plan([first, second]).fingerprint
        != _plan([first, second], dependencies=(_edge(first, second),)).fingerprint
    )


def test_changing_membership_changes_fingerprint() -> None:
    first, second = _task(), _task()

    assert _plan([first]).fingerprint != _plan([first, second]).fingerprint


def test_changing_objective_representation_changes_fingerprint() -> None:
    task = _task()
    first = Objective(objective_id=OBJECTIVE_ID, text="First framing")
    second = Objective(objective_id=OBJECTIVE_ID, text="Second framing")

    assert _plan([task], objective=first).fingerprint != _plan(
        [task], objective=second
    ).fingerprint


def test_changing_exact_assumption_basis_changes_fingerprint() -> None:
    task = _task()
    assumption = Assumption(text="Human-authored planning premise")

    assert _plan([task]).fingerprint != _plan(
        [task], assumptions=(assumption,)
    ).fingerprint


def test_duplicate_assumption_identity_is_rejected() -> None:
    task = _task()
    assumption = Assumption(text="Exact Human-authored premise")

    with pytest.raises(ValidationError, match="duplicate Assumption"):
        _plan([task], assumptions=(assumption, assumption))


def test_task_execution_status_does_not_change_fingerprint() -> None:
    pending = _task(status=TaskStatus.PENDING)
    completed = Task(
        task_id=pending.task_id,
        objective_id=pending.objective_id,
        kind=pending.kind,
        instruction=pending.instruction,
        status=TaskStatus.COMPLETED,
    )

    assert _plan([pending]).fingerprint == _plan([completed]).fingerprint


def test_task_semantic_payload_does_not_change_fingerprint() -> None:
    original = _task(kind=TaskKind.DATA)
    changed = Task(
        task_id=original.task_id,
        objective_id=original.objective_id,
        kind=TaskKind.GRAPH,
        instruction="Ask a different bounded graph question.",
        status=TaskStatus.FAILED,
    )

    assert _plan([original]).fingerprint == _plan([changed]).fingerprint


def test_concrete_data_profile_identity_is_not_fingerprint_content() -> None:
    task = _task()
    plan = _plan([task])

    assert "data_profile" not in plan.model_dump_json()
    assert "data_profile" not in plan._fingerprint_payload()


def test_plan_has_no_stopping_replan_or_lifecycle_policy_fields() -> None:
    prohibited = {
        "stopping_condition",
        "stopping_conditions",
        "replan_trigger",
        "replan_triggers",
        "replan_cause",
        "approval_state",
        "activation_state",
        "successor_plan_id",
    }

    assert prohibited.isdisjoint(Plan.model_fields)


def test_plan_is_not_an_fco_or_semantic_graph_member() -> None:
    assert "PLAN_REVISION" not in FirstClassObjectType.__members__
    semantic_graph_members = {
        FirstClassObjectType.OBJECTIVE,
        FirstClassObjectType.HYPOTHESIS,
        FirstClassObjectType.EVIDENCE,
        FirstClassObjectType.DISCOVERY,
    }
    assert all(member.value != "plan" for member in semantic_graph_members)


def test_plan_does_not_change_materialized_session_frame_categories() -> None:
    assert set(SessionFrame.model_fields) == {
        "objective",
        "assumptions",
        "tasks",
        "evidences",
        "discoveries",
        "data_profile",
    }


def test_planner_does_not_author_or_receive_plan() -> None:
    assert "plan" not in PlannerContext.model_fields
    assert "plan" not in PlannerOutput.model_fields
    assert "plan" not in PlannerState.model_fields


def test_dependency_eligibility_overrides_lower_dependent_order_rank() -> None:
    prerequisite, dependent = _task(), _task()
    plan = _plan(
        [prerequisite, dependent],
        bindings=(
            _binding(prerequisite, order_rank=10),
            _binding(dependent, order_rank=0),
        ),
        dependencies=(_edge(prerequisite, dependent),),
    )

    assert plan.eligible_task_ids() == (prerequisite.task_id,)
    assert plan.eligible_task_ids(completed_task_ids={prerequisite.task_id}) == (
        dependent.task_id,
    )


def test_plan_is_immutable_and_requires_member_task_construction() -> None:
    task = _task()
    plan = _plan([task])

    with pytest.raises(ValidationError, match="requires Tasks"):
        Plan(
            objective=Objective(objective_id=OBJECTIVE_ID, text="Test objective"),
            task_bindings=(_binding(task),),
        )
    with pytest.raises(ValidationError, match="frozen"):
        plan.dependencies = ()
