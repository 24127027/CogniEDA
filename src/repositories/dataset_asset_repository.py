"""Persistence access for dataset asset artifacts."""

from __future__ import annotations

import builtins
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, desc, select

from db.models import DatasetAssetRecord, DatasetLineageLinkRecord
from repositories.common import (
    dedupe_preserving_order,
    load_records_by_ids,
    load_related_ids,
    replace_link_records,
)
from schemas.artifacts import DatasetAsset
from schemas.common import LineageStep
from schemas.enums import DatasetKind, DatasetRole, DatasetSourceType

DATASET_ASSET_JSON_FIELDS = {"lineage_steps"}


class DatasetAssetUpdate(BaseModel):
    """Typed mutable fields for dataset-asset updates."""

    name: str | None = None
    source_type: DatasetSourceType | None = None
    location: str | None = None
    version: str | None = None
    kind: DatasetKind | None = None
    role: DatasetRole | None = None
    upstream_dataset_ids: list[UUID] | None = None
    lineage_steps: list[LineageStep] | None = None
    description: str | None = None
    updated_at: datetime | None = None


class DatasetAssetRepository:
    """Artifact-specific CRUD access for dataset assets."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, dataset_asset: DatasetAsset) -> DatasetAsset:
        """Persist and return a new dataset asset artifact."""

        record = DatasetAssetRecord(**self._record_payload(dataset_asset))
        self._session.add(record)
        self._sync_lineage_links(
            dataset_asset.dataset_id,
            dataset_asset.upstream_dataset_ids,
        )
        self._session.commit()
        self._session.refresh(record)
        return self._hydrate(record)

    def get_by_id(self, dataset_id: UUID) -> DatasetAsset | None:
        """Return a dataset asset by primary id if it exists."""

        record = self._session.get(DatasetAssetRecord, dataset_id)
        if record is None:
            return None
        return self._hydrate(record)

    def list(
        self,
        *,
        project_id: UUID | None = None,
        kind: DatasetKind | None = None,
        role: DatasetRole | None = None,
        source_type: DatasetSourceType | None = None,
    ) -> list[DatasetAsset]:
        """List dataset assets with optional project and domain filters."""

        statement = select(DatasetAssetRecord).order_by(desc(DatasetAssetRecord.updated_at))
        if project_id is not None:
            statement = statement.where(DatasetAssetRecord.project_id == project_id)
        if kind is not None:
            statement = statement.where(DatasetAssetRecord.kind == kind)
        if role is not None:
            statement = statement.where(DatasetAssetRecord.role == role)
        if source_type is not None:
            statement = statement.where(DatasetAssetRecord.source_type == source_type)
        records = self._session.exec(statement).all()
        return [self._hydrate(record) for record in records]

    def list_children(self, parent_dataset_id: UUID) -> builtins.list[DatasetAsset]:
        """List dataset assets derived from an upstream dataset."""

        child_ids = load_related_ids(
            self._session,
            DatasetLineageLinkRecord,
            owner_field_name="upstream_dataset_id",
            owner_id=parent_dataset_id,
            related_field_name="dataset_id",
        )
        records = load_records_by_ids(self._session, DatasetAssetRecord, child_ids)
        records.sort(key=lambda item: item.updated_at, reverse=True)
        return [self._hydrate(record) for record in records]

    def list_upstream(self, dataset_id: UUID) -> builtins.list[DatasetAsset]:
        """List upstream dataset assets referenced by a derived dataset."""

        upstream_ids = load_related_ids(
            self._session,
            DatasetLineageLinkRecord,
            owner_field_name="dataset_id",
            owner_id=dataset_id,
            related_field_name="upstream_dataset_id",
        )
        if not upstream_ids:
            return []
        records = load_records_by_ids(self._session, DatasetAssetRecord, upstream_ids)
        records.sort(key=lambda item: item.updated_at, reverse=True)
        return [self._hydrate(record) for record in records]

    def list_by_name(self, project_id: UUID, name: str) -> builtins.list[DatasetAsset]:
        """List dataset assets matching a name within a project."""

        statement = (
            select(DatasetAssetRecord)
            .where(DatasetAssetRecord.project_id == project_id)
            .where(DatasetAssetRecord.name == name)
            .order_by(desc(DatasetAssetRecord.updated_at))
        )
        records = self._session.exec(statement).all()
        return [self._hydrate(record) for record in records]

    def update(self, dataset_id: UUID, update: DatasetAssetUpdate) -> DatasetAsset | None:
        """Apply a typed partial update to a dataset asset record."""

        record = self._session.get(DatasetAssetRecord, dataset_id)
        if record is None:
            return None
        self._apply_update(record, update)
        if update.upstream_dataset_ids is not None:
            self._sync_lineage_links(dataset_id, update.upstream_dataset_ids)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return self._hydrate(record)

    def _hydrate(self, record: DatasetAssetRecord) -> DatasetAsset:
        payload = record.model_dump()
        payload["upstream_dataset_ids"] = load_related_ids(
            self._session,
            DatasetLineageLinkRecord,
            owner_field_name="dataset_id",
            owner_id=record.dataset_id,
            related_field_name="upstream_dataset_id",
        )
        return DatasetAsset.model_validate(payload)

    def _record_payload(self, dataset_asset: DatasetAsset) -> dict[str, object]:
        python_payload = dataset_asset.model_dump(
            mode="python",
            exclude={"upstream_dataset_ids"},
        )
        json_payload = dataset_asset.model_dump(
            mode="json",
            include=DATASET_ASSET_JSON_FIELDS,
        )
        python_payload["lineage_steps"] = json_payload["lineage_steps"]
        return python_payload

    def _apply_update(
        self,
        record: DatasetAssetRecord,
        update: DatasetAssetUpdate,
    ) -> None:
        python_payload = update.model_dump(
            mode="python",
            exclude_unset=True,
            exclude={"upstream_dataset_ids"},
        )
        json_payload = update.model_dump(
            mode="json",
            exclude_unset=True,
            include=DATASET_ASSET_JSON_FIELDS,
        )
        if "lineage_steps" in json_payload:
            python_payload["lineage_steps"] = json_payload["lineage_steps"]
        for field_name, field_value in python_payload.items():
            setattr(record, field_name, field_value)
        record.updated_at = datetime.now(UTC)

    def _sync_lineage_links(
        self,
        dataset_id: UUID,
        upstream_dataset_ids: builtins.list[UUID],
    ) -> None:
        deduped_ids: builtins.list[UUID] = dedupe_preserving_order(upstream_dataset_ids)
        replace_link_records(
            self._session,
            DatasetLineageLinkRecord,
            owner_field_name="dataset_id",
            owner_id=dataset_id,
            payloads=[
                {
                    "dataset_id": dataset_id,
                    "upstream_dataset_id": upstream_dataset_id,
                }
                for upstream_dataset_id in deduped_ids
            ],
        )
