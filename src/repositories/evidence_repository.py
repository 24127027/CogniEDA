"""Bounded append-only SQLite persistence for direct M1-A Evidence lineage."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from db.models import DataProfileRecord, EvidenceRecord, TaskRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.artifacts import Evidence

EVIDENCE_JSON_FIELDS = {"content", "provenance", "artifact_refs"}


class EvidenceRepository:
    """Persist Evidence only when its real Task and DataProfile already exist."""

    def __init__(self, session: Session, **_: object) -> None:
        self._session = session

    def create(self, evidence: Evidence) -> Evidence:
        if self._session.get(TaskRecord, evidence.task_id) is None:
            raise ValueError("Evidence requires an existing Task.")
        if self._session.get(DataProfileRecord, evidence.data_profile_id) is None:
            raise ValueError("Evidence requires an existing DataProfile.")
        record = EvidenceRecord(
            **schema_to_record_payload(evidence, json_fields=EVIDENCE_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Evidence, record)

    def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        record = self._session.get(EvidenceRecord, evidence_id)
        return None if record is None else record_to_schema(Evidence, record)

    def list(
        self,
        *,
        task_id: UUID | None = None,
        data_profile_id: UUID | None = None,
    ) -> list[Evidence]:
        statement = select(EvidenceRecord)
        if task_id is not None:
            statement = statement.where(EvidenceRecord.task_id == task_id)
        if data_profile_id is not None:
            statement = statement.where(EvidenceRecord.data_profile_id == data_profile_id)
        return [
            record_to_schema(Evidence, record) for record in self._session.exec(statement).all()
        ]
