"""Exact append-only persistence for immutable PlanRevision snapshots."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from cognieda.infrastructure.persistence.models import (
    PlanDependencyRecord,
    PlanRevisionRecord,
    PlanTaskBindingRecord,
    TaskRecord,
)
from cognieda.infrastructure.persistence.repositories.common import record_to_schema
from cognieda.schemas.artifacts import Task
from cognieda.schemas.plan_revision import PlanRevision


class PlanRevisionRepository:
    """Stage and reload complete immutable planning snapshots without CRUD mutation."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, revision: PlanRevision) -> None:
        """Stage one complete revision in the caller-owned transaction."""

        self._session.add(
            PlanRevisionRecord(
                plan_revision_id=revision.plan_revision_id,
                objective_id=revision.objective_id,
                contract_version=revision.contract_version,
                fingerprint=revision.fingerprint,
            )
        )
        self._session.flush()
        self._session.add_all(
            [
                PlanTaskBindingRecord(
                    plan_revision_id=revision.plan_revision_id,
                    task_id=binding.task_id,
                    order_rank=binding.order_rank,
                    priority=binding.priority,
                )
                for binding in revision.task_bindings
            ]
        )
        self._session.flush()
        self._session.add_all(
            [
                PlanDependencyRecord(
                    plan_revision_id=revision.plan_revision_id,
                    prerequisite_task_id=dependency.prerequisite_task_id,
                    dependent_task_id=dependency.dependent_task_id,
                )
                for dependency in revision.dependencies
            ]
        )

    def get_by_id(self, plan_revision_id: UUID) -> PlanRevision | None:
        header = self._session.get(PlanRevisionRecord, plan_revision_id)
        if header is None:
            return None

        binding_rows = self._session.exec(
            select(PlanTaskBindingRecord).where(
                PlanTaskBindingRecord.plan_revision_id == plan_revision_id
            )
        ).all()
        dependency_rows = self._session.exec(
            select(PlanDependencyRecord).where(
                PlanDependencyRecord.plan_revision_id == plan_revision_id
            )
        ).all()
        task_rows: list[TaskRecord] = []
        for binding in binding_rows:
            task_record = self._session.get(TaskRecord, binding.task_id)
            if task_record is None:
                raise ValueError("Persisted PlanRevision references a missing Task.")
            task_rows.append(task_record)

        revision = PlanRevision.model_validate(
            {
                "plan_revision_id": header.plan_revision_id,
                "objective_id": header.objective_id,
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
            context={
                "tasks": tuple(
                    record_to_schema(Task, task_record) for task_record in task_rows
                )
            },
        )
        if revision.fingerprint != header.fingerprint:
            raise ValueError("Persisted PlanRevision fingerprint does not match exact content.")
        return revision


__all__ = ("PlanRevisionRepository",)
