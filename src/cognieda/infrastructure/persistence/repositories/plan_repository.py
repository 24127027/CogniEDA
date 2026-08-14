"""Exact append-only persistence for immutable Plan aggregates."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from cognieda.infrastructure.persistence.models import (
    AssumptionRecord,
    ObjectiveRecord,
    PlanAssumptionRecord,
    PlanDependencyRecord,
    PlanRecord,
    PlanTaskBindingRecord,
    TaskRecord,
)
from cognieda.infrastructure.persistence.repositories.common import record_to_schema
from cognieda.schemas.artifacts import Assumption, Objective, Task
from cognieda.schemas.plan import Plan


class PlanRepository:
    """Stage and reload complete immutable Plans without CRUD mutation."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, plan: Plan) -> None:
        """Stage one complete Plan in the caller-owned transaction."""

        self._session.add(
            PlanRecord(
                plan_id=plan.plan_id,
                objective_id=plan.objective.objective_id,
                contract_version=plan.contract_version,
                fingerprint=plan.fingerprint,
            )
        )
        self._session.flush()
        self._session.add_all(
            [
                PlanAssumptionRecord(
                    plan_id=plan.plan_id,
                    assumption_id=assumption.assumption_id,
                )
                for assumption in plan.assumptions
            ]
        )
        self._session.add_all(
            [
                PlanTaskBindingRecord(
                    plan_id=plan.plan_id,
                    task_id=binding.task_id,
                    order_rank=binding.order_rank,
                    priority=binding.priority,
                )
                for binding in plan.task_bindings
            ]
        )
        self._session.flush()
        self._session.add_all(
            [
                PlanDependencyRecord(
                    plan_id=plan.plan_id,
                    prerequisite_task_id=dependency.prerequisite_task_id,
                    dependent_task_id=dependency.dependent_task_id,
                )
                for dependency in plan.dependencies
            ]
        )

    def get_by_id(self, plan_id: UUID) -> Plan | None:
        header = self._session.get(PlanRecord, plan_id)
        if header is None:
            return None

        objective_row = self._session.get(ObjectiveRecord, header.objective_id)
        if objective_row is None:
            raise ValueError("Persisted Plan references a missing Objective.")
        assumption_rows = self._session.exec(
            select(PlanAssumptionRecord).where(PlanAssumptionRecord.plan_id == plan_id)
        ).all()
        binding_rows = self._session.exec(
            select(PlanTaskBindingRecord).where(PlanTaskBindingRecord.plan_id == plan_id)
        ).all()
        dependency_rows = self._session.exec(
            select(PlanDependencyRecord).where(PlanDependencyRecord.plan_id == plan_id)
        ).all()

        assumptions: list[Assumption] = []
        for link in assumption_rows:
            assumption_record = self._session.get(AssumptionRecord, link.assumption_id)
            if assumption_record is None:
                raise ValueError("Persisted Plan references a missing Assumption.")
            assumptions.append(record_to_schema(Assumption, assumption_record))

        tasks: list[Task] = []
        for binding in binding_rows:
            task_record = self._session.get(TaskRecord, binding.task_id)
            if task_record is None:
                raise ValueError("Persisted Plan references a missing Task.")
            tasks.append(record_to_schema(Task, task_record))

        plan = Plan.model_validate(
            {
                "plan_id": header.plan_id,
                "objective": record_to_schema(Objective, objective_row),
                "assumptions": tuple(assumptions),
                "contract_version": header.contract_version,
                "task_bindings": [
                    {
                        "task_id": binding.task_id,
                        "order_rank": binding.order_rank,
                        "priority": binding.priority,
                    }
                    for binding in binding_rows
                ],
                "dependencies": [
                    {
                        "prerequisite_task_id": dependency.prerequisite_task_id,
                        "dependent_task_id": dependency.dependent_task_id,
                    }
                    for dependency in dependency_rows
                ],
            },
        )
        plan.validate_tasks(tuple(tasks))
        if plan.fingerprint != header.fingerprint:
            raise ValueError("Persisted Plan fingerprint does not match exact content.")
        return plan


__all__ = ("PlanRepository",)
