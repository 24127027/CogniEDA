"""Bounded append-only SQLite persistence for M1-A DataProfiles."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from cognieda.infrastructure.persistence.models import (
    DataProfileDatasetBindingRecord,
    DataProfileRecord,
)
from cognieda.infrastructure.persistence.repositories.common import (
    record_to_schema,
    schema_to_record_payload,
)
from cognieda.schemas import DataProfile, DataProfileDatasetBinding

DATA_PROFILE_JSON_FIELDS = {"columns"}


class DataProfileRepository:
    """Persist immutable MVP DataProfile snapshots without dataset lifecycle fields."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data_profile: DataProfile) -> DataProfile:
        self.add(data_profile)
        self._session.commit()
        record = self._session.get(DataProfileRecord, data_profile.data_profile_id)
        if record is None:
            raise RuntimeError("Committed DataProfile could not be reloaded.")
        self._session.refresh(record)
        return record_to_schema(DataProfile, record)

    def add(self, data_profile: DataProfile) -> None:
        """Stage a DataProfile without committing the caller's transaction."""

        record = DataProfileRecord(
            **schema_to_record_payload(data_profile, json_fields=DATA_PROFILE_JSON_FIELDS)
        )
        self._session.add(record)

    def get_by_id(self, data_profile_id: UUID) -> DataProfile | None:
        record = self._session.get(DataProfileRecord, data_profile_id)
        return None if record is None else record_to_schema(DataProfile, record)

    def list(self) -> list[DataProfile]:
        return [
            record_to_schema(DataProfile, record)
            for record in self._session.exec(select(DataProfileRecord)).all()
        ]


class DataProfileDatasetBindingRepository:
    """Persist immutable one-to-one DataProfile physical dataset bindings."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, binding: DataProfileDatasetBinding) -> None:
        self._session.add(DataProfileDatasetBindingRecord(**binding.model_dump()))

    def get_by_profile_id(
        self, data_profile_id: UUID
    ) -> DataProfileDatasetBinding | None:
        record = self._session.get(DataProfileDatasetBindingRecord, data_profile_id)
        return (
            None
            if record is None
            else DataProfileDatasetBinding.model_validate(record, from_attributes=True)
        )
