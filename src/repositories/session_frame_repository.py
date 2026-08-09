"""Bounded SQLite snapshot envelope for the M1-A SessionFrame."""

from __future__ import annotations

import builtins
from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import SessionFrameRecord
from schemas.artifacts import SessionFrame

SESSION_FRAME_JSON_FIELDS = {"state"}


class SessionFrameRepository:
    """Append and retrieve validated MVP SessionFrame snapshots."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, session_frame: SessionFrame) -> SessionFrame:
        record = SessionFrameRecord(state=session_frame.model_dump(mode="json"))
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return SessionFrame.model_validate(record.state)

    def get_by_id(self, session_frame_id: UUID) -> SessionFrame | None:
        record = self._session.get(SessionFrameRecord, session_frame_id)
        return None if record is None else SessionFrame.model_validate(record.state)

    def list(self) -> builtins.list[SessionFrame]:
        statement = select(SessionFrameRecord).order_by(desc(SessionFrameRecord.created_at))
        return [
            SessionFrame.model_validate(record.state)
            for record in self._session.exec(statement).all()
        ]

    def list_recent(self, *, limit: int = 10) -> builtins.list[SessionFrame]:
        return self.list()[:limit]

    def get_latest(self) -> SessionFrame | None:
        frames = self.list_recent(limit=1)
        return frames[0] if frames else None
