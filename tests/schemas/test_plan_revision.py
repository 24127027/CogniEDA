"""Executable PlanRevision V1 domain and architecture invariants."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from cognieda.agents.planner.context import PlanningContext
from cognieda.agents.planner.types import PlannerOutput, State
from cognieda.execution import Capability
from cognieda.schemas import (
    PLAN_REVISION_CONTRACT_VERSION,
    FirstClassObjectType,
    PlanDependency,
    PlanPriority,
    PlanRevision,
    PlanTaskBinding,
    PlanTaskRole,
    SessionFrame,
    Task,
    TaskKind,
    TaskStatus,
)

OBJECTIVE_ID = UUID("10000000-0000-0000-0000-000000000000")

_DEFAULT_BINDING: dict[TaskKind, tuple[Capability | None, PlanTaskRole]] = {
    TaskKind.DATA: (Capability.DATA_ANALYSIS, PlanTaskRole.DATA_EXPLORER),
    TaskKind.SCIENTIFIC: (
        Capability.HYPOTHESIS_TESTING,
        PlanTaskRole.HYPOTHESIS_ANALYST,
    ),
    TaskKind.GRAPH: (Capability.GRAPH_MINING, PlanTaskRole.GRAPH_MINER),
    TaskKind.SYNTHESIS: (None, PlanTaskRole.PLANNER),
}


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
    capability: Capability | None | object = ...,
    role: PlanTaskRole | None = None,
    order_rank: int = 0,
    priority: PlanPriority = PlanPriority.NORMAL,
) -> PlanTaskBinding:
    default_capability, default_role = _DEFAULT_BINDING[task.kind]
    selected_capability = default_capability if capability is ... else capability
    assert isinstance(selected_capability, Capability) or selected_capability is None
    return PlanTaskBinding(
        task_id=task.task_id,
        required_capability=selected_capability,
        assigned_role=role or default_role,
        order_rank=order_rank,
        priority=priority,
    )


def _revision(
    tasks: Iterable[Task],
    *,
    bindings: Iterable[PlanTaskBinding] | None = None,
    dependencies: Iterable[PlanDependency] = (),
    objective_id: UUID = OBJECTIVE_ID,
    plan_revision_id: UUID | None = None,
) -> PlanRevision:
    task_tuple = tuple(tasks)
    return PlanRevision.create(
        plan_revision_id=plan_revision_id,
        objective_id=objective_id,
        task_bindings=(
            tuple(_binding(task) for task in task_tuple) if bindings is None else tuple(bindings)
        ),
        dependencies=dependencies,
        authoritative_tasks=task_tuple,
    )


def _edge(prerequisite: Task, dependent: Task) -> PlanDependency:
    return PlanDependency(
        prerequisite_task_id=prerequisite.task_id,
        dependent_task_id=dependent.task_id,
    )


def test_valid_one_task_plan_revision_has_derived_membership_and_versioned_digest() -> None:
    task = _task()

    revision = _revision([task])

    assert revision.task_ids == frozenset({task.task_id})
    assert len(revision.task_bindings) == 1
    assert revision.contract_version == PLAN_REVISION_CONTRACT_VERSION
    assert revision.fingerprint.startswith("sha256:")
    assert len(revision.fingerprint) == len("sha256:") + 64


def test_valid_multi_root_dag_exposes_all_roots_as_eligible() -> None:
    first_root, second_root, leaf = _task(), _task(), _task()
    revision = _revision(
        [first_root, second_root, leaf],
        dependencies=(_edge(first_root, leaf), _edge(second_root, leaf)),
    )

    assert set(revision.eligible_task_ids()) == {first_root.task_id, second_root.task_id}


def test_valid_multi_leaf_dag_exposes_leaves_after_the_root_completes() -> None:
    root, first_leaf, second_leaf = _task(), _task(), _task()
    revision = _revision(
        [root, first_leaf, second_leaf],
        dependencies=(_edge(root, first_leaf), _edge(root, second_leaf)),
    )

    assert set(revision.eligible_task_ids(completed_task_ids={root.task_id})) == {
        first_leaf.task_id,
        second_leaf.task_id,
    }


def test_independent_tasks_may_share_order_rank() -> None:
    first, second = _task(), _task()
    revision = _revision(
        [first, second],
        bindings=(_binding(first, order_rank=1), _binding(second, order_rank=1)),
    )

    assert {binding.order_rank for binding in revision.task_bindings} == {1}
    assert revision.task_ids == frozenset({first.task_id, second.task_id})


def test_each_member_task_has_exactly_one_binding_source_of_truth() -> None:
    tasks = (_task(), _task())
    revision = _revision(tasks)

    assert revision.task_ids == frozenset(binding.task_id for binding in revision.task_bindings)
    assert "task_ids" not in PlanRevision.model_fields


def test_duplicate_binding_is_rejected() -> None:
    task = _task()
    binding = _binding(task)

    with pytest.raises(ValidationError, match="duplicate PlanTaskBinding"):
        _revision([task], bindings=(binding, binding))


def test_missing_authoritative_task_is_rejected() -> None:
    task = _task()

    with pytest.raises(ValidationError, match="without an authoritative Task"):
        PlanRevision.create(
            objective_id=OBJECTIVE_ID,
            task_bindings=(_binding(task),),
            authoritative_tasks=(),
        )


def test_duplicate_authoritative_task_is_rejected() -> None:
    task = _task()

    with pytest.raises(ValidationError, match="duplicate authoritative Task"):
        PlanRevision.create(
            objective_id=OBJECTIVE_ID,
            task_bindings=(_binding(task),),
            authoritative_tasks=(task, task),
        )


def test_task_from_another_objective_is_rejected() -> None:
    task = _task(objective_id=uuid4())

    with pytest.raises(ValidationError, match="PlanRevision Objective"):
        _revision([task])


def test_dependency_endpoint_outside_membership_is_rejected() -> None:
    member, outsider = _task(), _task()

    with pytest.raises(ValidationError, match="outside membership"):
        _revision([member], dependencies=(_edge(member, outsider),))


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
        _revision([first, second], dependencies=(edge, edge))


def test_direct_cycle_is_rejected() -> None:
    first, second = _task(), _task()

    with pytest.raises(ValidationError, match="acyclic"):
        _revision(
            [first, second],
            dependencies=(_edge(first, second), _edge(second, first)),
        )


def test_indirect_cycle_is_rejected() -> None:
    first, second, third = _task(), _task(), _task()

    with pytest.raises(ValidationError, match="acyclic"):
        _revision(
            [first, second, third],
            dependencies=(
                _edge(first, second),
                _edge(second, third),
                _edge(third, first),
            ),
        )


@pytest.mark.parametrize(
    "capability",
    [
        Capability.DATA_ANALYSIS,
        Capability.DATA_PROFILING,
        Capability.DATA_TRANSFORMATION,
    ],
)
def test_data_capability_and_data_explorer_role_are_valid(capability: Capability) -> None:
    task = _task(kind=TaskKind.DATA)

    revision = _revision([task], bindings=(_binding(task, capability=capability),))

    assert revision.task_bindings[0].assigned_role is PlanTaskRole.DATA_EXPLORER


def test_data_with_hypothesis_testing_is_rejected() -> None:
    task = _task(kind=TaskKind.DATA)

    with pytest.raises(ValidationError, match="incompatible required capability"):
        _revision(
            [task],
            bindings=(_binding(task, capability=Capability.HYPOTHESIS_TESTING),),
        )


def test_scientific_hypothesis_testing_and_analyst_role_are_valid() -> None:
    task = _task(kind=TaskKind.SCIENTIFIC)

    revision = _revision([task])

    assert revision.task_bindings[0].required_capability is Capability.HYPOTHESIS_TESTING
    assert revision.task_bindings[0].assigned_role is PlanTaskRole.HYPOTHESIS_ANALYST


def test_scientific_with_data_analysis_is_rejected() -> None:
    task = _task(kind=TaskKind.SCIENTIFIC)

    with pytest.raises(ValidationError, match="incompatible required capability"):
        _revision(
            [task],
            bindings=(_binding(task, capability=Capability.DATA_ANALYSIS),),
        )


def test_graph_mining_and_graph_miner_role_are_valid() -> None:
    task = _task(kind=TaskKind.GRAPH)

    revision = _revision([task])

    assert revision.task_bindings[0].required_capability is Capability.GRAPH_MINING
    assert revision.task_bindings[0].assigned_role is PlanTaskRole.GRAPH_MINER


def test_synthesis_none_capability_and_planner_role_are_valid() -> None:
    task = _task(kind=TaskKind.SYNTHESIS)

    revision = _revision([task])

    assert revision.task_bindings[0].required_capability is None
    assert revision.task_bindings[0].assigned_role is PlanTaskRole.PLANNER


def test_synthesis_with_dispatcher_capability_is_rejected() -> None:
    task = _task(kind=TaskKind.SYNTHESIS)

    with pytest.raises(ValidationError, match="incompatible required capability"):
        _revision(
            [task],
            bindings=(_binding(task, capability=Capability.DATA_ANALYSIS),),
        )


def test_task_kind_and_role_mismatch_is_rejected() -> None:
    task = _task(kind=TaskKind.DATA)

    with pytest.raises(ValidationError, match="incompatible assigned role"):
        _revision([task], bindings=(_binding(task, role=PlanTaskRole.PLANNER),))


def test_negative_order_rank_is_rejected() -> None:
    task = _task()

    with pytest.raises(ValidationError):
        _binding(task, order_rank=-1)


def test_tied_order_rank_is_accepted() -> None:
    first, second = _task(), _task()

    assert _revision(
        [first, second],
        bindings=(_binding(first, order_rank=3), _binding(second, order_rank=3)),
    )


def test_priority_defaults_to_normal() -> None:
    task = _task()

    assert _binding(task).priority is PlanPriority.NORMAL


@pytest.mark.parametrize("priority", list(PlanPriority))
def test_all_finite_priorities_are_accepted(priority: PlanPriority) -> None:
    task = _task()

    assert _revision([task], bindings=(_binding(task, priority=priority),))


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

    assert prohibited.isdisjoint(PlanRevision.model_fields)
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
        "plan_revision_id",
        "approval_state",
        "activation_state",
    }

    assert prohibited.isdisjoint(Task.model_fields)


def test_canonical_serialization_is_deterministic() -> None:
    first = _task(task_id=UUID("00000000-0000-0000-0000-000000000001"))
    second = _task(task_id=UUID("00000000-0000-0000-0000-000000000002"))
    revision_id = uuid4()
    forward = _revision(
        [first, second],
        bindings=(_binding(first, order_rank=1), _binding(second, order_rank=0)),
        dependencies=(_edge(first, second),),
        plan_revision_id=revision_id,
    )
    reverse = _revision(
        [second, first],
        bindings=(_binding(second, order_rank=0), _binding(first, order_rank=1)),
        dependencies=(_edge(first, second),),
        plan_revision_id=revision_id,
    )

    assert forward.model_dump_json() == reverse.model_dump_json()


def test_binding_input_order_does_not_change_fingerprint() -> None:
    first, second = _task(), _task()
    bindings = (_binding(first, order_rank=1), _binding(second, order_rank=1))

    assert (
        _revision([first, second], bindings=bindings).fingerprint
        == _revision([second, first], bindings=reversed(bindings)).fingerprint
    )


def test_dependency_input_order_does_not_change_fingerprint() -> None:
    root, first_leaf, second_leaf = _task(), _task(), _task()
    dependencies = (_edge(root, first_leaf), _edge(root, second_leaf))

    assert (
        _revision([root, first_leaf, second_leaf], dependencies=dependencies).fingerprint
        == _revision(
            [second_leaf, first_leaf, root], dependencies=reversed(dependencies)
        ).fingerprint
    )


def test_changing_capability_changes_fingerprint() -> None:
    task = _task()

    assert (
        _revision(
            [task], bindings=(_binding(task, capability=Capability.DATA_ANALYSIS),)
        ).fingerprint
        != _revision(
            [task], bindings=(_binding(task, capability=Capability.DATA_PROFILING),)
        ).fingerprint
    )


def test_changing_role_changes_fingerprint_contribution() -> None:
    task = _task()
    revision = _revision([task])
    changed_binding = revision.task_bindings[0].model_copy(
        update={"assigned_role": PlanTaskRole.PLANNER}
    )
    structurally_changed = PlanRevision.model_construct(
        plan_revision_id=revision.plan_revision_id,
        objective_id=revision.objective_id,
        task_bindings=(changed_binding,),
        dependencies=revision.dependencies,
        contract_version=revision.contract_version,
    )

    assert structurally_changed.fingerprint != revision.fingerprint
    with pytest.raises(ValidationError, match="incompatible assigned role"):
        _revision([task], bindings=(changed_binding,))


@pytest.mark.parametrize(
    ("field", "changed_value"),
    [("order_rank", 2), ("priority", PlanPriority.HIGH)],
)
def test_changing_binding_coordination_changes_fingerprint(
    field: str,
    changed_value: object,
) -> None:
    task = _task()
    original = _revision([task])
    changed = _revision(
        [task],
        bindings=(_binding(task).model_copy(update={field: changed_value}),),
    )

    assert changed.fingerprint != original.fingerprint


def test_changing_dependency_changes_fingerprint() -> None:
    first, second = _task(), _task()

    assert (
        _revision([first, second]).fingerprint
        != _revision([first, second], dependencies=(_edge(first, second),)).fingerprint
    )


def test_changing_membership_changes_fingerprint() -> None:
    first, second = _task(), _task()

    assert _revision([first]).fingerprint != _revision([first, second]).fingerprint


def test_task_execution_status_does_not_change_fingerprint() -> None:
    pending = _task(status=TaskStatus.PENDING)
    completed = Task(
        task_id=pending.task_id,
        objective_id=pending.objective_id,
        kind=pending.kind,
        instruction=pending.instruction,
        status=TaskStatus.COMPLETED,
    )

    assert _revision([pending]).fingerprint == _revision([completed]).fingerprint


def test_concrete_data_profile_identity_is_not_fingerprint_content() -> None:
    task = _task()
    revision = _revision([task])

    assert "data_profile" not in revision.model_dump_json()
    assert "data_profile" not in revision._fingerprint_payload()


def test_plan_revision_has_no_stopping_replan_or_lifecycle_policy_fields() -> None:
    prohibited = {
        "stopping_condition",
        "stopping_conditions",
        "replan_trigger",
        "replan_triggers",
        "replan_cause",
        "approval_state",
        "activation_state",
        "successor_plan_revision_id",
    }

    assert prohibited.isdisjoint(PlanRevision.model_fields)


def test_plan_revision_is_not_an_fco_or_semantic_graph_member() -> None:
    assert "PLAN_REVISION" not in FirstClassObjectType.__members__
    semantic_graph_members = {
        FirstClassObjectType.OBJECTIVE,
        FirstClassObjectType.HYPOTHESIS,
        FirstClassObjectType.EVIDENCE,
        FirstClassObjectType.DISCOVERY,
    }
    assert all(member.value != "plan_revision" for member in semantic_graph_members)


def test_session_frame_contract_is_unchanged() -> None:
    assert set(SessionFrame.model_fields) == {
        "objective",
        "assumptions",
        "tasks",
        "evidences",
        "data_profile",
    }


def test_planner_does_not_author_or_receive_plan_revision() -> None:
    assert "plan_revision" not in PlanningContext.model_fields
    assert "plan_revision" not in PlannerOutput.model_fields
    assert "plan_revision" not in State.model_fields


def test_dependency_eligibility_overrides_lower_dependent_order_rank() -> None:
    prerequisite, dependent = _task(), _task()
    revision = _revision(
        [prerequisite, dependent],
        bindings=(
            _binding(prerequisite, order_rank=10),
            _binding(dependent, order_rank=0),
        ),
        dependencies=(_edge(prerequisite, dependent),),
    )

    assert revision.eligible_task_ids() == (prerequisite.task_id,)
    assert revision.eligible_task_ids(completed_task_ids={prerequisite.task_id}) == (
        dependent.task_id,
    )


def test_plan_revision_is_immutable_and_requires_authoritative_construction() -> None:
    task = _task()
    revision = _revision([task])

    with pytest.raises(ValidationError, match="authoritative Tasks"):
        PlanRevision(
            objective_id=OBJECTIVE_ID,
            task_bindings=(_binding(task),),
        )
    with pytest.raises(ValidationError, match="frozen"):
        revision.dependencies = ()
