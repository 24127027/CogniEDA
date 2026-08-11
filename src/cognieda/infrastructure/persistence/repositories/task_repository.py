"""Bounded SQLite persistence for the canonical Task semantic core."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from cognieda.infrastructure.persistence.models import TaskRecord
from cognieda.infrastructure.persistence.repositories.common import (
    apply_update,
    record_to_schema,
    schema_to_record_payload,
)
from cognieda.schemas.artifacts import Task
from cognieda.schemas.enums import TaskStatus

TASK_JSON_FIELDS: set[str] = set()


class TaskUpdate(BaseModel):
    """Only execution status is mutable in the active Task repository boundary."""

    model_config = ConfigDict(extra="forbid")

    status: TaskStatus | None = None


class TaskRepository:
    """Persist canonical Task semantics without plan or scientific fields."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, task: Task) -> Task:
        record = TaskRecord(**schema_to_record_payload(task))
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Task, record)

    def get_by_id(self, task_id: UUID) -> Task | None:
        record = self._session.get(TaskRecord, task_id)
        return None if record is None else record_to_schema(Task, record)

    def list(self, *, status: TaskStatus | None = None) -> list[Task]:
        statement = select(TaskRecord)
        if status is not None:
            statement = statement.where(TaskRecord.status == status)
        return [record_to_schema(Task, record) for record in self._session.exec(statement).all()]

    def update(self, task_id: UUID, update: TaskUpdate) -> Task | None:
        record = self._session.get(TaskRecord, task_id)
        if record is None:
            return None
        apply_update(record, update)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Task, record)
