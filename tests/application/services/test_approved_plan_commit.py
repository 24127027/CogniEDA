from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session, select

from cognieda.application.services import (
    ApprovedPlanCommitError,
    ApprovedPlanCommitErrorCode,
    commit_approved_plan,
)
from cognieda.execution import Capability
from cognieda.infrastructure.persistence.models import (
    ActivePlanRevisionRecord,
    ObjectiveRecord,
    PlanRevisionRecord,
    TaskRecord,
)
from cognieda.infrastructure.persistence.repositories import PlanRevisionRepository
from cognieda.schemas import (
    Objective,
    PlanDraft,
    PlanDraftApproval,
    PlanDraftDecision,
    PlanDraftDependency,
    PlanPriority,
    TaskDraft,
    TaskKind,
    TaskStatus,
)


def _draft(*, objective: Objective | None = None, task_count: int = 1) -> PlanDraft:
    objective = objective or Objective(text="Understand dataset size.")
    task_drafts = tuple(
        TaskDraft(
            kind=TaskKind.DATA,
            instruction=f"Bounded data work {index}.",
            required_capability=Capability.DATA_ANALYSIS,
            order_rank=index,
            priority=PlanPriority.HIGH if index == 0 else PlanPriority.NORMAL,
        )
        for index in range(task_count)
    )
    dependencies = (
        (
            PlanDraftDependency(
                prerequisite_task_draft_id=task_drafts[0].task_draft_id,
                dependent_task_draft_id=task_drafts[1].task_draft_id,
            ),
        )
        if task_count == 2
        else ()
    )
    return PlanDraft(
        objective=objective,
        task_drafts=task_drafts,
        dependencies=dependencies,
    )


def _approval(
    draft: PlanDraft,
    *,
    decision: PlanDraftDecision = PlanDraftDecision.APPROVE,
) -> PlanDraftApproval:
    return PlanDraftApproval(
        plan_draft_id=draft.plan_draft_id,
        plan_draft_fingerprint=draft.fingerprint,
        decision=decision,
    )


def _counts(session: Session) -> tuple[int, int, int, int]:
    return (
        len(session.exec(select(ObjectiveRecord)).all()),
        len(session.exec(select(TaskRecord)).all()),
        len(session.exec(select(PlanRevisionRecord)).all()),
        len(session.exec(select(ActivePlanRevisionRecord)).all()),
    )


def test_approved_draft_atomically_admits_tasks_revision_and_active_selection(
    db_session: Session,
) -> None:
    draft = _draft(task_count=2)

    result = commit_approved_plan(
        db_session,
        plan_draft=draft,
        approval=_approval(draft),
    )

    assert result.objective == draft.objective
    assert [task.task_id for task in result.tasks] == [
        task_draft.task_draft_id for task_draft in draft.task_drafts
    ]
    assert all(task.status is TaskStatus.PENDING for task in result.tasks)
    assert result.plan_revision.objective_id == draft.objective.objective_id
    assert result.plan_revision.dependencies[0].prerequisite_task_id == result.tasks[0].task_id
    assert result.active_selection.plan_revision_id == result.plan_revision.plan_revision_id
    assert PlanRevisionRepository(db_session).get_by_id(
        result.plan_revision.plan_revision_id
    ) == result.plan_revision
    assert _counts(db_session) == (1, 2, 1, 1)


@pytest.mark.parametrize(
    ("approval", "expected_code"),
    [
        ("reject", ApprovedPlanCommitErrorCode.DRAFT_REJECTED),
        ("mismatch", ApprovedPlanCommitErrorCode.APPROVAL_MISMATCH),
    ],
)
def test_rejection_or_non_exact_approval_creates_no_authoritative_state(
    db_session: Session,
    approval: str,
    expected_code: ApprovedPlanCommitErrorCode,
) -> None:
    draft = _draft()
    decision = _approval(draft, decision=PlanDraftDecision.REJECT)
    if approval == "mismatch":
        decision = decision.model_copy(
            update={
                "decision": PlanDraftDecision.APPROVE,
                "plan_draft_id": uuid4(),
            }
        )

    with pytest.raises(ApprovedPlanCommitError) as exc_info:
        commit_approved_plan(db_session, plan_draft=draft, approval=decision)

    assert exc_info.value.code is expected_code
    assert _counts(db_session) == (0, 0, 0, 0)


def test_failed_commit_rolls_back_staged_objective_and_tasks(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = _draft()

    def fail_revision_add(self: PlanRevisionRepository, revision: object) -> None:
        del self, revision
        raise RuntimeError("injected revision persistence failure")

    monkeypatch.setattr(PlanRevisionRepository, "add", fail_revision_add)

    with pytest.raises(RuntimeError, match="injected revision persistence failure"):
        commit_approved_plan(
            db_session,
            plan_draft=draft,
            approval=_approval(draft),
        )

    assert _counts(db_session) == (0, 0, 0, 0)


def test_existing_active_revision_blocks_replanning_without_orphan_task(
    db_session: Session,
) -> None:
    first = _draft()
    commit_approved_plan(
        db_session,
        plan_draft=first,
        approval=_approval(first),
    )
    second = _draft(objective=first.objective)

    with pytest.raises(ApprovedPlanCommitError) as exc_info:
        commit_approved_plan(
            db_session,
            plan_draft=second,
            approval=_approval(second),
        )

    assert exc_info.value.code is ApprovedPlanCommitErrorCode.ACTIVE_PLAN_EXISTS
    assert _counts(db_session) == (1, 1, 1, 1)
