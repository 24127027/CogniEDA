"""Persistence access for Assumption FCOs."""

from __future__ import annotations

import builtins
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, desc, select

from db.models import AssumptionRecord, DiscoveryRecord
from repositories.common import (
    apply_update,
    filter_records_by_related_id,
    record_to_schema,
    schema_to_record_payload,
)
from schemas.artifacts import Assumption
from schemas.enums import AssumptionStatus

ASSUMPTION_JSON_FIELDS = {
    "scoped_data_profile_ids",
    "contradicted_by_discovery_ids",
}


class AssumptionUpdate(BaseModel):
    """Typed lifecycle fields for Assumption review without rewriting truth."""

    model_config = ConfigDict(extra="forbid")

    status: AssumptionStatus | None = None
    contradicted_by_discovery_ids: list[UUID] | None = None
    replacement_assumption_id: UUID | None = None
    updated_at: datetime | None = None


class AssumptionRepository:
    """Repository for assumptions used in planning context."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, assumption: Assumption) -> Assumption:
        """Persist and return a new Assumption."""

        record = AssumptionRecord(
            **schema_to_record_payload(
                assumption,
                json_fields=ASSUMPTION_JSON_FIELDS,
            )
        )
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
        if status is not None:
            statement = statement.where(AssumptionRecord.status == status)
        records = self._session.exec(statement).all()
        if profile_id is not None:
            records = filter_records_by_related_id(
                records,
                field_name="scoped_data_profile_ids",
                related_id=profile_id,
            )
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
        apply_update(record, update, json_fields=ASSUMPTION_JSON_FIELDS)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Assumption, record)

    def flag_for_contradiction(
        self,
        assumption_id: UUID,
        *,
        discovery_id: UUID,
    ) -> Assumption | None:
        """Flag an Assumption for review without rewriting its statement."""

        record = self._session.get(AssumptionRecord, assumption_id)
        if record is None:
            return None
        if self._session.get(DiscoveryRecord, discovery_id) is None:
            raise ValueError("Contradiction review requires an existing Discovery.")
        discovery_ref = str(discovery_id)
        contradicted_by_discovery_ids = list(record.contradicted_by_discovery_ids)
        if discovery_ref not in contradicted_by_discovery_ids:
            contradicted_by_discovery_ids.append(discovery_ref)
        record.contradicted_by_discovery_ids = contradicted_by_discovery_ids
        record.status = AssumptionStatus.FLAGGED
        record.updated_at = datetime.now(UTC)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Assumption, record)
