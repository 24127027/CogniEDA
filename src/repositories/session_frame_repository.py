"""Persistence access for append-only session frame artifacts."""

from __future__ import annotations

import builtins
from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import SessionFrameRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.artifacts import SessionFrame

SESSION_FRAME_JSON_FIELDS = {
    "dataset_summaries",
    "active_dataset_refs",
    "active_assumptions",
    "active_assumption_refs",
    "active_hypotheses",
    "active_hypothesis_refs",
    "strongest_evidence",
    "strongest_evidence_refs",
    "recent_decisions",
    "recent_decision_refs",
    "pending_tasks",
    "open_questions",
    "key_warnings",
    "stale_context",
    "dead_ends",
    "cached_tool_results",
    "frame_invalidation_rules",
}


class SessionFrameRepository:
    """Artifact-specific CRUD access for compact session frames."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, session_frame: SessionFrame) -> SessionFrame:
        """Persist and return a new session frame artifact."""

        record = SessionFrameRecord(
            **schema_to_record_payload(session_frame, json_fields=SESSION_FRAME_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(SessionFrame, record)

    def get_by_id(self, session_frame_id: UUID) -> SessionFrame | None:
        """Return a session frame by primary id if it exists."""

        record = self._session.get(SessionFrameRecord, session_frame_id)
        if record is None:
            return None
        return record_to_schema(SessionFrame, record)

    def list(self, *, project_id: UUID | None = None) -> list[SessionFrame]:
        """List session frames, optionally scoped to a project."""

        statement = select(SessionFrameRecord).order_by(desc(SessionFrameRecord.created_at))
        if project_id is not None:
            statement = statement.where(SessionFrameRecord.project_id == project_id)
        records = self._session.exec(statement).all()
        return [record_to_schema(SessionFrame, record) for record in records]

    def list_recent(self, project_id: UUID, *, limit: int = 10) -> builtins.list[SessionFrame]:
        """List recent session frames for a project."""

        statement = (
            select(SessionFrameRecord)
            .where(SessionFrameRecord.project_id == project_id)
            .order_by(desc(SessionFrameRecord.created_at))
            .limit(limit)
        )
        records = self._session.exec(statement).all()
        return [record_to_schema(SessionFrame, record) for record in records]

    def get_latest(self, project_id: UUID) -> SessionFrame | None:
        """Return the latest session frame for a project."""

        statement = (
            select(SessionFrameRecord)
            .where(SessionFrameRecord.project_id == project_id)
            .order_by(desc(SessionFrameRecord.created_at))
            .limit(1)
        )
        record = self._session.exec(statement).first()
        if record is None:
            return None
        return record_to_schema(SessionFrame, record)
