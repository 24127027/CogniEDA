"""Persistence access for append-only data profile artifacts."""

from __future__ import annotations

import builtins
from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import DataProfileRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.artifacts import DataProfile
from schemas.enums import DataProfileMethod

DATA_PROFILE_JSON_FIELDS = {"schema_summary", "baseline_summary", "quality_flags"}


class DataProfileRepository:
    """Artifact-specific CRUD access for append-only data profiles."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data_profile: DataProfile) -> DataProfile:
        """Persist and return a new data profile artifact."""

        record = DataProfileRecord(
            **schema_to_record_payload(data_profile, json_fields=DATA_PROFILE_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(DataProfile, record)

    def get_by_id(self, profile_id: UUID) -> DataProfile | None:
        """Return a data profile by primary id if it exists."""

        record = self._session.get(DataProfileRecord, profile_id)
        if record is None:
            return None
        return record_to_schema(DataProfile, record)

    def list(
        self,
        *,
        project_id: UUID | None = None,
        dataset_id: UUID | None = None,
        method: DataProfileMethod | None = None,
    ) -> list[DataProfile]:
        """List data profiles with optional project, dataset, and method filters."""

        statement = select(DataProfileRecord).order_by(desc(DataProfileRecord.created_at))
        if project_id is not None:
            statement = statement.where(DataProfileRecord.project_id == project_id)
        if dataset_id is not None:
            statement = statement.where(DataProfileRecord.dataset_id == dataset_id)
        if method is not None:
            statement = statement.where(DataProfileRecord.method == method)
        records = self._session.exec(statement).all()
        return [record_to_schema(DataProfile, record) for record in records]

    def list_for_dataset(self, dataset_id: UUID) -> builtins.list[DataProfile]:
        """List profiles for a dataset."""

        return self.list(dataset_id=dataset_id)

    def get_latest_for_dataset(
        self,
        dataset_id: UUID,
        *,
        method: DataProfileMethod | None = None,
    ) -> DataProfile | None:
        """Return the latest profile for a dataset, optionally scoped to a method."""

        statement = (
            select(DataProfileRecord)
            .where(DataProfileRecord.dataset_id == dataset_id)
            .order_by(desc(DataProfileRecord.created_at))
            .limit(1)
        )
        if method is not None:
            statement = statement.where(DataProfileRecord.method == method)
        record = self._session.exec(statement).first()
        if record is None:
            return None
        return record_to_schema(DataProfile, record)
