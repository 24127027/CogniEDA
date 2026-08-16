"""Atomic admission and activation of an exact authorized Plan bundle."""

from __future__ import annotations

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


class PlanAdmissionService:
    """Admit one exact authorized bundle through application authority."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def admit(self, plan: Plan) -> Plan:
        """Validate, persist, and activate one exact authorized bundle atomically."""

        try:
            new_objective, new_tasks = self._validate_authoritative_bundle(plan)
            if new_objective:
                self._session.add(ObjectiveRecord(**schema_to_record_payload(plan.objective)))
            self._session.add_all(
                TaskRecord(**schema_to_record_payload(task)) for task in new_tasks
            )
            self._session.flush()

            canonical = PlanValidator(self._session).validate(plan)
            PlanRepository(self._session).add(canonical)
            self._session.flush()
            ActivePlanRepository(self._session).activate(canonical)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return canonical

    def _validate_authoritative_bundle(
        self,
        plan: Plan,
    ) -> tuple[bool, tuple[Task, ...]]:
        if self._session.get(PlanRecord, plan.plan_id) is not None:
            raise ValueError("Plan identity already exists; admission cannot overwrite it.")

        for assumption in plan.assumptions:
            row = self._session.get(AssumptionRecord, assumption.assumption_id)
            if row is None:
                raise ValueError("Plan admission requires every Assumption to be admitted.")
            if record_to_schema(Assumption, row) != assumption:
                raise ValueError(
                    "Plan admission rejects changed content for an admitted Assumption."
                )

        objective_row = self._session.get(
            ObjectiveRecord,
            plan.objective.objective_id,
        )
        new_objective = objective_row is None
        if objective_row is not None and (
            record_to_schema(Objective, objective_row) != plan.objective
        ):
            raise ValueError("Plan admission rejects an Objective identity collision.")

        new_tasks: list[Task] = []
        for task in plan.tasks:
            task_row = self._session.get(TaskRecord, task.task_id)
            if task_row is None:
                new_tasks.append(task)
                continue
            persisted = record_to_schema(Task, task_row)
            if persisted.semantic_payload() != task.semantic_payload():
                raise ValueError("Plan admission rejects a Task identity collision.")
        return new_objective, tuple(new_tasks)


__all__ = ("PlanAdmissionService",)
