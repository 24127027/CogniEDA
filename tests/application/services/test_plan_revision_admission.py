"""Application-authority admission for durable PlanRevision proposals."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session

from cognieda.agents.planner.context import PlanningContext
from cognieda.agents.planner.types import PlannerOutput, State
from cognieda.application.services import (
    PlanRevisionAdmissionError,
    PlanRevisionAdmissionErrorCode,
    PlanRevisionAdmissionService,
)
from cognieda.execution import Capability
from cognieda.infrastructure.persistence.models import PlanRevisionRecord
from cognieda.infrastructure.persistence.repositories import (
    ObjectiveRepository,
    PlanRevisionRepository,
    TaskRepository,
)
from cognieda.schemas import (
    FirstClassObjectType,
    Objective,
    PlanDependency,
    PlanPriority,
    PlanRevision,
    PlanTaskBinding,
    SessionFrame,
    Task,
    TaskKind,
)


def _persisted_objective(session: Session, text: str = "Admit a plan") -> Objective:
    return ObjectiveRepository(session).create(Objective(text=text))


def _task(
    objective_id: UUID,
    *,
    task_id: UUID | None = None,
    kind: TaskKind = TaskKind.DATA,
    persisted_in: Session | None = None,
) -> Task:
    task = Task(
        task_id=task_id or uuid4(),
        objective_id=objective_id,
        kind=kind,
        instruction=f"Perform {kind.value} work.",
    )
    return TaskRepository(persisted_in).create(task) if persisted_in is not None else task


def _binding(
    task: Task,
    *,
    capability: Capability | None | object = ...,
    order_rank: int = 0,
    priority: PlanPriority = PlanPriority.NORMAL,
) -> PlanTaskBinding:
    default_capability = {
        TaskKind.DATA: Capability.DATA_ANALYSIS,
        TaskKind.SCIENTIFIC: Capability.HYPOTHESIS_TESTING,
        TaskKind.GRAPH: Capability.GRAPH_MINING,
    }[task.kind]
    selected = default_capability if capability is ... else capability
    assert isinstance(selected, Capability) or selected is None
    return PlanTaskBinding(
        task_id=task.task_id,
        required_capability=selected,
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
        authoritative_tasks=task_tuple,
    )


def _edge(prerequisite: Task, dependent: Task) -> PlanDependency:
    return PlanDependency(
        prerequisite_task_id=prerequisite.task_id,
        dependent_task_id=dependent.task_id,
    )


def _assert_rejected(
    service: PlanRevisionAdmissionService,
    candidate: PlanRevision,
    code: PlanRevisionAdmissionErrorCode,
) -> None:
    with pytest.raises(PlanRevisionAdmissionError) as exc_info:
        service.admit_proposal(candidate)
    assert exc_info.value.code is code


def test_valid_proposal_is_admitted_and_reloads_exactly(db_session: Session) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id, persisted_in=db_session)
    candidate = _revision(objective.objective_id, [task])

    result = PlanRevisionAdmissionService(db_session).admit_proposal(candidate)

    assert result.created is True
    assert result.plan_revision == candidate
    assert result.plan_revision.fingerprint == candidate.fingerprint
    assert PlanRevisionRepository(db_session).get_by_id(candidate.plan_revision_id) == candidate


def test_missing_objective_is_rejected(db_session: Session) -> None:
    objective_id = uuid4()
    task = _task(objective_id)
    candidate = _revision(objective_id, [task])

    _assert_rejected(
        PlanRevisionAdmissionService(db_session),
        candidate,
        PlanRevisionAdmissionErrorCode.OBJECTIVE_NOT_FOUND,
    )


def test_missing_task_is_rejected(db_session: Session) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id)
    candidate = _revision(objective.objective_id, [task])

    _assert_rejected(
        PlanRevisionAdmissionService(db_session),
        candidate,
        PlanRevisionAdmissionErrorCode.TASK_NOT_FOUND,
    )


def test_wrong_objective_authoritative_task_is_rejected(db_session: Session) -> None:
    proposal_objective = _persisted_objective(db_session, "Proposal objective")
    task_objective = _persisted_objective(db_session, "Task objective")
    task_id = uuid4()
    _task(task_objective.objective_id, task_id=task_id, persisted_in=db_session)
    caller_task = _task(proposal_objective.objective_id, task_id=task_id)
    candidate = _revision(proposal_objective.objective_id, [caller_task])

    _assert_rejected(
        PlanRevisionAdmissionService(db_session),
        candidate,
        PlanRevisionAdmissionErrorCode.TASK_OBJECTIVE_MISMATCH,
    )


@pytest.mark.parametrize(
    ("kind", "capability"),
    [
        (TaskKind.DATA, Capability.HYPOTHESIS_TESTING),
        (TaskKind.SCIENTIFIC, Capability.DATA_ANALYSIS),
        (TaskKind.GRAPH, Capability.DATA_PROFILING),
    ],
)
def test_invalid_task_kind_capability_is_rejected(
    db_session: Session,
    kind: TaskKind,
    capability: Capability,
) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id, kind=kind, persisted_in=db_session)
    invalid_binding = _binding(task, capability=capability)
    candidate = PlanRevision.model_construct(
        plan_revision_id=uuid4(),
        objective_id=objective.objective_id,
        task_bindings=(invalid_binding,),
        dependencies=(),
        contract_version="plan-revision/v1",
    )

    _assert_rejected(
        PlanRevisionAdmissionService(db_session),
        candidate,
        PlanRevisionAdmissionErrorCode.INVALID_PROPOSAL,
    )


def test_duplicate_binding_is_rejected(db_session: Session) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id, persisted_in=db_session)
    binding = _binding(task)
    candidate = PlanRevision.model_construct(
        plan_revision_id=uuid4(),
        objective_id=objective.objective_id,
        task_bindings=(binding, binding),
        dependencies=(),
        contract_version="plan-revision/v1",
    )

    _assert_rejected(
        PlanRevisionAdmissionService(db_session),
        candidate,
        PlanRevisionAdmissionErrorCode.INVALID_PROPOSAL,
    )


@pytest.mark.parametrize("case", ["outside", "self", "duplicate", "direct", "indirect"])
def test_invalid_dependency_graph_is_rejected(db_session: Session, case: str) -> None:
    objective = _persisted_objective(db_session)
    tasks = tuple(
        _task(objective.objective_id, persisted_in=db_session) for _ in range(3)
    )
    first, second, third = tasks
    if case == "outside":
        dependencies = (_edge(first, _task(objective.objective_id)),)
    elif case == "self":
        dependencies = (
            PlanDependency.model_construct(
                prerequisite_task_id=first.task_id,
                dependent_task_id=first.task_id,
            ),
        )
    elif case == "duplicate":
        edge = _edge(first, second)
        dependencies = (edge, edge)
    elif case == "direct":
        dependencies = (_edge(first, second), _edge(second, first))
    else:
        dependencies = (
            _edge(first, second),
            _edge(second, third),
            _edge(third, first),
        )
    candidate = PlanRevision.model_construct(
        plan_revision_id=uuid4(),
        objective_id=objective.objective_id,
        task_bindings=tuple(_binding(task) for task in tasks),
        dependencies=dependencies,
        contract_version="plan-revision/v1",
    )

    _assert_rejected(
        PlanRevisionAdmissionService(db_session),
        candidate,
        PlanRevisionAdmissionErrorCode.INVALID_PROPOSAL,
    )


def test_unsupported_contract_version_is_rejected(db_session: Session) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id, persisted_in=db_session)
    valid = _revision(objective.objective_id, [task])
    candidate = PlanRevision.model_construct(
        **valid.model_dump(exclude={"fingerprint", "contract_version"}),
        contract_version="plan-revision/v2",
    )

    _assert_rejected(
        PlanRevisionAdmissionService(db_session),
        candidate,
        PlanRevisionAdmissionErrorCode.UNSUPPORTED_CONTRACT_VERSION,
    )


def test_invalid_revision_identity_is_rejected(db_session: Session) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id, persisted_in=db_session)
    valid = _revision(objective.objective_id, [task])
    candidate = PlanRevision.model_construct(
        **valid.model_dump(exclude={"fingerprint", "plan_revision_id"}),
        plan_revision_id="not-a-uuid",
    )

    _assert_rejected(
        PlanRevisionAdmissionService(db_session),
        candidate,
        PlanRevisionAdmissionErrorCode.INVALID_IDENTITY,
    )


@pytest.mark.parametrize(
    "invalid_binding",
    [
        PlanTaskBinding.model_construct(
            task_id=UUID("00000000-0000-0000-0000-000000000001"),
            required_capability=Capability.DATA_ANALYSIS,
            order_rank=-1,
            priority=PlanPriority.NORMAL,
        ),
        PlanTaskBinding.model_construct(
            task_id=UUID("00000000-0000-0000-0000-000000000001"),
            required_capability=Capability.DATA_ANALYSIS,
            order_rank=0,
            priority="urgent",
        ),
    ],
)
def test_invalid_rank_or_priority_is_rejected(
    db_session: Session,
    invalid_binding: PlanTaskBinding,
) -> None:
    objective = _persisted_objective(db_session)
    task = _task(
        objective.objective_id,
        task_id=invalid_binding.task_id,
        persisted_in=db_session,
    )
    candidate = PlanRevision.model_construct(
        plan_revision_id=uuid4(),
        objective_id=objective.objective_id,
        task_bindings=(invalid_binding,),
        dependencies=(),
        contract_version="plan-revision/v1",
    )

    _assert_rejected(
        PlanRevisionAdmissionService(db_session),
        candidate,
        PlanRevisionAdmissionErrorCode.INVALID_PROPOSAL,
    )
    assert task.task_id == invalid_binding.task_id


def test_exact_replay_is_idempotent(db_session: Session) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id, persisted_in=db_session)
    candidate = _revision(objective.objective_id, [task])
    service = PlanRevisionAdmissionService(db_session)

    first = service.admit_proposal(candidate)
    replay = service.admit_proposal(candidate)

    assert first.created is True
    assert replay.created is False
    assert replay.plan_revision == candidate


def test_same_identity_different_content_is_rejected(db_session: Session) -> None:
    objective = _persisted_objective(db_session)
    first = _task(objective.objective_id, persisted_in=db_session)
    second = _task(objective.objective_id, persisted_in=db_session)
    revision_id = uuid4()
    original = _revision(objective.objective_id, [first], plan_revision_id=revision_id)
    conflicting = _revision(objective.objective_id, [second], plan_revision_id=revision_id)
    service = PlanRevisionAdmissionService(db_session)
    service.admit_proposal(original)

    _assert_rejected(
        service,
        conflicting,
        PlanRevisionAdmissionErrorCode.IDENTITY_COLLISION,
    )
    assert PlanRevisionRepository(db_session).get_by_id(revision_id) == original


def test_different_identities_with_same_fingerprint_are_both_admitted(
    db_session: Session,
) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id, persisted_in=db_session)
    first = _revision(objective.objective_id, [task])
    second = _revision(objective.objective_id, [task])
    service = PlanRevisionAdmissionService(db_session)
    assert first.fingerprint == second.fingerprint

    first_result = service.admit_proposal(first)
    second_result = service.admit_proposal(second)

    assert first_result.created is True
    assert second_result.created is True
    assert (
        first_result.plan_revision.plan_revision_id
        != second_result.plan_revision.plan_revision_id
    )


def test_corrupt_stored_fingerprint_fails_closed(db_session: Session) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id, persisted_in=db_session)
    candidate = _revision(objective.objective_id, [task])
    service = PlanRevisionAdmissionService(db_session)
    service.admit_proposal(candidate)
    record = db_session.get(PlanRevisionRecord, candidate.plan_revision_id)
    assert record is not None
    record.fingerprint = "sha256:" + "0" * 64
    db_session.add(record)
    db_session.commit()

    _assert_rejected(
        service,
        candidate,
        PlanRevisionAdmissionErrorCode.FINGERPRINT_MISMATCH,
    )


def test_unavailable_provider_does_not_block_or_rewrite_admission(
    db_session: Session,
) -> None:
    objective = _persisted_objective(db_session)
    task = _task(
        objective.objective_id,
        kind=TaskKind.GRAPH,
        persisted_in=db_session,
    )
    candidate = _revision(objective.objective_id, [task])

    admitted = PlanRevisionAdmissionService(db_session).admit_proposal(candidate)

    assert admitted.created is True
    assert admitted.plan_revision.task_bindings[0].required_capability is Capability.GRAPH_MINING


def test_admission_adds_no_approval_activation_execution_or_planner_surface() -> None:
    prohibited = {
        "approval_state",
        "activation_state",
        "active_plan_revision_id",
        "execution_state",
    }
    assert prohibited.isdisjoint(PlanRevision.model_fields)
    assert "plan_revision" not in PlanningContext.model_fields
    assert "plan_revision" not in PlannerOutput.model_fields
    assert "plan_revision" not in State.model_fields
    assert "plan_revision" not in SessionFrame.model_fields
    assert "PLAN_REVISION" not in FirstClassObjectType.__members__
