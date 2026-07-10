"""Persistence access for Task FCOs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, desc, select

from db.models import TaskRecord
from repositories.common import apply_update, record_to_schema, schema_to_record_payload
from schemas.artifacts import Task
from schemas.enums import TaskKind, TaskLifecycleState

TASK_JSON_FIELDS = {"variables", "analytical_specification"}


class TaskUpdate(BaseModel):
    """Typed mutable fields for Task workflow-state changes."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    lifecycle_state: TaskLifecycleState | None = None
    task_kind: TaskKind | None = None
    parent_task_id: UUID | None = None
    profile_id: UUID | None = None
    variables: list[str] | None = None
    evidence_expectation: str | None = None
    analytical_specification: dict[str, object] | None = None
    updated_at: datetime | None = None


class TaskRepository:
    """Repository for durable workflow Tasks."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, task: Task) -> Task:
        """Persist and return a new Task."""

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
        apply_update(record, update, json_fields=TASK_JSON_FIELDS)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Task, record)
