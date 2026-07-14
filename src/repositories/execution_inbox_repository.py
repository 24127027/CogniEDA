"""Persistence access for minimal ExecutionInbox records."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import ExecutionInboxRecord
from repositories.common import record_to_schema
from schemas.provenance import ExecutionInbox


class ExecutionInboxRepository:
    """Repository for execution inbox records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, inbox_id: UUID) -> ExecutionInbox | None:
        """Return an ExecutionInbox by primary id if it exists."""
        record = self._session.get(ExecutionInboxRecord, inbox_id)
        if record is None:
            return None
        return record_to_schema(ExecutionInbox, record)

    def list(
        self,
        *,
        execution_run_id: UUID | None = None,
        dispatch_idempotency_key: str | None = None,
        status: str | None = None,
    ) -> list[ExecutionInbox]:
        """List ExecutionInbox records with simple filters."""
        statement = select(ExecutionInboxRecord).order_by(desc(ExecutionInboxRecord.created_at))
        if execution_run_id is not None:
            statement = statement.where(ExecutionInboxRecord.execution_run_id == execution_run_id)
        if dispatch_idempotency_key is not None:
            statement = statement.where(
                ExecutionInboxRecord.dispatch_idempotency_key == dispatch_idempotency_key
            )
        if status is not None:
            statement = statement.where(ExecutionInboxRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(ExecutionInbox, record) for record in records]
