"""Bounded SQLite persistence for the M1-A Objective contract."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from cognieda.infrastructure.persistence.models import ObjectiveRecord
from cognieda.infrastructure.persistence.repositories.common import (
    record_to_schema,
    schema_to_record_payload,
)
from cognieda.schemas.artifacts import Objective


class ObjectiveUpdate(BaseModel):
    """M1-B placeholder; M1-A does not implement Objective update behavior."""

    model_config = ConfigDict(extra="forbid")

    text: str | None = None


class ObjectiveRepository:
    """Persist and retrieve minimum MVP Objective state on SQLite."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, objective: Objective) -> Objective:
        record = ObjectiveRecord(**schema_to_record_payload(objective))
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Objective, record)

    def get_by_id(self, objective_id: UUID) -> Objective | None:
        record = self._session.get(ObjectiveRecord, objective_id)
        return None if record is None else record_to_schema(Objective, record)

    def list(self) -> list[Objective]:
        return [
            record_to_schema(Objective, record)
            for record in self._session.exec(select(ObjectiveRecord)).all()
        ]

    def update(self, objective_id: UUID, update: ObjectiveUpdate, **_: object) -> Objective | None:
        raise NotImplementedError("Objective update behavior is deferred to M1-B.")
