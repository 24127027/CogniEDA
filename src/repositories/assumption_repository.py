"""Persistence access for Assumption FCOs."""

from __future__ import annotations

import builtins
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, desc, select

from db.models import AssumptionRecord
from repositories.common import apply_update, record_to_schema, schema_to_record_payload
from schemas.artifacts import Assumption
from schemas.enums import AssumptionStatus, ConfidenceLevel


class AssumptionUpdate(BaseModel):
    """Typed mutable fields for assumption lifecycle and wording changes."""

    statement: str | None = None
    basis: str | None = None
    confidence: ConfidenceLevel | None = None
    status: AssumptionStatus | None = None
    profile_id: UUID | None = None
    updated_at: datetime | None = None


class AssumptionRepository:
    """Repository for assumptions used in planning context."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, assumption: Assumption) -> Assumption:
        """Persist and return a new Assumption."""

        record = AssumptionRecord(**schema_to_record_payload(assumption))
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Assumption, record)

    def get_by_id(self, assumption_id: UUID) -> Assumption | None:
        """Return an assumption by primary id if it exists."""

        record = self._session.get(AssumptionRecord, assumption_id)
        if record is None:
            return None
        return record_to_schema(Assumption, record)

    def list(
        self,
        *,
        profile_id: UUID | None = None,
        status: AssumptionStatus | None = None,
    ) -> list[Assumption]:
        """List assumptions with optional profile and status filters."""

        statement = select(AssumptionRecord).order_by(desc(AssumptionRecord.updated_at))
        if profile_id is not None:
            statement = statement.where(AssumptionRecord.profile_id == profile_id)
        if status is not None:
            statement = statement.where(AssumptionRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(Assumption, record) for record in records]

    def list_active(self) -> builtins.list[Assumption]:
        """List active assumptions for planning context."""

        return self.list(status=AssumptionStatus.ACTIVE)

    def list_for_profile(self, profile_id: UUID) -> builtins.list[Assumption]:
        """List assumptions linked to a DataProfile."""

        return self.list(profile_id=profile_id)

    def update(self, assumption_id: UUID, update: AssumptionUpdate) -> Assumption | None:
        """Apply an allowed assumption lifecycle or wording transition."""

        record = self._session.get(AssumptionRecord, assumption_id)
        if record is None:
            return None
        apply_update(record, update)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Assumption, record)
