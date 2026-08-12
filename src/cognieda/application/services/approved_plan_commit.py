"""Atomic admission of one exact Human-approved transient PlanDraft."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlmodel import Session

from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRevisionRepository,
    ObjectiveRepository,
    PlanRevisionRepository,
    TaskRepository,
)
from cognieda.schemas.artifacts import Objective, Task
from cognieda.schemas.enums import TaskStatus
from cognieda.schemas.plan_draft import PlanDraft, PlanDraftApproval, PlanDraftDecision
from cognieda.schemas.plan_revision import (
    ActivePlanRevisionSelection,
    PlanDependency,
    PlanRevision,
    PlanTaskBinding,
)

from .plan_revision_validation import PlanRevisionValidator


class ApprovedPlanCommitErrorCode(StrEnum):
    """Finite rejection categories for the authoritative plan transition."""

    APPROVAL_MISMATCH = "approval_mismatch"
    DRAFT_REJECTED = "draft_rejected"
    OBJECTIVE_CONFLICT = "objective_conflict"
    ACTIVE_PLAN_EXISTS = "active_plan_exists"


class ApprovedPlanCommitError(ValueError):
    def __init__(self, code: ApprovedPlanCommitErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ApprovedPlanCommitResult:
    """Exact authoritative objects admitted by one successful transaction."""

    objective: Objective
    tasks: tuple[Task, ...]
    plan_revision: PlanRevision
    active_selection: ActivePlanRevisionSelection


def commit_approved_plan(
    session: Session,
    *,
    plan_draft: PlanDraft,
    approval: PlanDraftApproval,
) -> ApprovedPlanCommitResult:
    """Atomically admit Objective, Tasks, immutable revision, and active selection."""

    if (
        approval.plan_draft_id != plan_draft.plan_draft_id
        or approval.plan_draft_fingerprint != plan_draft.fingerprint
    ):
        raise ApprovedPlanCommitError(
            ApprovedPlanCommitErrorCode.APPROVAL_MISMATCH,
            "Human approval does not identify the exact current PlanDraft.",
        )
    if approval.decision is not PlanDraftDecision.APPROVE:
        raise ApprovedPlanCommitError(
            ApprovedPlanCommitErrorCode.DRAFT_REJECTED,
            "A rejected PlanDraft cannot enter authoritative state.",
        )

    objectives = ObjectiveRepository(session)
    tasks = TaskRepository(session)
    revisions = PlanRevisionRepository(session)
    active_revisions = ActivePlanRevisionRepository(session)
    objective = plan_draft.objective

    try:
        existing_objective = objectives.get_by_id(objective.objective_id)
        if existing_objective is None:
            objectives.add(objective)
        elif existing_objective != objective:
            raise ApprovedPlanCommitError(
                ApprovedPlanCommitErrorCode.OBJECTIVE_CONFLICT,
                "PlanDraft Objective identity conflicts with authoritative content.",
            )

        if active_revisions.get_by_objective_id(objective.objective_id) is not None:
            raise ApprovedPlanCommitError(
                ApprovedPlanCommitErrorCode.ACTIVE_PLAN_EXISTS,
                "Replanning an Objective with an active PlanRevision is deferred.",
            )

        authoritative_tasks = tuple(
            Task(
                task_id=task_draft.task_draft_id,
                objective_id=objective.objective_id,
                kind=task_draft.kind,
                instruction=task_draft.instruction,
                status=TaskStatus.PENDING,
            )
            for task_draft in plan_draft.task_drafts
        )
        for task in authoritative_tasks:
            tasks.add(task)

        revision = PlanRevision.create(
            objective_id=objective.objective_id,
            task_bindings=(
                PlanTaskBinding(
                    task_id=task_draft.task_draft_id,
                    required_capability=task_draft.required_capability,
                    order_rank=task_draft.order_rank,
                    priority=task_draft.priority,
                )
                for task_draft in plan_draft.task_drafts
            ),
            dependencies=(
                PlanDependency(
                    prerequisite_task_id=dependency.prerequisite_task_draft_id,
                    dependent_task_id=dependency.dependent_task_draft_id,
                )
                for dependency in plan_draft.dependencies
            ),
            authoritative_tasks=authoritative_tasks,
        )

        session.flush()
        revision = PlanRevisionValidator(session).validate(revision)
        revisions.add(revision)
        active_selection = ActivePlanRevisionSelection(
            objective_id=objective.objective_id,
            plan_revision_id=revision.plan_revision_id,
        )
        active_revisions.add(active_selection)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return ApprovedPlanCommitResult(
        objective=objective,
        tasks=authoritative_tasks,
        plan_revision=revision,
        active_selection=active_selection,
    )


__all__ = (
    "ApprovedPlanCommitError",
    "ApprovedPlanCommitErrorCode",
    "ApprovedPlanCommitResult",
    "commit_approved_plan",
)
