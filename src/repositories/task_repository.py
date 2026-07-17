"""Persistence access for Task FCOs."""

from __future__ import annotations

import builtins
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlmodel import Session, desc, select

from db.models import DiscoveryRecord, TaskRecord
from repositories.common import apply_update, record_to_schema, schema_to_record_payload
from schemas.artifacts import Task
from schemas.enums import TaskDependencyType, TaskKind, TaskLifecycleState

TASK_JSON_FIELDS = {
    "variables",
    "analytical_specification",
    "motivated_by_discovery_ids",
    "review_reasons",
}


class TaskUpdate(BaseModel):
    """Typed mutable fields for Task workflow-state changes."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    lifecycle_state: TaskLifecycleState | None = None
    task_kind: TaskKind | None = None
    parent_task_id: UUID | None = None
    dependency_type: TaskDependencyType | None = None
    blocked_reason: str | None = None
    superseded_by_task_id: UUID | None = None
    profile_id: UUID | None = None
    variables: list[str] | None = None
    evidence_expectation: str | None = None
    analytical_specification: dict[str, object] | None = None
    motivated_by_discovery_ids: list[UUID] | None = None
    review_reasons: list[str] | None = None
    updated_at: datetime | None = None

    @field_validator("motivated_by_discovery_ids")
    @classmethod
    def _validate_unique_discovery_ids(cls, value: list[UUID] | None) -> list[UUID] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("motivated_by_discovery_ids must not contain duplicates")
        return value

    @model_validator(mode="after")
    def _reject_explicit_null_motivation(self) -> TaskUpdate:
        if (
            "motivated_by_discovery_ids" in self.model_fields_set
            and self.motivated_by_discovery_ids is None
        ):
            raise ValueError("motivated_by_discovery_ids must be a list when provided")
        return self


class TaskRepository:
    """Repository for durable workflow Tasks."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, task: Task) -> Task:
        """Persist and return a new Task."""

        self._validate_motivating_discoveries(task.motivated_by_discovery_ids)
        self._validate_parent(task.task_id, task.parent_task_id)
        record = TaskRecord(**schema_to_record_payload(task, json_fields=TASK_JSON_FIELDS))
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Task, record)

    def get_by_id(self, task_id: UUID) -> Task | None:
        """Return a Task by primary id if it exists."""

        record = self._session.get(TaskRecord, task_id)
        if record is None:
            return None
        return record_to_schema(Task, record)

    def list(
        self,
        *,
        parent_task_id: UUID | None = None,
        profile_id: UUID | None = None,
        lifecycle_state: TaskLifecycleState | None = None,
    ) -> list[Task]:
        """List Tasks with optional hierarchy, profile, and lifecycle filters."""

        statement = select(TaskRecord).order_by(desc(TaskRecord.updated_at))
        if parent_task_id is not None:
            statement = statement.where(TaskRecord.parent_task_id == parent_task_id)
        if profile_id is not None:
            statement = statement.where(TaskRecord.profile_id == profile_id)
        if lifecycle_state is not None:
            statement = statement.where(TaskRecord.lifecycle_state == lifecycle_state)
        records = self._session.exec(statement).all()
        return [record_to_schema(Task, record) for record in records]

    def update(self, task_id: UUID, update: TaskUpdate) -> Task | None:
        """Apply an allowed Task workflow-state transition."""

        record = self._session.get(TaskRecord, task_id)
        if record is None:
            return None
        if "motivated_by_discovery_ids" in update.model_fields_set:
            self._validate_motivating_discoveries(update.motivated_by_discovery_ids or [])
        if "parent_task_id" in update.model_fields_set:
            self._validate_parent(task_id, update.parent_task_id)
        apply_update(record, update, json_fields=TASK_JSON_FIELDS)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Task, record)

    def _validate_motivating_discoveries(self, discovery_ids: Sequence[UUID]) -> None:
        """Require motivation references from this workspace-local graph."""

        for discovery_id in discovery_ids:
            if self._session.get(DiscoveryRecord, discovery_id) is None:
                raise ValueError(f"Referenced Discovery does not exist: {discovery_id}")

    def list_motivated_by_discovery(self, discovery_id: UUID) -> builtins.list[Task]:
        """Return Tasks that are directly motivated by the exact discovery."""
        all_tasks = self.list()
        discovery_str = str(discovery_id)
        # Using exact Python-side filtering because motivated_by_discovery_ids is JSON
        return [
            task
            for task in all_tasks
            if discovery_str in [str(d) for d in task.motivated_by_discovery_ids]
        ]

    def _validate_parent(self, task_id: UUID, parent_task_id: UUID | None) -> None:
        if parent_task_id is None:
            return
        if parent_task_id == task_id:
            raise ValueError("A Task cannot be its own parent.")
        parent = self._session.get(TaskRecord, parent_task_id)
        if parent is None:
            raise ValueError(f"Parent Task does not exist: {parent_task_id}")
        seen: set[UUID] = {task_id}
        current: TaskRecord | None = parent
        while current is not None:
            if current.task_id in seen:
                raise ValueError("Task parent relationship would create a cycle.")
            seen.add(current.task_id)
            current = (
                self._session.get(TaskRecord, current.parent_task_id)
                if current.parent_task_id is not None
                else None
            )
