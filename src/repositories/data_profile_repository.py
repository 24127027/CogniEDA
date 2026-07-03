"""Persistence access for append-only DataProfile FCOs."""

from __future__ import annotations

import builtins
from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import DataProfileRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.artifacts import DataProfile
from schemas.enums import DataProfileLifecycleState, DataProfileMethod

DATA_PROFILE_JSON_FIELDS = {
    "schema_summary",
    "baseline_summary",
    "quality_flags",
    "preprocessing_history",
    "artifact_refs",
}


class DataProfileRepository:
    """Repository for immutable DataProfile records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, data_profile: DataProfile) -> DataProfile:
        """Persist and return a new DataProfile."""

        record = DataProfileRecord(
            **schema_to_record_payload(data_profile, json_fields=DATA_PROFILE_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(DataProfile, record)

    def get_by_id(self, profile_id: UUID) -> DataProfile | None:
        """Return a DataProfile by primary id if it exists."""

        record = self._session.get(DataProfileRecord, profile_id)
        if record is None:
            return None
        return record_to_schema(DataProfile, record)

    def list(
        self,
        *,
        dataset_path: str | None = None,
        dvc_hash: str | None = None,
        method: DataProfileMethod | None = None,
        lifecycle_state: DataProfileLifecycleState | None = None,
        accepted_as_ground_truth: bool | None = None,
    ) -> list[DataProfile]:
        """List profiles with optional data-version and lifecycle filters."""

        statement = select(DataProfileRecord).order_by(desc(DataProfileRecord.created_at))
        if dataset_path is not None:
            statement = statement.where(DataProfileRecord.dataset_path == dataset_path)
        if dvc_hash is not None:
            statement = statement.where(DataProfileRecord.dvc_hash == dvc_hash)
        if method is not None:
            statement = statement.where(DataProfileRecord.method == method)
        if lifecycle_state is not None:
            statement = statement.where(DataProfileRecord.lifecycle_state == lifecycle_state)
        if accepted_as_ground_truth is not None:
            statement = statement.where(
                DataProfileRecord.accepted_as_ground_truth == accepted_as_ground_truth
            )
        records = self._session.exec(statement).all()
        return [record_to_schema(DataProfile, record) for record in records]

    def list_for_dataset_path(self, dataset_path: str) -> builtins.list[DataProfile]:
        """List all profiles for a physical or logical dataset path."""

        return self.list(dataset_path=dataset_path)

    def get_latest_for_dataset_path(
        self,
        dataset_path: str,
        *,
        method: DataProfileMethod | None = None,
    ) -> DataProfile | None:
        """Return the newest profile for a dataset path, optionally scoped by method."""

        statement = (
            select(DataProfileRecord)
            .where(DataProfileRecord.dataset_path == dataset_path)
            .order_by(desc(DataProfileRecord.created_at))
            .limit(1)
        )
        if method is not None:
            statement = statement.where(DataProfileRecord.method == method)
        record = self._session.exec(statement).first()
        if record is None:
            return None
        return record_to_schema(DataProfile, record)
