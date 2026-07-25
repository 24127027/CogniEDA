"""Repository for durable non-FCO evaluation-control records."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import EvaluationControlRecord
from schemas.enums import EvaluationControlState

ACTIVE_EVALUATION_STATES = {
    EvaluationControlState.PENDING,
    EvaluationControlState.CLAIMED,
    EvaluationControlState.PROPOSAL_READY,
    EvaluationControlState.RETRYABLE_FAILED,
}


class EvaluationControlRepository:
    """Repository managing durable EvaluationControlRecord state."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def stage_create(self, record: EvaluationControlRecord) -> EvaluationControlRecord:
        """Stage creation of an EvaluationControlRecord in the current session."""

        self._session.add(record)
        return record

    def get_by_id(self, evaluation_id: UUID) -> EvaluationControlRecord | None:
        """Return EvaluationControlRecord by primary ID."""

        return self._session.get(EvaluationControlRecord, evaluation_id)

    def get_by_hypothesis_and_digest(
        self,
        hypothesis_id: UUID,
        bundle_digest: str,
    ) -> EvaluationControlRecord | None:
        """Get existing evaluation record matching hypothesis_id and bundle_digest."""

        statement = (
            select(EvaluationControlRecord)
            .where(EvaluationControlRecord.hypothesis_id == hypothesis_id)
            .where(EvaluationControlRecord.bundle_digest == bundle_digest)
            .order_by(desc(EvaluationControlRecord.created_at))
        )
        return self._session.exec(statement).first()

    def get_by_evaluation_key(self, evaluation_key: str) -> EvaluationControlRecord | None:
        """Return the exact identity-bound evaluation control, if present."""

        return self._session.exec(
            select(EvaluationControlRecord).where(
                EvaluationControlRecord.evaluation_key == evaluation_key
            )
        ).first()

    def get_active_evaluation(self, hypothesis_id: UUID) -> EvaluationControlRecord | None:
        """Return active (non-terminal) evaluation for a hypothesis if one exists."""

        statement = (
            select(EvaluationControlRecord)
            .where(EvaluationControlRecord.hypothesis_id == hypothesis_id)
            .where(EvaluationControlRecord.state.in_(tuple(ACTIVE_EVALUATION_STATES)))  # type: ignore[attr-defined]
            .order_by(desc(EvaluationControlRecord.created_at))
        )
        return self._session.exec(statement).first()

    def list_by_hypothesis(self, hypothesis_id: UUID) -> list[EvaluationControlRecord]:
        """List all evaluation records for a hypothesis."""

        statement = (
            select(EvaluationControlRecord)
            .where(EvaluationControlRecord.hypothesis_id == hypothesis_id)
            .order_by(desc(EvaluationControlRecord.created_at))
        )
        return list(self._session.exec(statement).all())

    def list_pending(self, *, limit: int = 100) -> list[EvaluationControlRecord]:
        """Return pending controls in deterministic creation order."""

        statement = (
            select(EvaluationControlRecord)
            .where(EvaluationControlRecord.state == EvaluationControlState.PENDING)
            .order_by(EvaluationControlRecord.created_at, EvaluationControlRecord.evaluation_id)
            .limit(limit)
        )
        return list(self._session.exec(statement).all())
