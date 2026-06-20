"""Persistence access for hypothesis artifacts."""

from __future__ import annotations

import builtins
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, desc, select

from db.models import (
    HypothesisAssumptionLinkRecord,
    HypothesisDatasetLinkRecord,
    HypothesisRecord,
)
from repositories.common import (
    dedupe_preserving_order,
    load_records_by_ids,
    load_related_ids,
    replace_link_records,
)
from schemas.artifacts import Hypothesis
from schemas.enums import HypothesisStatus

HYPOTHESIS_JSON_FIELDS = {"variables"}


class HypothesisUpdate(BaseModel):
    """Typed mutable fields for hypothesis updates."""

    statement: str | None = None
    variables: list[str] | None = None
    scope: str | None = None
    validation_method: str | None = None
    status: HypothesisStatus | None = None
    assumption_ids: list[UUID] | None = None
    dataset_ids: list[UUID] | None = None
    updated_at: datetime | None = None


class HypothesisRepository:
    """Artifact-specific CRUD access for hypotheses."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, hypothesis: Hypothesis) -> Hypothesis:
        """Persist and return a new hypothesis artifact."""

        record = HypothesisRecord(**self._record_payload(hypothesis))
        self._session.add(record)
        self._sync_assumption_links(hypothesis.hypothesis_id, hypothesis.assumption_ids)
        self._sync_dataset_links(hypothesis.hypothesis_id, hypothesis.dataset_ids)
        self._session.commit()
        self._session.refresh(record)
        return self._hydrate(record)

    def get_by_id(self, hypothesis_id: UUID) -> Hypothesis | None:
        """Return a hypothesis by primary id if it exists."""

        record = self._session.get(HypothesisRecord, hypothesis_id)
        if record is None:
            return None
        return self._hydrate(record)

    def list(self, *, project_id: UUID | None = None) -> list[Hypothesis]:
        """List hypotheses, optionally scoped to a project."""

        statement = select(HypothesisRecord).order_by(desc(HypothesisRecord.updated_at))
        if project_id is not None:
            statement = statement.where(HypothesisRecord.project_id == project_id)
        records = self._session.exec(statement).all()
        return [self._hydrate(record) for record in records]

    def list_active(self, *, project_id: UUID | None = None) -> builtins.list[Hypothesis]:
        """List only active working-context hypotheses."""

        active_statuses = (
            HypothesisStatus.PROPOSED,
            HypothesisStatus.PLANNED,
            HypothesisStatus.VALIDATING,
            HypothesisStatus.INCONCLUSIVE,
        )
        hypotheses = self.list(project_id=project_id)
        return [hypothesis for hypothesis in hypotheses if hypothesis.status in active_statuses]

    def list_for_dataset(self, dataset_id: UUID) -> builtins.list[Hypothesis]:
        """List hypotheses linked to a dataset id."""

        hypothesis_ids = load_related_ids(
            self._session,
            HypothesisDatasetLinkRecord,
            owner_field_name="dataset_id",
            owner_id=dataset_id,
            related_field_name="hypothesis_id",
        )
        records = load_records_by_ids(self._session, HypothesisRecord, hypothesis_ids)
        records.sort(key=lambda item: item.updated_at, reverse=True)
        return [self._hydrate(record) for record in records]

    def list_for_assumption(self, assumption_id: UUID) -> builtins.list[Hypothesis]:
        """List hypotheses linked to an assumption id."""

        hypothesis_ids = load_related_ids(
            self._session,
            HypothesisAssumptionLinkRecord,
            owner_field_name="assumption_id",
            owner_id=assumption_id,
            related_field_name="hypothesis_id",
        )
        records = load_records_by_ids(self._session, HypothesisRecord, hypothesis_ids)
        records.sort(key=lambda item: item.updated_at, reverse=True)
        return [self._hydrate(record) for record in records]

    def update(self, hypothesis_id: UUID, update: HypothesisUpdate) -> Hypothesis | None:
        """Apply a typed partial update to a hypothesis record."""

        record = self._session.get(HypothesisRecord, hypothesis_id)
        if record is None:
            return None
        self._apply_update(record, update)
        if update.assumption_ids is not None:
            self._sync_assumption_links(hypothesis_id, update.assumption_ids)
        if update.dataset_ids is not None:
            self._sync_dataset_links(hypothesis_id, update.dataset_ids)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return self._hydrate(record)

    def _hydrate(self, record: HypothesisRecord) -> Hypothesis:
        payload = record.model_dump()
        payload["assumption_ids"] = load_related_ids(
            self._session,
            HypothesisAssumptionLinkRecord,
            owner_field_name="hypothesis_id",
            owner_id=record.hypothesis_id,
            related_field_name="assumption_id",
        )
        payload["dataset_ids"] = load_related_ids(
            self._session,
            HypothesisDatasetLinkRecord,
            owner_field_name="hypothesis_id",
            owner_id=record.hypothesis_id,
            related_field_name="dataset_id",
        )
        return Hypothesis.model_validate(payload)

    def _record_payload(self, hypothesis: Hypothesis) -> dict[str, object]:
        python_payload = hypothesis.model_dump(
            mode="python",
            exclude={"assumption_ids", "dataset_ids"},
        )
        json_payload = hypothesis.model_dump(
            mode="json",
            include=HYPOTHESIS_JSON_FIELDS,
        )
        if "variables" in json_payload:
            python_payload["variables"] = json_payload["variables"]
        return python_payload

    def _apply_update(self, record: HypothesisRecord, update: HypothesisUpdate) -> None:
        python_payload = update.model_dump(
            mode="python",
            exclude_unset=True,
            exclude={"assumption_ids", "dataset_ids"},
        )
        json_payload = update.model_dump(
            mode="json",
            exclude_unset=True,
            include=HYPOTHESIS_JSON_FIELDS,
        )
        if "variables" in json_payload:
            python_payload["variables"] = json_payload["variables"]
        for field_name, field_value in python_payload.items():
            setattr(record, field_name, field_value)
        record.updated_at = datetime.now(UTC)

    def _sync_assumption_links(
        self,
        hypothesis_id: UUID,
        assumption_ids: builtins.list[UUID],
    ) -> None:
        deduped_ids: builtins.list[UUID] = dedupe_preserving_order(assumption_ids)
        replace_link_records(
            self._session,
            HypothesisAssumptionLinkRecord,
            owner_field_name="hypothesis_id",
            owner_id=hypothesis_id,
            payloads=[
                {
                    "hypothesis_id": hypothesis_id,
                    "assumption_id": assumption_id,
                }
                for assumption_id in deduped_ids
            ],
        )

    def _sync_dataset_links(
        self,
        hypothesis_id: UUID,
        dataset_ids: builtins.list[UUID],
    ) -> None:
        deduped_ids: builtins.list[UUID] = dedupe_preserving_order(dataset_ids)
        replace_link_records(
            self._session,
            HypothesisDatasetLinkRecord,
            owner_field_name="hypothesis_id",
            owner_id=hypothesis_id,
            payloads=[
                {
                    "hypothesis_id": hypothesis_id,
                    "dataset_id": dataset_id,
                }
                for dataset_id in deduped_ids
            ],
        )
