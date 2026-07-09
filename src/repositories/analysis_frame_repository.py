"""Persistence access for minimal AnalysisFrame provenance records."""

from __future__ import annotations

from uuid import UUID

from db.models import AnalysisFrameRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.provenance import AnalysisFrame
from sqlmodel import Session, desc, select

ANALYSIS_FRAME_JSON_FIELDS = {"column_refs"}


class AnalysisFrameRepository:
    """Repository for provenance-only AnalysisFrame records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, analysis_frame: AnalysisFrame) -> AnalysisFrame:
        """Persist and return a new AnalysisFrame record."""

        record = AnalysisFrameRecord(
            **schema_to_record_payload(
                analysis_frame,
                json_fields=ANALYSIS_FRAME_JSON_FIELDS,
            )
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(AnalysisFrame, record)

    def get_by_id(self, analysis_frame_id: UUID) -> AnalysisFrame | None:
        """Return an AnalysisFrame by primary id if it exists."""

        record = self._session.get(AnalysisFrameRecord, analysis_frame_id)
        if record is None:
            return None
        return record_to_schema(AnalysisFrame, record)

    def list(self, *, data_profile_id: UUID | None = None) -> list[AnalysisFrame]:
        """List AnalysisFrame records, optionally scoped to one DataProfile."""

        statement = select(AnalysisFrameRecord).order_by(desc(AnalysisFrameRecord.created_at))
        if data_profile_id is not None:
            statement = statement.where(AnalysisFrameRecord.data_profile_id == data_profile_id)
        records = self._session.exec(statement).all()
        return [record_to_schema(AnalysisFrame, record) for record in records]
