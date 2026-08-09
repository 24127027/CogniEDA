"""Bounded append-only SQLite persistence for M1-A DataProfiles."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from db.models import DataProfileRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.artifacts import DataProfile

DATA_PROFILE_JSON_FIELDS = {"columns"}


class DataProfileRepository:
    """Persist immutable MVP DataProfile snapshots without dataset lifecycle fields."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data_profile: DataProfile) -> DataProfile:
        record = DataProfileRecord(
            **schema_to_record_payload(data_profile, json_fields=DATA_PROFILE_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(DataProfile, record)

    def get_by_id(self, data_profile_id: UUID) -> DataProfile | None:
        record = self._session.get(DataProfileRecord, data_profile_id)
        return None if record is None else record_to_schema(DataProfile, record)

    def list(self) -> list[DataProfile]:
        return [
            record_to_schema(DataProfile, record)
            for record in self._session.exec(select(DataProfileRecord)).all()
        ]
