"""Persistence access for decision log artifacts."""

from __future__ import annotations

import builtins
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, desc, select

from db.models import (
    DecisionAssumptionLinkRecord,
    DecisionHypothesisLinkRecord,
    DecisionLogRecord,
)
from repositories.common import (
    dedupe_preserving_order,
    load_related_ids,
    replace_link_records,
)
from schemas.artifacts import DecisionLog
from schemas.enums import DecisionStatus, DecisionType

DECISION_JSON_FIELDS = {
    "alternatives_considered",
}


class DecisionLogUpdate(BaseModel):
    """Typed mutable fields for decision-log updates."""

    decision_type: DecisionType | None = None
    decision: str | None = None
    rationale: str | None = None
    status: DecisionStatus | None = None
    alternatives_considered: list[str] | None = None
    assumption_ids: list[UUID] | None = None
    hypothesis_ids: list[UUID] | None = None
    superseded_by_decision_id: UUID | None = None
    updated_at: datetime | None = None


class DecisionLogRepository:
    """Artifact-specific CRUD access for decision logs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, decision_log: DecisionLog) -> DecisionLog:
        """Persist and return a new decision log artifact."""

        record = DecisionLogRecord(**self._record_payload(decision_log))
        self._session.add(record)
        self._sync_assumption_links(decision_log.decision_id, decision_log.assumption_ids)
        self._sync_hypothesis_links(decision_log.decision_id, decision_log.hypothesis_ids)
        self._session.commit()
        self._session.refresh(record)
        return self._hydrate(record)

    def get_by_id(self, decision_id: UUID) -> DecisionLog | None:
        """Return a decision log artifact by primary id if it exists."""

        record = self._session.get(DecisionLogRecord, decision_id)
        if record is None:
            return None
        return self._hydrate(record)

    def list(
        self,
        *,
        project_id: UUID | None = None,
        status: DecisionStatus | None = None,
    ) -> list[DecisionLog]:
        """List decision logs, optionally scoped to a project."""

        statement = select(DecisionLogRecord).order_by(desc(DecisionLogRecord.updated_at))
        if project_id is not None:
            statement = statement.where(DecisionLogRecord.project_id == project_id)
        if status is not None:
            statement = statement.where(DecisionLogRecord.status == status)
        records = self._session.exec(statement).all()
        return [self._hydrate(record) for record in records]

    def list_active(self, *, project_id: UUID | None = None) -> builtins.list[DecisionLog]:
        """List only active decisions."""

        return self.list(project_id=project_id, status=DecisionStatus.ACTIVE)

    def list_recent(
        self,
        *,
        project_id: UUID | None = None,
        limit: int = 10,
        active_only: bool = True,
    ) -> builtins.list[DecisionLog]:
        """List recent decisions, optionally only active ones."""

        statement = (
            select(DecisionLogRecord)
            .order_by(desc(DecisionLogRecord.updated_at))
            .limit(limit)
        )
        if project_id is not None:
            statement = statement.where(DecisionLogRecord.project_id == project_id)
        if active_only:
            statement = statement.where(DecisionLogRecord.status == DecisionStatus.ACTIVE)
        records = self._session.exec(statement).all()
        return [self._hydrate(record) for record in records]

    def update(self, decision_id: UUID, update: DecisionLogUpdate) -> DecisionLog | None:
        """Apply a typed partial update to a decision log record."""

        record = self._session.get(DecisionLogRecord, decision_id)
        if record is None:
            return None
        self._apply_update(record, update)
        if update.assumption_ids is not None:
            self._sync_assumption_links(decision_id, update.assumption_ids)
        if update.hypothesis_ids is not None:
            self._sync_hypothesis_links(decision_id, update.hypothesis_ids)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return self._hydrate(record)

    def _hydrate(self, record: DecisionLogRecord) -> DecisionLog:
        payload = record.model_dump()
        payload["assumption_ids"] = load_related_ids(
            self._session,
            DecisionAssumptionLinkRecord,
            owner_field_name="decision_id",
            owner_id=record.decision_id,
            related_field_name="assumption_id",
        )
        payload["hypothesis_ids"] = load_related_ids(
            self._session,
            DecisionHypothesisLinkRecord,
            owner_field_name="decision_id",
            owner_id=record.decision_id,
            related_field_name="hypothesis_id",
        )
        return DecisionLog.model_validate(payload)

    def _record_payload(self, decision_log: DecisionLog) -> dict[str, object]:
        python_payload = decision_log.model_dump(
            mode="python",
            exclude={"assumption_ids", "hypothesis_ids"},
        )
        json_payload = decision_log.model_dump(
            mode="json",
            include=DECISION_JSON_FIELDS,
        )
        if "alternatives_considered" in json_payload:
            python_payload["alternatives_considered"] = json_payload["alternatives_considered"]
        return python_payload

    def _apply_update(self, record: DecisionLogRecord, update: DecisionLogUpdate) -> None:
        python_payload = update.model_dump(
            mode="python",
            exclude_unset=True,
            exclude={"assumption_ids", "hypothesis_ids"},
        )
        json_payload = update.model_dump(
            mode="json",
            exclude_unset=True,
            include=DECISION_JSON_FIELDS,
        )
        if "alternatives_considered" in json_payload:
            python_payload["alternatives_considered"] = json_payload["alternatives_considered"]
        for field_name, field_value in python_payload.items():
            setattr(record, field_name, field_value)
        record.updated_at = datetime.now(UTC)

    def _sync_assumption_links(
        self,
        decision_id: UUID,
        assumption_ids: builtins.list[UUID],
    ) -> None:
        deduped_ids: builtins.list[UUID] = dedupe_preserving_order(assumption_ids)
        replace_link_records(
            self._session,
            DecisionAssumptionLinkRecord,
            owner_field_name="decision_id",
            owner_id=decision_id,
            payloads=[
                {
                    "decision_id": decision_id,
                    "assumption_id": assumption_id,
                }
                for assumption_id in deduped_ids
            ],
        )

    def _sync_hypothesis_links(
        self,
        decision_id: UUID,
        hypothesis_ids: builtins.list[UUID],
    ) -> None:
        deduped_ids: builtins.list[UUID] = dedupe_preserving_order(hypothesis_ids)
        replace_link_records(
            self._session,
            DecisionHypothesisLinkRecord,
            owner_field_name="decision_id",
            owner_id=decision_id,
            payloads=[
                {
                    "decision_id": decision_id,
                    "hypothesis_id": hypothesis_id,
                }
                for hypothesis_id in deduped_ids
            ],
        )
