"""Human-authorized atomic admission and activation of exact Plan bundles."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator
from sqlmodel import Session

from cognieda.application.services.plan_validation import PlanValidator
from cognieda.infrastructure.persistence.models import (
    AssumptionRecord,
    ObjectiveRecord,
    PlanRecord,
    TaskRecord,
)
from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRepository,
    PlanRepository,
)
from cognieda.infrastructure.persistence.repositories.common import (
    record_to_schema,
    schema_to_record_payload,
)
from cognieda.schemas.artifacts import Assumption, Objective, Task
from cognieda.schemas.plan import Plan


class PlanReviewAction(StrEnum):
    """Finite Human authority over one exact transient Plan candidate."""

    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"


class PlanReviewDecision(BaseModel):
    """Human review value bound to one exact candidate Plan identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: PlanReviewAction
    plan_id: UUID
    feedback: str | None = None

    @model_validator(mode="after")
    def _require_feedback_for_nonapproval(self) -> PlanReviewDecision:
        if self.action in {PlanReviewAction.REJECT, PlanReviewAction.REVISE} and (
            self.feedback is None or not self.feedback.strip()
        ):
            raise ValueError(f"{self.action.value} requires exact Human feedback.")
        return self


class PlanAdmissionService:
    """Apply one typed Human review decision at the application authority boundary."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def admit(
        self,
        decision: PlanReviewDecision,
        *,
        plan: Plan,
        tasks: tuple[Task, ...],
    ) -> PlanReviewDecision:
        """Admit an approved exact bundle, or preserve a non-authoritative rejection."""

        if decision.plan_id != plan.plan_id:
            raise ValueError("Plan review decision does not identify the exact candidate Plan.")
        if decision.action is not PlanReviewAction.APPROVE:
            return decision

        try:
            new_objective, new_tasks = self._validate_authoritative_bundle(plan, tasks)
            if new_objective:
                self._session.add(
                    ObjectiveRecord(**schema_to_record_payload(plan.objective))
                )
            self._session.add_all(
                TaskRecord(**schema_to_record_payload(task)) for task in new_tasks
            )
            self._session.flush()

            canonical = PlanValidator(self._session).validate(plan, tasks=tasks)
            PlanRepository(self._session).add(canonical)
            self._session.flush()
            ActivePlanRepository(self._session).activate(canonical)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return decision

    def _validate_authoritative_bundle(
        self,
        plan: Plan,
        tasks: tuple[Task, ...],
    ) -> tuple[bool, tuple[Task, ...]]:
        plan.validate_tasks(tasks)

        if self._session.get(PlanRecord, plan.plan_id) is not None:
            raise ValueError("Plan identity already exists; approval cannot overwrite it.")

        for assumption in plan.assumptions:
            row = self._session.get(AssumptionRecord, assumption.assumption_id)
            if row is None:
                raise ValueError("Plan approval requires every Assumption to be admitted.")
            if record_to_schema(Assumption, row) != assumption:
                raise ValueError(
                    "Plan approval rejects changed content for an admitted Assumption."
                )

        objective_row = self._session.get(
            ObjectiveRecord,
            plan.objective.objective_id,
        )
        new_objective = objective_row is None
        if objective_row is not None and (
            record_to_schema(Objective, objective_row) != plan.objective
        ):
            raise ValueError("Plan approval rejects an Objective identity collision.")

        new_tasks: list[Task] = []
        for task in tasks:
            task_row = self._session.get(TaskRecord, task.task_id)
            if task_row is None:
                new_tasks.append(task)
                continue
            persisted = record_to_schema(Task, task_row)
            if self._task_semantics(persisted) != self._task_semantics(task):
                raise ValueError("Plan approval rejects a Task identity collision.")
        return new_objective, tuple(new_tasks)

    @staticmethod
    def _task_semantics(task: Task) -> tuple[object, ...]:
        return (
            task.task_id,
            task.objective_id,
            task.kind,
            task.instruction,
        )


__all__ = (
    "PlanAdmissionService",
    "PlanReviewAction",
    "PlanReviewDecision",
)
