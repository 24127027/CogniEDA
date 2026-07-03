"""Persistence access for immutable Evidence FCOs."""

from __future__ import annotations

import builtins
from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import EvidenceRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.artifacts import Evidence
from schemas.enums import EvidenceLifecycleState

EVIDENCE_JSON_FIELDS = {
    "parameters",
    "provenance",
    "result_summary",
    "artifact_refs",
    "limitations",
}


class EvidenceRepository:
    """Repository for append-only Evidence records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, evidence: Evidence) -> Evidence:
        """Persist and return a new Evidence record."""

        record = EvidenceRecord(
            **schema_to_record_payload(evidence, json_fields=EVIDENCE_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Evidence, record)

    def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        """Return an Evidence record by primary id if it exists."""

        record = self._session.get(EvidenceRecord, evidence_id)
        if record is None:
            return None
        return record_to_schema(Evidence, record)

    def list(
        self,
        *,
        hypothesis_id: UUID | None = None,
        profile_id: UUID | None = None,
        lifecycle_state: EvidenceLifecycleState | None = None,
    ) -> list[Evidence]:
        """List evidence by hypothesis, DataProfile, or lifecycle state."""

        statement = select(EvidenceRecord).order_by(desc(EvidenceRecord.created_at))
        if hypothesis_id is not None:
            statement = statement.where(EvidenceRecord.hypothesis_id == hypothesis_id)
        if profile_id is not None:
            statement = statement.where(EvidenceRecord.profile_id == profile_id)
        if lifecycle_state is not None:
            statement = statement.where(EvidenceRecord.lifecycle_state == lifecycle_state)
        records = self._session.exec(statement).all()
        return [record_to_schema(Evidence, record) for record in records]

    def list_for_hypothesis(self, hypothesis_id: UUID) -> builtins.list[Evidence]:
        """List Evidence records for one Hypothesis."""

        return self.list(hypothesis_id=hypothesis_id)

    def list_for_profile(self, profile_id: UUID) -> builtins.list[Evidence]:
        """List Evidence records for one DataProfile."""

        return self.list(profile_id=profile_id)
