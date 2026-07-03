"""Persistence access for Objective FCOs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, desc, select

from db.models import ObjectiveRecord
from repositories.common import apply_update, record_to_schema, schema_to_record_payload
from schemas.artifacts import Objective
from schemas.enums import ObjectiveStatus


class ObjectiveUpdate(BaseModel):
    """Typed mutable fields for Objective lifecycle and wording changes."""

    title: str | None = None
    statement: str | None = None
    status: ObjectiveStatus | None = None
    updated_at: datetime | None = None


class ObjectiveRepository:
    """Repository for workspace-local Objective records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, objective: Objective) -> Objective:
        """Persist and return a new Objective."""

        record = ObjectiveRecord(**schema_to_record_payload(objective))
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Objective, record)

    def get_by_id(self, objective_id: UUID) -> Objective | None:
        """Return an Objective by primary id if it exists."""

        record = self._session.get(ObjectiveRecord, objective_id)
        if record is None:
            return None
        return record_to_schema(Objective, record)

    def list(self, *, status: ObjectiveStatus | None = None) -> list[Objective]:
        """List objectives with an optional lifecycle filter."""

        statement = select(ObjectiveRecord).order_by(desc(ObjectiveRecord.updated_at))
        if status is not None:
            statement = statement.where(ObjectiveRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(Objective, record) for record in records]

    def update(self, objective_id: UUID, update: ObjectiveUpdate) -> Objective | None:
        """Apply an allowed Objective lifecycle or wording transition."""

        record = self._session.get(ObjectiveRecord, objective_id)
        if record is None:
            return None
        apply_update(record, update)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Objective, record)
