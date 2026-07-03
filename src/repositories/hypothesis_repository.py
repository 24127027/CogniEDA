"""Persistence access for Hypothesis FCOs."""

from __future__ import annotations

import builtins
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, desc, select

from db.models import HypothesisRecord
from repositories.common import apply_update, record_to_schema, schema_to_record_payload
from schemas.artifacts import Hypothesis
from schemas.enums import HypothesisStatus

HYPOTHESIS_JSON_FIELDS = {"variables"}


class HypothesisUpdate(BaseModel):
    """Typed mutable fields for hypothesis lifecycle transitions."""

    statement: str | None = None
    variables: list[str] | None = None
    scope: str | None = None
    validation_method: str | None = None
    evidence_expectation: str | None = None
    status: HypothesisStatus | None = None
    updated_at: datetime | None = None


class HypothesisRepository:
    """Repository for atomic hypothesis test contracts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, hypothesis: Hypothesis) -> Hypothesis:
        """Persist and return a new Hypothesis."""

        record = HypothesisRecord(
            **schema_to_record_payload(hypothesis, json_fields=HYPOTHESIS_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Hypothesis, record)

    def get_by_id(self, hypothesis_id: UUID) -> Hypothesis | None:
        """Return a hypothesis by primary id if it exists."""

        record = self._session.get(HypothesisRecord, hypothesis_id)
        if record is None:
            return None
        return record_to_schema(Hypothesis, record)

    def list(
        self,
        *,
        task_id: UUID | None = None,
        profile_id: UUID | None = None,
        status: HypothesisStatus | None = None,
    ) -> list[Hypothesis]:
        """List hypotheses by task, profile, or lifecycle state."""

        statement = select(HypothesisRecord).order_by(desc(HypothesisRecord.updated_at))
        if task_id is not None:
            statement = statement.where(HypothesisRecord.task_id == task_id)
        if profile_id is not None:
            statement = statement.where(HypothesisRecord.profile_id == profile_id)
        if status is not None:
            statement = statement.where(HypothesisRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(Hypothesis, record) for record in records]

    def list_active(self) -> builtins.list[Hypothesis]:
        """List hypotheses that can still appear in active working context."""

        active_statuses = (HypothesisStatus.PROPOSED, HypothesisStatus.TESTING)
        return [
            hypothesis
            for hypothesis in self.list()
            if hypothesis.status in active_statuses
        ]

    def list_for_profile(self, profile_id: UUID) -> builtins.list[Hypothesis]:
        """List hypotheses scoped to a DataProfile."""

        return self.list(profile_id=profile_id)

    def update(self, hypothesis_id: UUID, update: HypothesisUpdate) -> Hypothesis | None:
        """Apply an allowed hypothesis lifecycle transition."""

        record = self._session.get(HypothesisRecord, hypothesis_id)
        if record is None:
            return None
        apply_update(record, update, json_fields=HYPOTHESIS_JSON_FIELDS)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Hypothesis, record)
