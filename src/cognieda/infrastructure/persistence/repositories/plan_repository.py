"""Append-only persistence for exact immutable Plan snapshots."""

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
    """Stage and reconstruct Plans without update or delete authority."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, plan: Plan) -> None:
        """Stage one complete snapshot in the caller-owned transaction."""

        if self._session.get(PlanRecord, plan.plan_id) is not None:
            raise ValueError("Plan identity already exists; Plans are append-only.")

        objective_row = self._session.get(ObjectiveRecord, plan.objective.objective_id)
        if objective_row is None:
            raise ValueError("Plan references a missing Objective.")
        if record_to_schema(Objective, objective_row) != plan.objective:
            raise ValueError("Plan Objective differs from the admitted Objective.")

        for assumption in plan.assumptions:
            assumption_row = self._session.get(AssumptionRecord, assumption.assumption_id)
            if assumption_row is None:
                raise ValueError("Plan references a missing Assumption.")
            if record_to_schema(Assumption, assumption_row) != assumption:
                raise ValueError("Plan Assumption differs from the admitted Assumption.")

        tasks: list[Task] = []
        for binding in plan.task_bindings:
            task_row = self._session.get(TaskRecord, binding.task_id)
            if task_row is None:
                raise ValueError("Plan references a missing Task.")
            tasks.append(record_to_schema(Task, task_row))
        plan.validate_tasks(tasks)

        self._session.add(
            PlanRecord(
                plan_id=plan.plan_id,
                objective_id=plan.objective.objective_id,
                objective_snapshot=plan.objective.model_dump(mode="json"),
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
                    assumption_snapshot=assumption.model_dump(mode="json"),
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
        """Reconstruct exact historical content and verify its stored fingerprint."""

        header = self._session.get(PlanRecord, plan_id)
        if header is None:
            return None
        if self._session.get(ObjectiveRecord, header.objective_id) is None:
            raise ValueError("Persisted Plan references a missing Objective.")

        objective = Objective.model_validate(header.objective_snapshot)
        if objective.objective_id != header.objective_id:
            raise ValueError("Persisted Plan Objective snapshot identity is inconsistent.")

        assumption_rows = self._session.exec(
            select(PlanAssumptionRecord).where(PlanAssumptionRecord.plan_id == plan_id)
        ).all()
        assumptions: list[Assumption] = []
        for row in assumption_rows:
            if self._session.get(AssumptionRecord, row.assumption_id) is None:
                raise ValueError("Persisted Plan references a missing Assumption.")
            assumption = Assumption.model_validate(row.assumption_snapshot)
            if assumption.assumption_id != row.assumption_id:
                raise ValueError("Persisted Plan Assumption snapshot identity is inconsistent.")
            assumptions.append(assumption)

        binding_rows = self._session.exec(
            select(PlanTaskBindingRecord).where(PlanTaskBindingRecord.plan_id == plan_id)
        ).all()
        tasks: list[Task] = []
        for binding in binding_rows:
            task_row = self._session.get(TaskRecord, binding.task_id)
            if task_row is None:
                raise ValueError("Persisted Plan references a missing Task.")
            tasks.append(record_to_schema(Task, task_row))

        dependency_rows = self._session.exec(
            select(PlanDependencyRecord).where(PlanDependencyRecord.plan_id == plan_id)
        ).all()
        plan = Plan.model_validate(
            {
                "plan_id": header.plan_id,
                "objective": objective,
                "assumptions": assumptions,
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
                "contract_version": header.contract_version,
            }
        )
        plan.validate_tasks(tasks)
        if plan.fingerprint != header.fingerprint:
            raise ValueError("Persisted Plan fingerprint does not match exact content.")
        return plan


__all__ = ("PlanRepository",)
