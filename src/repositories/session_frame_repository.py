"""Persistence access for append-only SessionFrame FCOs."""

from __future__ import annotations

import builtins
from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import SessionFrameRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.artifacts import SessionFrame

SESSION_FRAME_JSON_FIELDS = {
    "data_profile_summaries",
    "active_data_profile_refs",
    "active_tasks",
    "active_task_refs",
    "active_assumptions",
    "active_assumption_refs",
    "active_hypotheses",
    "active_hypothesis_refs",
    "relevant_discoveries",
    "relevant_discovery_refs",
    "supporting_evidence",
    "supporting_evidence_refs",
    "recent_user_decisions",
    "recent_user_decision_refs",
    "pending_tasks",
    "pending_proposals",
    "user_pins",
    "user_exclusions",
    "mandatory_dependencies",
    "inclusion_reasons",
    "open_questions",
    "key_warnings",
    "stale_context",
    "dead_ends",
    "cached_tool_results",
    "frame_invalidation_rules",
}


class SessionFrameRepository:
    """Repository for compact, append-only active-context frames."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, session_frame: SessionFrame) -> SessionFrame:
        """Persist and return a new SessionFrame."""

        record = SessionFrameRecord(
            **schema_to_record_payload(session_frame, json_fields=SESSION_FRAME_JSON_FIELDS)
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(SessionFrame, record)

    def get_by_id(self, session_frame_id: UUID) -> SessionFrame | None:
        """Return a SessionFrame by primary id if it exists."""

        record = self._session.get(SessionFrameRecord, session_frame_id)
        if record is None:
            return None
        return record_to_schema(SessionFrame, record)

    def list(self) -> list[SessionFrame]:
        """List all SessionFrames in this workspace graph."""

        statement = select(SessionFrameRecord).order_by(desc(SessionFrameRecord.created_at))
        records = self._session.exec(statement).all()
        return [record_to_schema(SessionFrame, record) for record in records]

    def list_recent(self, *, limit: int = 10) -> builtins.list[SessionFrame]:
        """List recent SessionFrames in this workspace graph."""

        statement = select(SessionFrameRecord).order_by(desc(SessionFrameRecord.created_at)).limit(
            limit
        )
        records = self._session.exec(statement).all()
        return [record_to_schema(SessionFrame, record) for record in records]

    def get_latest(self) -> SessionFrame | None:
        """Return the latest SessionFrame in this workspace graph."""

        statement = select(SessionFrameRecord).order_by(desc(SessionFrameRecord.created_at)).limit(
            1
        )
        record = self._session.exec(statement).first()
        if record is None:
            return None
        return record_to_schema(SessionFrame, record)
