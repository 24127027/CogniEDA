"""Persistence access for typed user-decision provenance records."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, desc, select

from db.models import UserDecisionRecord
from repositories.common import apply_update, record_to_schema, schema_to_record_payload
from schemas.artifacts import UserDecision
from schemas.enums import UserDecisionStatus, UserDecisionType

USER_DECISION_JSON_FIELDS = {
    "alternatives_considered",
    "related_task_ids",
    "related_hypothesis_ids",
}


class UserDecisionUpdate(BaseModel):
    """Typed mutable fields for user-decision provenance lifecycle updates."""

    status: UserDecisionStatus | None = None
    superseded_by_decision_id: UUID | None = None
    updated_at: datetime | None = None


class UserDecisionRepository:
    """Repository for typed provenance records of user decisions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, user_decision: UserDecision) -> UserDecision:
        """Persist and return a new user-decision provenance record."""

        record = UserDecisionRecord(
            **schema_to_record_payload(user_decision, json_fields=USER_DECISION_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(UserDecision, record)

    def get_by_id(self, decision_id: UUID) -> UserDecision | None:
        """Return a user-decision provenance record by id if it exists."""

        record = self._session.get(UserDecisionRecord, decision_id)
        if record is None:
            return None
        return record_to_schema(UserDecision, record)

    def list(
        self,
        *,
        decision_type: UserDecisionType | None = None,
        status: UserDecisionStatus | None = None,
    ) -> list[UserDecision]:
        """List user-decision records by type or lifecycle state."""

        statement = select(UserDecisionRecord).order_by(desc(UserDecisionRecord.updated_at))
        if decision_type is not None:
            statement = statement.where(UserDecisionRecord.decision_type == decision_type)
        if status is not None:
            statement = statement.where(UserDecisionRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(UserDecision, record) for record in records]

    def update(self, decision_id: UUID, update: UserDecisionUpdate) -> UserDecision | None:
        """Apply a user-decision provenance lifecycle transition."""

        record = self._session.get(UserDecisionRecord, decision_id)
        if record is None:
            return None
        apply_update(record, update)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(UserDecision, record)
