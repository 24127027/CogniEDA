"""Atomic admission of exact Human-approved transient canonical plan objects."""

from __future__ import annotations

from sqlmodel import Session

from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRevisionRepository,
    ObjectiveRepository,
    PlanRevisionRepository,
    TaskRepository,
)
from cognieda.schemas.artifacts import Objective, Task
from cognieda.schemas.enums import TaskStatus
from cognieda.schemas.plan_revision import ActivePlanRevisionSelection, PlanRevision

from .plan_revision_validation import PlanRevisionValidator


class ApprovedPlanCommitError(ValueError):
    """Reject an invalid authoritative plan transition."""


def commit_approved_plan(
    session: Session,
    *,
    objective: Objective,
    tasks: tuple[Task, ...],
    plan_revision: PlanRevision,
) -> None:
    """Atomically persist and activate the exact approved canonical objects."""

    task_ids = {task.task_id for task in tasks}
    if not tasks or len(task_ids) != len(tasks):
        raise ApprovedPlanCommitError("Approved plan requires unique canonical Tasks.")
    if plan_revision.objective_id != objective.objective_id:
        raise ApprovedPlanCommitError("Approved PlanRevision must belong to its Objective.")
    if plan_revision.task_ids != task_ids:
        raise ApprovedPlanCommitError("Approved PlanRevision membership must match exact Tasks.")
    if any(
        task.objective_id != objective.objective_id or task.status is not TaskStatus.PENDING
        for task in tasks
    ):
        raise ApprovedPlanCommitError(
            "Approved Tasks must be pending and belong to the exact Objective."
        )

    objectives = ObjectiveRepository(session)
    task_repository = TaskRepository(session)
    revisions = PlanRevisionRepository(session)
    active_revisions = ActivePlanRevisionRepository(session)

    try:
        existing_objective = objectives.get_by_id(objective.objective_id)
        if existing_objective is None:
            objectives.add(objective)
        elif existing_objective != objective:
            raise ApprovedPlanCommitError(
                "Transient Objective identity conflicts with authoritative content."
            )

        if active_revisions.get_by_objective_id(objective.objective_id) is not None:
            raise ApprovedPlanCommitError(
                "Replanning an Objective with an active PlanRevision is deferred."
            )

        for task in tasks:
            if task_repository.get_by_id(task.task_id) is not None:
                raise ApprovedPlanCommitError(
                    "Transient Task identity conflicts with authoritative state."
                )
            task_repository.add(task)

        session.flush()
        validated_revision = PlanRevisionValidator(session).validate(plan_revision)
        revisions.add(validated_revision)
        active_revisions.add(
            ActivePlanRevisionSelection(
                objective_id=objective.objective_id,
                plan_revision_id=validated_revision.plan_revision_id,
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise


__all__ = (
    "ApprovedPlanCommitError",
    "commit_approved_plan",
)
