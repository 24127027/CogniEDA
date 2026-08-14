"""Side-effect-free validation for exact canonical Plan candidates."""

from __future__ import annotations

from typing import Any, Literal, cast
from uuid import uuid4

import pytest
from sqlmodel import Session

from cognieda.application.services.plan_validation import (
    PlanValidationError,
    PlanValidationErrorCode,
    PlanValidator,
)
from cognieda.infrastructure.persistence.models import TaskRecord
from cognieda.infrastructure.persistence.repositories import (
    AssumptionRepository,
    ObjectiveRepository,
    PlanRepository,
    TaskRepository,
    TaskUpdate,
)
from cognieda.schemas import (
    Assumption,
    Objective,
    Plan,
    PlanTaskBinding,
    Task,
    TaskKind,
    TaskStatus,
)


def _persisted_bundle(session: Session) -> tuple[Objective, Assumption, Task]:
    objective = ObjectiveRepository(session).create(Objective(text="Understand retention."))
    assumption = AssumptionRepository(session).create(
        Assumption(text="Renewal dates are reliable.")
    )
    task = TaskRepository(session).create(
        Task(
            objective_id=objective.objective_id,
            kind=TaskKind.DATA,
            instruction="Profile retention data.",
        )
    )
    return objective, assumption, task


def _candidate(objective: Objective, assumption: Assumption, task: Task) -> Plan:
    return Plan.create(
        objective=objective,
        assumptions=(assumption,),
        task_bindings=(PlanTaskBinding(task_id=task.task_id, order_rank=0),),
        tasks=(task,),
    )


def _assert_code(
    validator: PlanValidator,
    candidate: Plan,
    code: PlanValidationErrorCode,
    *,
    tasks: tuple[Task, ...] | None = None,
) -> None:
    with pytest.raises(PlanValidationError) as exc_info:
        validator.validate(candidate, tasks=tasks)
    assert exc_info.value.code is code


def test_valid_candidate_is_canonical_and_not_persisted(db_session: Session) -> None:
    objective, assumption, task = _persisted_bundle(db_session)
    candidate = _candidate(objective, assumption, task)

    validated = PlanValidator(db_session).validate(candidate, tasks=(task,))

    assert validated == candidate
    assert PlanRepository(db_session).get_by_id(candidate.plan_id) is None


def test_missing_objective_fails_closed(db_session: Session) -> None:
    objective = Objective(text="Missing.")
    assumption = AssumptionRepository(db_session).create(Assumption(text="Admitted."))
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Inspect.",
    )
    candidate = _candidate(objective, assumption, task)

    _assert_code(PlanValidator(db_session), candidate, PlanValidationErrorCode.OBJECTIVE_NOT_FOUND)


def test_objective_content_mismatch_fails_closed(db_session: Session) -> None:
    objective, assumption, task = _persisted_bundle(db_session)
    candidate = _candidate(
        Objective(objective_id=objective.objective_id, text="Counterfeit content."),
        assumption,
        task,
    )

    _assert_code(
        PlanValidator(db_session),
        candidate,
        PlanValidationErrorCode.OBJECTIVE_CONTENT_MISMATCH,
    )


def test_missing_assumption_fails_closed(db_session: Session) -> None:
    objective, _, task = _persisted_bundle(db_session)
    candidate = _candidate(objective, Assumption(text="Missing."), task)

    _assert_code(PlanValidator(db_session), candidate, PlanValidationErrorCode.ASSUMPTION_NOT_FOUND)


def test_assumption_content_mismatch_fails_closed(db_session: Session) -> None:
    objective, assumption, task = _persisted_bundle(db_session)
    counterfeit = Assumption(
        assumption_id=assumption.assumption_id,
        text="Counterfeit content.",
    )
    candidate = _candidate(objective, counterfeit, task)

    _assert_code(
        PlanValidator(db_session),
        candidate,
        PlanValidationErrorCode.ASSUMPTION_CONTENT_MISMATCH,
    )


def test_missing_task_fails_closed(db_session: Session) -> None:
    objective, assumption, task = _persisted_bundle(db_session)
    missing = task.model_copy(update={"task_id": uuid4()})
    candidate = _candidate(objective, assumption, missing)

    _assert_code(PlanValidator(db_session), candidate, PlanValidationErrorCode.TASK_NOT_FOUND)


def test_persisted_task_objective_mismatch_fails_closed(db_session: Session) -> None:
    objective, assumption, task = _persisted_bundle(db_session)
    candidate = _candidate(objective, assumption, task)
    other_objective = ObjectiveRepository(db_session).create(Objective(text="Other scope."))
    row = db_session.get(TaskRecord, task.task_id)
    assert row is not None
    row.objective_id = other_objective.objective_id
    db_session.add(row)
    db_session.commit()

    _assert_code(
        PlanValidator(db_session),
        candidate,
        PlanValidationErrorCode.TASK_OBJECTIVE_MISMATCH,
    )


@pytest.mark.parametrize("case", ["missing", "extra", "duplicate", "wrong_objective"])
def test_supplied_task_bundle_is_exact(db_session: Session, case: str) -> None:
    objective, assumption, task = _persisted_bundle(db_session)
    candidate = _candidate(objective, assumption, task)
    extra = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Extra.",
    )
    if case == "missing":
        tasks = ()
    elif case == "extra":
        tasks = (task, extra)
    elif case == "duplicate":
        tasks = (task, task)
    else:
        tasks = (task.model_copy(update={"objective_id": uuid4()}),)

    _assert_code(
        PlanValidator(db_session),
        candidate,
        PlanValidationErrorCode.INVALID_CANDIDATE,
        tasks=tasks,
    )


def test_task_runtime_status_is_not_plan_content(db_session: Session) -> None:
    objective, assumption, pending = _persisted_bundle(db_session)
    candidate = _candidate(objective, assumption, pending)
    completed = TaskRepository(db_session).update(
        pending.task_id,
        update=TaskUpdate(status=TaskStatus.COMPLETED),
    )
    assert completed is not None

    assert PlanValidator(db_session).validate(candidate, tasks=(pending,)) == candidate


def test_unsupported_contract_and_invalid_identity_are_rejected(db_session: Session) -> None:
    objective, assumption, task = _persisted_bundle(db_session)
    valid = _candidate(objective, assumption, task)
    unsupported = Plan.model_construct(
        **valid.model_dump(exclude={"fingerprint", "contract_version"}),
        contract_version="plan/v2",
    )
    invalid_id = Plan.model_construct(
        **valid.model_dump(exclude={"fingerprint", "plan_id"}),
        plan_id="not-a-uuid",
    )

    _assert_code(
        PlanValidator(db_session),
        unsupported,
        PlanValidationErrorCode.UNSUPPORTED_CONTRACT_VERSION,
    )
    _assert_code(PlanValidator(db_session), invalid_id, PlanValidationErrorCode.INVALID_IDENTITY)


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


def test_fingerprint_mismatch_is_rejected(db_session: Session) -> None:
    objective, assumption, task = _persisted_bundle(db_session)
    candidate = cast(Plan, _FingerprintMismatchCandidate(_candidate(objective, assumption, task)))

    _assert_code(PlanValidator(db_session), candidate, PlanValidationErrorCode.FINGERPRINT_MISMATCH)


def test_validator_has_no_persistence_or_runtime_authority(db_session: Session) -> None:
    objective, assumption, task = _persisted_bundle(db_session)
    validator = PlanValidator(db_session)

    assert validator.validate(_candidate(objective, assumption, task))
    prohibited = {"add", "save", "persist", "commit", "dispatch", "activate", "approve"}
    assert prohibited.isdisjoint(vars(PlanValidator))
