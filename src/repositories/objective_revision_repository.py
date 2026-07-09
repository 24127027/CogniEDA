"""Persistence access for ObjectiveRevision provenance records."""

from __future__ import annotations

from uuid import UUID

from db.models import ObjectiveRevisionRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.provenance import ObjectiveRevision
from sqlmodel import Session, asc, select

OBJECTIVE_REVISION_JSON_FIELDS = {"changed_fields"}


class ObjectiveRevisionRepository:
    """Repository for minimal non-FCO ObjectiveRevision provenance records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, revision: ObjectiveRevision) -> ObjectiveRevision:
        """Persist and return a new ObjectiveRevision record."""

        record = ObjectiveRevisionRecord(
            **schema_to_record_payload(
                revision,
                json_fields=OBJECTIVE_REVISION_JSON_FIELDS,
            )
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(ObjectiveRevision, record)

    def get(self, revision_id: UUID | str) -> ObjectiveRevision | None:
        """Return an ObjectiveRevision by primary id if it exists."""

        record = self._session.get(ObjectiveRevisionRecord, UUID(str(revision_id)))
        if record is None:
            return None
        return record_to_schema(ObjectiveRevision, record)

    def list_for_objective(self, objective_id: UUID | str) -> list[ObjectiveRevision]:
        """List ObjectiveRevision records for one Objective in creation order."""

        statement = (
            select(ObjectiveRevisionRecord)
            .where(ObjectiveRevisionRecord.objective_id == UUID(str(objective_id)))
            .order_by(asc(ObjectiveRevisionRecord.created_at))
        )
        records = self._session.exec(statement).all()
        return [record_to_schema(ObjectiveRevision, record) for record in records]
