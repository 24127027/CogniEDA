"""Atomic Application admission and activation for exact Human-approved Plans."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel
from sqlmodel import Session

from cognieda.application.services.plan_validation import PlanValidator
from cognieda.infrastructure.persistence.models import (
    ActivePlanRecord,
    ObjectiveRecord,
    TaskRecord,
)
from cognieda.infrastructure.persistence.repositories import PlanRepository
from cognieda.infrastructure.persistence.repositories.common import (
    record_to_schema,
    schema_to_record_payload,
)
from cognieda.schemas.artifacts import Objective, Task
from cognieda.schemas.plan import Plan


class PlanAdmissionService:
    """Persist one exact approved bundle and select it executable atomically."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def admit(self, plan: Plan, tasks: Iterable[Task]) -> Plan:
        member_tasks = tuple(tasks)
        plan.validate_tasks(member_tasks)
        try:
            self._stage_exact(
                ObjectiveRecord,
                plan.objective.objective_id,
                plan.objective,
                Objective,
            )
            for task in member_tasks:
                self._stage_exact(TaskRecord, task.task_id, task, Task)
            self._session.flush()

            canonical = PlanValidator(self._session).validate(plan, tasks=member_tasks)
            PlanRepository(self._session).add(canonical)
            self._session.flush()

            active = self._session.get(
                ActivePlanRecord,
                canonical.objective.objective_id,
            )
            if active is None:
                active = ActivePlanRecord(
                    objective_id=canonical.objective.objective_id,
                    plan_id=canonical.plan_id,
                )
            else:
                active.plan_id = canonical.plan_id
            self._session.add(active)
            self._session.commit()
            return canonical
        except Exception:
            self._session.rollback()
            raise

    def _stage_exact(
        self,
        record_type: type[Any],
        identity: object,
        schema: BaseModel,
        schema_type: type[BaseModel],
    ) -> None:
        existing: Any = self._session.get(record_type, identity)
        if existing is None:
            self._session.add(record_type(**schema_to_record_payload(schema)))
            return
        if record_to_schema(schema_type, existing) != schema:
            raise ValueError(
                f"Approved {schema_type.__name__} identity conflicts with persisted content."
            )


__all__ = ("PlanAdmissionService",)
