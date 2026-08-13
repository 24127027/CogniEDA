"""Side-effect-free application validation for PlanRevision candidates."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal, cast
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session

from cognieda.application.services import (
    PlanRevisionValidationError,
    PlanRevisionValidationErrorCode,
    PlanRevisionValidator,
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


def _persisted_objective(session: Session, text: str = "Validate a plan") -> Objective:
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


def _assert_rejected(
    validator: PlanRevisionValidator,
    candidate: PlanRevision,
    code: PlanRevisionValidationErrorCode,
) -> None:
    with pytest.raises(PlanRevisionValidationError) as exc_info:
        validator.validate(candidate)
    assert exc_info.value.code is code


def test_valid_candidate_is_returned_without_persistence(db_session: Session) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id, persisted_in=db_session)
    candidate = _revision(objective.objective_id, [task])

    validated = PlanRevisionValidator(db_session).validate(candidate)

    assert validated == candidate
    assert validated.fingerprint == candidate.fingerprint
    assert PlanRevisionRepository(db_session).get_by_id(candidate.plan_revision_id) is None
    assert not db_session.new
    assert not db_session.dirty
    assert not db_session.deleted


def test_missing_objective_is_rejected(db_session: Session) -> None:
    objective_id = uuid4()
    task = _task(objective_id)
    candidate = _revision(objective_id, [task])

    _assert_rejected(
        PlanRevisionValidator(db_session),
        candidate,
        PlanRevisionValidationErrorCode.OBJECTIVE_NOT_FOUND,
    )


def test_missing_task_is_rejected(db_session: Session) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id)
    candidate = _revision(objective.objective_id, [task])

    _assert_rejected(
        PlanRevisionValidator(db_session),
        candidate,
        PlanRevisionValidationErrorCode.TASK_NOT_FOUND,
    )


def test_wrong_objective_authoritative_task_is_rejected(db_session: Session) -> None:
    candidate_objective = _persisted_objective(db_session, "Candidate objective")
    task_objective = _persisted_objective(db_session, "Task objective")
    task_id = uuid4()
    _task(task_objective.objective_id, task_id=task_id, persisted_in=db_session)
    caller_task = _task(candidate_objective.objective_id, task_id=task_id)
    candidate = _revision(candidate_objective.objective_id, [caller_task])

    _assert_rejected(
        PlanRevisionValidator(db_session),
        candidate,
        PlanRevisionValidationErrorCode.TASK_OBJECTIVE_MISMATCH,
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
        PlanRevisionValidator(db_session),
        candidate,
        PlanRevisionValidationErrorCode.INVALID_CANDIDATE,
    )


@pytest.mark.parametrize("case", ["outside", "self", "duplicate", "direct", "indirect"])
def test_invalid_dependency_graph_is_rejected(db_session: Session, case: str) -> None:
    objective = _persisted_objective(db_session)
    tasks = tuple(_task(objective.objective_id, persisted_in=db_session) for _ in range(3))
    first, second, third = tasks
    dependencies: tuple[PlanDependency, ...]
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
        PlanRevisionValidator(db_session),
        candidate,
        PlanRevisionValidationErrorCode.INVALID_CANDIDATE,
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
        PlanRevisionValidator(db_session),
        candidate,
        PlanRevisionValidationErrorCode.UNSUPPORTED_CONTRACT_VERSION,
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
        PlanRevisionValidator(db_session),
        candidate,
        PlanRevisionValidationErrorCode.INVALID_IDENTITY,
    )


@pytest.mark.parametrize(
    "invalid_binding",
    [
        PlanTaskBinding.model_construct(
            task_id=UUID("00000000-0000-0000-0000-000000000001"),
            order_rank=-1,
            priority=PlanPriority.NORMAL,
        ),
        PlanTaskBinding.model_construct(
            task_id=UUID("00000000-0000-0000-0000-000000000001"),
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
        PlanRevisionValidator(db_session),
        candidate,
        PlanRevisionValidationErrorCode.INVALID_CANDIDATE,
    )
    assert task.task_id == invalid_binding.task_id


def test_noncanonical_candidate_representation_is_rejected(
    db_session: Session,
) -> None:
    objective = _persisted_objective(db_session)
    first = _task(objective.objective_id, persisted_in=db_session)
    second = _task(objective.objective_id, persisted_in=db_session)
    canonical = _revision(
        objective.objective_id,
        [first, second],
        bindings=(
            _binding(first, order_rank=0),
            _binding(second, order_rank=1),
        ),
    )
    candidate = PlanRevision.model_construct(
        plan_revision_id=canonical.plan_revision_id,
        objective_id=canonical.objective_id,
        task_bindings=tuple(reversed(canonical.task_bindings)),
        dependencies=canonical.dependencies,
        contract_version=canonical.contract_version,
    )

    _assert_rejected(
        PlanRevisionValidator(db_session),
        candidate,
        PlanRevisionValidationErrorCode.INVALID_CANDIDATE,
    )


class _FingerprintMismatchCandidate:
    def __init__(self, revision: PlanRevision) -> None:
        self._revision = revision

    def __getattr__(self, name: str) -> object:
        return getattr(self._revision, name)

    @property
    def fingerprint(self) -> str:
        return "sha256:" + "0" * 64

    def model_dump(
        self,
        *,
        mode: Literal["json"],
        exclude: set[str],
    ) -> dict[str, Any]:
        return self._revision.model_dump(mode=mode, exclude=exclude)


def test_candidate_fingerprint_mismatch_is_rejected(db_session: Session) -> None:
    objective = _persisted_objective(db_session)
    task = _task(objective.objective_id, persisted_in=db_session)
    valid = _revision(objective.objective_id, [task])
    candidate = cast(
        PlanRevision,
        _FingerprintMismatchCandidate(valid),
    )

    _assert_rejected(
        PlanRevisionValidator(db_session),
        candidate,
        PlanRevisionValidationErrorCode.FINGERPRINT_MISMATCH,
    )


@pytest.mark.parametrize("kind", list(TaskKind))
def test_all_task_kinds_validate_without_provider_or_capability_lookup(
    db_session: Session,
    kind: TaskKind,
) -> None:
    objective = _persisted_objective(db_session)
    task = _task(
        objective.objective_id,
        kind=kind,
        persisted_in=db_session,
    )
    candidate = _revision(objective.objective_id, [task])

    validated = PlanRevisionValidator(db_session).validate(candidate)

    assert validated == candidate
    assert "capability" not in validated.model_dump_json()
    assert PlanRevisionRepository(db_session).get_by_id(candidate.plan_revision_id) is None
