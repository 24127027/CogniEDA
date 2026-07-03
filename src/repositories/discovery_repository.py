"""Persistence access for immutable Discovery FCOs."""

from __future__ import annotations

import builtins
from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import DiscoveryRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.artifacts import Discovery
from schemas.enums import DiscoveryEpistemicStatus

DISCOVERY_JSON_FIELDS = {"evidence_ids", "claim", "validity_basis"}


class DiscoveryRepository:
    """Repository for evidence-bound Discovery claims."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, discovery: Discovery) -> Discovery:
        """Persist and return a new Discovery."""

        record = DiscoveryRecord(
            **schema_to_record_payload(discovery, json_fields=DISCOVERY_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Discovery, record)

    def get_by_id(self, discovery_id: UUID) -> Discovery | None:
        """Return a Discovery by primary id if it exists."""

        record = self._session.get(DiscoveryRecord, discovery_id)
        if record is None:
            return None
        return record_to_schema(Discovery, record)

    def list(
        self,
        *,
        hypothesis_id: UUID | None = None,
        epistemic_status: DiscoveryEpistemicStatus | None = None,
    ) -> list[Discovery]:
        """List Discoveries by source Hypothesis or epistemic status."""

        statement = select(DiscoveryRecord).order_by(desc(DiscoveryRecord.created_at))
        if hypothesis_id is not None:
            statement = statement.where(DiscoveryRecord.hypothesis_id == hypothesis_id)
        if epistemic_status is not None:
            statement = statement.where(DiscoveryRecord.epistemic_status == epistemic_status)
        records = self._session.exec(statement).all()
        return [record_to_schema(Discovery, record) for record in records]

    def list_for_hypothesis(self, hypothesis_id: UUID) -> builtins.list[Discovery]:
        """List Discoveries produced for one Hypothesis."""

        return self.list(hypothesis_id=hypothesis_id)
