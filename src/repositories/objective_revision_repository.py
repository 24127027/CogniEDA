"""Append-only persistence for ObjectiveRevision provenance."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, asc, select

from db.models import ObjectiveRevisionRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.provenance import ObjectiveRevision

OBJECTIVE_REVISION_JSON_FIELDS = {"changed_fields"}


class ObjectiveRevisionRepository:
    """Read and append immutable Objective revision history."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def stage_for_objective_mutation(
        self,
        revision: ObjectiveRevision,
    ) -> ObjectiveRevisionRecord:
        """Stage one revision in the caller-owned transaction."""

        record = ObjectiveRevisionRecord(
            **schema_to_record_payload(
                revision,
                json_fields=OBJECTIVE_REVISION_JSON_FIELDS,
            )
        )
        self._session.add(record)
        return record

    def get_by_id(self, revision_id: UUID) -> ObjectiveRevision | None:
        """Return one immutable revision by id."""

        record = self._session.get(ObjectiveRevisionRecord, revision_id)
        if record is None:
            return None
        return record_to_schema(ObjectiveRevision, record)

    def list_for_objective(self, objective_id: UUID) -> list[ObjectiveRevision]:
        """List one Objective's revisions in deterministic creation order."""

        statement = (
            select(ObjectiveRevisionRecord)
            .where(ObjectiveRevisionRecord.objective_id == objective_id)
            .order_by(
                asc(ObjectiveRevisionRecord.created_at),
                asc(ObjectiveRevisionRecord.objective_revision_id),
            )
        )
        records = self._session.exec(statement).all()
        return [record_to_schema(ObjectiveRevision, record) for record in records]
