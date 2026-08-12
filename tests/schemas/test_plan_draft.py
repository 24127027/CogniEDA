from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognieda.execution import Capability
from cognieda.schemas import (
    Objective,
    PlanDraft,
    PlanDraftApproval,
    PlanDraftDecision,
    PlanDraftDependency,
    TaskDraft,
    TaskKind,
)


def _draft() -> PlanDraft:
    return PlanDraft(
        objective=Objective(text="Understand dataset size."),
        task_drafts=(
            TaskDraft(
                kind=TaskKind.DATA,
                instruction="Count rows.",
                required_capability=Capability.DATA_ANALYSIS,
                order_rank=0,
            ),
        ),
    )


def test_fingerprint_binds_exact_transient_snapshot() -> None:
    draft = _draft()
    reloaded = PlanDraft.model_validate(draft.model_dump(exclude={"fingerprint"}))
    changed = PlanDraft(
        plan_draft_id=draft.plan_draft_id,
        objective=draft.objective,
        task_drafts=(
            draft.task_drafts[0].model_copy(update={"instruction": "Count valid rows."}),
        ),
    )

    assert reloaded.fingerprint == draft.fingerprint
    assert changed.fingerprint != draft.fingerprint


def test_approval_identifies_exact_draft_and_decision() -> None:
    draft = _draft()

    approval = PlanDraftApproval(
        plan_draft_id=draft.plan_draft_id,
        plan_draft_fingerprint=draft.fingerprint,
        decision=PlanDraftDecision.APPROVE,
    )

    assert approval.plan_draft_id == draft.plan_draft_id
    assert approval.plan_draft_fingerprint == draft.fingerprint


def test_dependency_references_must_be_unambiguous_members() -> None:
    member = _draft().task_drafts[0]

    with pytest.raises(ValidationError, match="member TaskDrafts"):
        PlanDraft(
            objective=Objective(text="Understand dataset size."),
            task_drafts=(member,),
            dependencies=(
                PlanDraftDependency(
                    prerequisite_task_draft_id=member.task_draft_id,
                    dependent_task_draft_id=uuid4(),
                ),
            ),
        )
