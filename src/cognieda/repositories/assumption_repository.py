"""Bounded SQLite persistence for the M1-A Assumption contract."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from cognieda.db.models import AssumptionRecord
from cognieda.repositories.common import record_to_schema, schema_to_record_payload
from cognieda.schemas.artifacts import Assumption

ASSUMPTION_JSON_FIELDS: set[str] = set()


class AssumptionUpdate(BaseModel):
    """M1-B placeholder; M1-A has no Assumption lifecycle mutation."""

    model_config = ConfigDict(extra="forbid")

    text: str | None = None


class AssumptionRepository:
    """Persist and retrieve planning-only MVP Assumptions on SQLite."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, assumption: Assumption) -> Assumption:
        record = AssumptionRecord(**schema_to_record_payload(assumption))
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Assumption, record)

    def get_by_id(self, assumption_id: UUID) -> Assumption | None:
        record = self._session.get(AssumptionRecord, assumption_id)
        return None if record is None else record_to_schema(Assumption, record)

    def list(self) -> list[Assumption]:
        return [
            record_to_schema(Assumption, record)
            for record in self._session.exec(select(AssumptionRecord)).all()
        ]

    def update(self, assumption_id: UUID, update: AssumptionUpdate) -> Assumption | None:
        raise NotImplementedError("Assumption update behavior is deferred to M1-B.")
