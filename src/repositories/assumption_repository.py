"""Persistence access for assumption artifacts."""

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
    """Typed mutable fields for assumption updates."""

    statement: str | None = None
    basis: str | None = None
    confidence: ConfidenceLevel | None = None
    status: AssumptionStatus | None = None
    dataset_id: UUID | None = None
    profile_id: UUID | None = None
    updated_at: datetime | None = None


class AssumptionRepository:
    """Artifact-specific CRUD access for assumptions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, assumption: Assumption) -> Assumption:
        """Persist and return a new assumption artifact."""

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
        project_id: UUID | None = None,
        dataset_id: UUID | None = None,
        profile_id: UUID | None = None,
        status: AssumptionStatus | None = None,
    ) -> list[Assumption]:
        """List assumptions with optional project, dataset, profile, and status filters."""

        statement = select(AssumptionRecord).order_by(desc(AssumptionRecord.updated_at))
        if project_id is not None:
            statement = statement.where(AssumptionRecord.project_id == project_id)
        if dataset_id is not None:
            statement = statement.where(AssumptionRecord.dataset_id == dataset_id)
        if profile_id is not None:
            statement = statement.where(AssumptionRecord.profile_id == profile_id)
        if status is not None:
            statement = statement.where(AssumptionRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(Assumption, record) for record in records]

    def list_active(self, *, project_id: UUID | None = None) -> builtins.list[Assumption]:
        """List only active assumptions."""

        return self.list(project_id=project_id, status=AssumptionStatus.ACTIVE)

    def list_for_dataset(self, dataset_id: UUID) -> builtins.list[Assumption]:
        """List assumptions linked to a dataset."""

        return self.list(dataset_id=dataset_id)

    def update(self, assumption_id: UUID, update: AssumptionUpdate) -> Assumption | None:
        """Apply a typed partial update to an assumption record."""

        record = self._session.get(AssumptionRecord, assumption_id)
        if record is None:
            return None
        apply_update(record, update)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Assumption, record)
